"""充电桩状态模拟器的测试（PLAN §3.2 任务 5.8）。

钉住三件事：

1. **状态按时间流转**：空闲→充电中→已充满→释放，且阈值未到时不乱跳
2. **业务阈值来自 `system_config`**：把 `full_timeout_min` 从 30 改到 120，
   同一时刻的已充满桩就不再释放 —— 证明模拟器没硬编码（契约 §7）
3. **一次只推进一步**：否则演示时会直接跳过「充电中」，第 3 页三种状态色白设计
"""

from __future__ import annotations

from datetime import datetime

from app import models as m
from app.simulator import (
    SIM_CHARGING_TO_FULL_MIN,
    SIM_IDLE_TO_CHARGING_MIN,
    advance,
    advance_pile,
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
