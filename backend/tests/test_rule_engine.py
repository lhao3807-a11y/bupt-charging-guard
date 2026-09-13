"""规则引擎单测 —— 覆盖四条规则的命中、边界与阈值来源。

对应 CONTRACT §11 验收项：「POST /api/judge 四条规则正确：燃油占位 / 异常占位 /
充满未移车 各命中，正常充电返回 null」。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app import models as m
from app.db import Base
from app.rule_engine import ConfigMissingError, judge, mark_notified, save_violation
from app.schemas import RecognitionResult, VType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 判定时刻：种子数据的桩状态在这个时间点上正好分别对应四条规则
NOW = datetime(2026, 9, 8, 10, 0, 0)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    m.seed_db(session)
    try:
        yield session
    finally:
        session.close()


def make_recognition(plate: str, vtype: VType, frame_time: datetime = NOW):
    return RecognitionResult(
        plate=plate,
        vtype=vtype,
        confidence=0.97,
        bbox=[120, 80, 200, 120],
        frame_time=frame_time,
    )


def fuel(plate: str, frame_time: datetime = NOW):
    return make_recognition(plate, VType.燃油, frame_time)


def ev(plate: str, frame_time: datetime = NOW):
    return make_recognition(plate, VType.新能源, frame_time)


# ---------------------------------------------------------------------------
# 规则① 燃油车（蓝牌）占充电位 → 1
# ---------------------------------------------------------------------------
def test_rule1_fuel_on_pile_hits(db):
    record = judge(fuel("京A88888"), db)
    assert record is not None
    assert record.rule_hit == m.RULE_FUEL_OCCUPY == 1
    assert record.plate == "京A88888"
    assert record.vtype == VType.燃油
    assert record.pile_id == "PILE-004"
    assert record.id is None  # 尚未落库
    assert record.notify_status == "未提醒"
    assert record.occur_time == NOW  # 判定时刻取 frame_time


def test_rule1_hits_even_if_pile_is_charging(db):
    """燃油车占位与桩状态无关，桩在充电中也应命中（同桩被占用即违规）。"""
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-004").one()
    pile.status = m.PILE_CHARGING
    db.commit()

    record = judge(fuel("京A88888"), db)
    assert record is not None and record.rule_hit == m.RULE_FUEL_OCCUPY


# ---------------------------------------------------------------------------
# 规则② 新能源车未充电且久停 → 2
# ---------------------------------------------------------------------------
def test_rule2_ev_idle_too_long_hits(db):
    # PILE-003 空闲，start_time=08:30 → 10:00 已停 90 分钟 > 30
    record = judge(ev("京AD24680"), db)
    assert record is not None
    assert record.rule_hit == m.RULE_ABNORMAL == 2
    assert record.pile_id == "PILE-003"


@pytest.mark.parametrize("minutes", [0, 5, 29])
def test_rule2_not_hit_within_threshold(db, minutes):
    """未超阈值不提醒。"""
    record = judge(
        ev("京AD24680", frame_time=datetime(2026, 9, 8, 8, 30) + timedelta(minutes=minutes)), db
    )
    assert record is None


def test_rule2_not_hit_without_start_time(db):
    """桩空闲但没有到达时间 → 无法判定久停，不提醒。"""
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-003").one()
    pile.start_time = None
    db.commit()
    assert judge(ev("京AD24680"), db) is None


# ---------------------------------------------------------------------------
# 规则③ 新能源车充满超时未移车 → 3
# ---------------------------------------------------------------------------
def test_rule3_ev_full_timeout_hits(db):
    # PILE-002 已充满，end_time=09:20 → 10:00 已充满 40 分钟 > 30
    record = judge(ev("京AD67890"), db)
    assert record is not None
    assert record.rule_hit == m.RULE_FULL_NOT_MOVED == 3
    assert record.pile_id == "PILE-002"


@pytest.mark.parametrize("minutes", [0, 10, 29])
def test_rule3_not_hit_within_threshold(db, minutes):
    record = judge(
        ev("京AD67890", frame_time=datetime(2026, 9, 8, 9, 20) + timedelta(minutes=minutes)), db
    )
    assert record is None


def test_rule3_not_hit_without_end_time(db):
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-002").one()
    pile.end_time = None
    db.commit()
    assert judge(ev("京AD67890"), db) is None


# ---------------------------------------------------------------------------
# 规则④ 正常充电 → None
# ---------------------------------------------------------------------------
def test_rule4_normal_charging_returns_none(db):
    # PILE-001 充电中
    assert judge(ev("京AD12345"), db) is None


def test_unknown_plate_not_on_any_pile_returns_none(db):
    """车牌不在任何桩上 → 不属于判定范围（也不因缺桩而报错）。"""
    assert judge(ev("京AD00000"), db) is None
    assert judge(fuel("京A11111"), db) is None


# ---------------------------------------------------------------------------
# 阈值必须来自 system_config，禁止硬编码
# ---------------------------------------------------------------------------
def test_threshold_comes_from_db_not_hardcoded(db):
    """把 abnormal_park_min 改成 120 后，原本命中的 90 分钟场景不再命中。"""
    assert judge(ev("京AD24680"), db) is not None

    cfg = db.query(m.SystemConfig).filter(m.SystemConfig.key == "abnormal_park_min").one()
    cfg.value = "120"
    db.commit()

    assert judge(ev("京AD24680"), db) is None


def test_full_timeout_threshold_comes_from_db(db):
    assert judge(ev("京AD67890"), db) is not None

    cfg = db.query(m.SystemConfig).filter(m.SystemConfig.key == "full_timeout_min").one()
    cfg.value = "120"
    db.commit()

    assert judge(ev("京AD67890"), db) is None


def test_missing_config_raises_clear_error(db):
    """缺阈值时明确报错，而不是静默兜底。"""
    db.query(m.SystemConfig).filter(m.SystemConfig.key == "abnormal_park_min").delete()
    db.commit()
    with pytest.raises(ConfigMissingError, match="abnormal_park_min"):
        judge(ev("京AD24680"), db)


# ---------------------------------------------------------------------------
# 落库 / 沙箱辅助
# ---------------------------------------------------------------------------
def test_save_violation_persists_and_returns_id(db):
    record = judge(fuel("京A88888"), db)
    assert record is not None

    saved = save_violation(db, record)
    assert saved.id is not None
    row = db.get(m.OccupationRecord, saved.id)
    assert row.plate == "京A88888"
    assert row.rule_hit == m.RULE_FUEL_OCCUPY
    assert row.pile_id == "PILE-004"
    assert row.notify_status == "未提醒"
    assert row.notify_time is None


def test_mark_notified_updates_status_and_time(db):
    saved = save_violation(db, judge(fuel("京A88888"), db))
    when = datetime(2026, 9, 8, 10, 0, 30)

    assert mark_notified(db, saved.id, m.NOTIFY_SENT, when) is True

    row = db.get(m.OccupationRecord, saved.id)
    assert row.notify_status == "已提醒"
    assert row.notify_time == when


def test_mark_notified_missing_record_returns_false(db):
    assert mark_notified(db, 999999, m.NOTIFY_FAILED) is False
