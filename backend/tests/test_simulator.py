"""充电桩状态模拟器的测试（PLAN §3.2 任务 5.8）。

钉住三件事：

1. **状态按时间流转**：空闲→充电中→已充满→释放，且阈值未到时不乱跳
2. **业务阈值来自 `system_config`**：把 `full_timeout_min` 从 30 改到 120，
   同一时刻的已充满桩就不再释放 —— 证明模拟器没硬编码（契约 §7）
3. **一次只推进一步**：否则演示时会直接跳过「充电中」，第 3 页三种状态色白设计
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import models as m
from app.simulator import (
    SIM_CHARGING_TO_FULL_MIN,
    SIM_IDLE_TO_CHARGING_MIN,
    advance,
    advance_pile,
    normalize_moment,
)

NOW = datetime(2026, 9, 8, 10, 0, 0)


def _pile(db, pile_id: str) -> m.ChargingPile:
    return db.get(m.ChargingPile, pile_id)


def _set_config(db, key: str, value: str) -> None:
    row = db.get(m.SystemConfig, key)
    row.value = value
    db.commit()


# ---------------------------------------------------------------------------
# 空闲 → 充电中
# ---------------------------------------------------------------------------
def test_idle_pile_with_car_starts_charging_after_wait(db_session):
    """种子 PILE-003：空闲、08:30 到达 → 10:00 早该开始充电了。"""
    change = advance_pile(_pile(db_session, "PILE-003"), db_session, NOW)
    assert change is not None
    assert (change.from_status, change.to_status) == (m.PILE_IDLE, m.PILE_CHARGING)
    pile = _pile(db_session, "PILE-003")
    assert pile.status == m.PILE_CHARGING
    assert pile.start_time == NOW  # 重置为「开始充电时刻」


def test_idle_pile_waiting_not_long_enough(db_session):
    pile = _pile(db_session, "PILE-003")
    pile.start_time = NOW  # 刚到
    db_session.commit()
    assert advance_pile(pile, db_session, NOW) is None
    assert pile.status == m.PILE_IDLE


def test_idle_pile_without_car_never_changes(db_session):
    """没有车就不该凭空开始充电 —— 车从识别系统来，不由模拟器编。"""
    db_session.add(m.ChargingPile(pile_id="PILE-800", status=m.PILE_IDLE, bound_plate=None))
    db_session.commit()
    assert advance_pile(_pile(db_session, "PILE-800"), db_session, NOW) is None
    assert _pile(db_session, "PILE-800").status == m.PILE_IDLE


# ---------------------------------------------------------------------------
# 充电中 → 已充满
# ---------------------------------------------------------------------------
def test_charging_pile_becomes_full(db_session):
    pile = _pile(db_session, "PILE-001")  # 种子：09:50 开始充电
    moment = pile.start_time.replace(minute=0)  # 09:00 —— 不足 20 分钟
    assert advance_pile(pile, db_session, moment) is None

    later = datetime(2026, 9, 8, 10, 15)  # 25 分钟后
    change = advance_pile(pile, db_session, later)
    assert (change.from_status, change.to_status) == (m.PILE_CHARGING, m.PILE_FULL)
    assert pile.end_time == later
    assert SIM_CHARGING_TO_FULL_MIN == 20


# ---------------------------------------------------------------------------
# 已充满 → 释放（业务阈值）
# ---------------------------------------------------------------------------
def test_full_pile_released_after_timeout(db_session):
    """种子 PILE-002：09:20 充满，10:00 已超 30 分钟阈值 → 释放。"""
    change = advance_pile(_pile(db_session, "PILE-002"), db_session, NOW)
    assert (change.from_status, change.to_status) == (m.PILE_FULL, m.PILE_IDLE)
    pile = _pile(db_session, "PILE-002")
    assert pile.bound_plate is None
    assert pile.start_time is None and pile.end_time is None


def test_full_pile_uses_config_threshold_not_hardcode(db_session):
    """契约 §7：阈值来自 system_config。改成 120 分钟 → 同一时刻不再释放。"""
    assert (
        advance_pile(_pile(db_session, "PILE-002"), db_session, NOW) is not None
    )  # 30 分钟阈值下释放
    db_session.rollback()

    _set_config(db_session, "full_timeout_min", "120")
    assert advance_pile(_pile(db_session, "PILE-002"), db_session, NOW) is None
    assert _pile(db_session, "PILE-002").status == m.PILE_FULL

    _set_config(db_session, "full_timeout_min", "5")
    assert advance_pile(_pile(db_session, "PILE-002"), db_session, NOW) is not None


def test_release_uses_end_time_not_start_time(db_session):
    """充满超时按 `end_time` 算（规则③同一口径），不是按到达时间。"""
    pile = _pile(db_session, "PILE-002")
    pile.end_time = NOW  # 刚充满
    db_session.commit()
    assert advance_pile(pile, db_session, NOW) is None


# ---------------------------------------------------------------------------
# 超时释放必须留下规则③记录（第 2 周验收审查阻断项 ①）
# ---------------------------------------------------------------------------
def test_timeout_release_leaves_rule3_record(db_session):
    """**防回归**：释放前要把「充满超时未移车」落库。

    早期版本只把桩清空就返回，于是进度文档宣称的「模拟数据会自然触发规则③」
    实际一条记录都没有 —— 第 2 页/第 4 页看不到任何真数据。
    """
    advance_pile(_pile(db_session, "PILE-002"), db_session, NOW)

    rows = db_session.query(m.OccupationRecord).all()
    assert len(rows) == 1, rows
    row = rows[0]
    assert row.rule_hit == m.RULE_FULL_NOT_MOVED
    assert row.plate == "京AD67890"  # 释放前的绑定车牌，记录要留住（无 FK，删车也不删它）
    assert row.pile_id == "PILE-002"
    assert row.vtype == m.VTYPE_NEW_ENERGY
    assert row.occur_time == NOW
    assert row.notify_status == m.NOTIFY_PENDING


def test_release_reason_mentions_recorded_rule(db_session):
    """变化原因里写明落了哪条规则，演示时一眼能看出记录是怎么来的。"""
    change = advance_pile(_pile(db_session, "PILE-002"), db_session, NOW)
    assert "规则③" in change.reason, change.reason


def test_timeout_release_writes_no_record_when_vehicle_unknown(db_session):
    """车没录入 `vehicle` 表 → 判不出车型 → **宁可不落库，也不编造车型**。

    车型决定命中规则①还是③，兜底成「新能源」等于往库里写假数据，
    与本项目「不静默兜底」的纪律冲突。
    """
    db_session.add(
        m.ChargingPile(
            pile_id="PILE-900",
            status=m.PILE_FULL,
            bound_plate="京Z99999",  # 不在 SEED_VEHICLES 里
            start_time=datetime(2026, 9, 8, 8, 0),
            end_time=datetime(2026, 9, 8, 9, 0),
        )
    )
    db_session.commit()

    change = advance_pile(_pile(db_session, "PILE-900"), db_session, NOW)
    assert change is not None and change.to_status == m.PILE_IDLE  # 照样释放
    assert db_session.query(m.OccupationRecord).count() == 0
    assert "规则" not in change.reason


def test_fuel_car_on_full_pile_records_rule1_not_rule3(db_session):
    """判定交回规则引擎：桩上若是燃油车，引擎判规则①，模拟器不得擅自写 3。"""
    pile = _pile(db_session, "PILE-004")  # 种子：绑定燃油车 京A88888
    pile.status = m.PILE_FULL
    pile.end_time = datetime(2026, 9, 8, 9, 0)
    db_session.commit()

    advance_pile(pile, db_session, NOW)
    row = db_session.query(m.OccupationRecord).one()
    assert row.rule_hit == m.RULE_FUEL_OCCUPY
    assert row.vtype == m.VTYPE_FUEL


def test_repeated_timeout_does_not_duplicate_records(db_session):
    """同一违规持续中只更新不新增（复用 `save_violation` 的去重口径）。"""
    db_session.add(
        m.ChargingPile(
            pile_id="PILE-901",
            status=m.PILE_FULL,
            bound_plate="京AD33333",
            start_time=datetime(2026, 9, 8, 8, 0),
            end_time=datetime(2026, 9, 8, 9, 0),
        )
    )
    db_session.commit()

    advance_pile(_pile(db_session, "PILE-901"), db_session, NOW)
    first_count = db_session.query(m.OccupationRecord).count()
    # 再绑一辆车、再超时一次：同桩同规则且未提醒 → 复用同一条
    pile = _pile(db_session, "PILE-901")
    pile.status = m.PILE_FULL
    pile.bound_plate = "京AD33333"
    pile.end_time = datetime(2026, 9, 8, 9, 0)
    db_session.commit()
    advance_pile(pile, db_session, datetime(2026, 9, 8, 11, 0))

    assert db_session.query(m.OccupationRecord).count() == first_count == 1


# ---------------------------------------------------------------------------
# 时间基准：带时区的时刻要归一化（第 2 周验收审查阻断项 ③）
# ---------------------------------------------------------------------------
def test_normalize_moment_strips_timezone():
    """aware → 本地朴素时间；naive / None 原样返回。"""
    aware = datetime(2026, 9, 8, 10, 30, tzinfo=timezone(timedelta(hours=8)))
    naive = normalize_moment(aware)
    assert naive.tzinfo is None
    assert naive == aware.astimezone().replace(tzinfo=None)

    plain = datetime(2026, 9, 8, 10, 30)
    assert normalize_moment(plain) is plain
    assert normalize_moment(None) is None


def test_advance_accepts_timezone_aware_now(db_session):
    """**防回归**：传带时区的 `now` 曾经抛 TypeError（aware − naive）→ 接口 500。"""
    aware = NOW.replace(tzinfo=timezone(timedelta(hours=8)))
    result = advance(db_session, now=aware)
    assert result.advanced_at.tzinfo is None
    assert result.advanced_at == NOW
    assert result.changed_count == 3  # 确实推进了，不是静默空转


# ---------------------------------------------------------------------------
# advance：批量 + 单步 + 确定性
# ---------------------------------------------------------------------------
def test_advance_walks_every_pile(db_session):
    result = advance(db_session, now=NOW)
    # 种子 4 桩：001 充电中未满（不变）、002 超时释放、003/004 空闲转充电中
    assert result.changed_count == 3
    assert {change.pile_id for change in result.changes} == {"PILE-002", "PILE-003", "PILE-004"}
    assert result.advanced_at == NOW


def test_advance_is_idempotent_within_same_moment(db_session):
    """同一时刻推进两次：第二次应当「无变化」（一次只推进一步）。

    否则演示时一刷新就会连跳两档，看不到中间的「充电中」。
    """
    assert advance(db_session, now=NOW).changed_count == 3
    assert advance(db_session, now=NOW).changed_count == 0


def test_advance_is_deterministic():
    """同样的输入 → 同样的输出（不掷随机数），演示可复现。

    `advance` 会 commit，同一会话无法回滚重来，故开两个等价的独立内存库对比。
    """
    first_db, first_engine = _fresh_seeded_session()
    second_db, second_engine = _fresh_seeded_session()
    try:
        first = advance(first_db, now=NOW)
        second = advance(second_db, now=NOW)
        assert [(c.pile_id, c.from_status, c.to_status) for c in first.changes] == [
            (c.pile_id, c.from_status, c.to_status) for c in second.changes
        ]
    finally:
        first_db.close()
        first_engine.dispose()
        second_db.close()
        second_engine.dispose()


def _fresh_seeded_session():
    """新建一份独立的内存库（已建表 + 灌种子），与 conftest 的 db_session 同规格。"""
    from app.db import Base
    from app.models import seed_db
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()
    seed_db(session)
    return session, engine


def test_advance_commits_changes(db_session):
    advance(db_session, now=NOW)
    statuses = {p.pile_id: p.status for p in db_session.query(m.ChargingPile).all()}
    assert statuses == {
        "PILE-001": m.PILE_CHARGING,
        "PILE-002": m.PILE_IDLE,
        "PILE-003": m.PILE_CHARGING,
        "PILE-004": m.PILE_CHARGING,
    }


def test_simulator_constants_are_documented_as_pacing(db_session):
    """模拟器节奏参数是常量、不进 system_config —— 那张表只放业务阈值（契约 §7 白名单）。"""
    keys = {row.key for row in db_session.query(m.SystemConfig).all()}
    assert keys == {"full_timeout_min", "abnormal_park_min"}
    assert SIM_IDLE_TO_CHARGING_MIN > 0 and SIM_CHARGING_TO_FULL_MIN > 0
