"""规则引擎**边界用例** —— PLAN §2.2 任务 2.6 要求的四类：

1. 桩不存在（车辆不在任何 ``bound_plate`` / 桩表被清空）
2. 车牌未绑定（ Unknown plate，路径与「桩不存在」相同但语义不同，两处都要守住）
3. 阈值为 0（严格大于才命中：恰好 0 分钟不命中，超过哪怕 1 秒就命中）
4. 时间倒挂（``frame_time`` 早于 ``start_time`` / ``end_time``，不得命中也不得抛错）

主路径（四规则命中 + 正常 null）见 ``test_rule_engine.py``。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app import models as m
from app.db import Base
from app.rule_engine import judge
from app.schemas import RecognitionResult, VType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 种子数据的桩状态在 NOW 上分别对应四条规则（同 test_rule_engine.py 的口径）
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
        engine.dispose()


def rec(plate: str, vtype: VType, frame_time: datetime = NOW) -> RecognitionResult:
    return RecognitionResult(
        plate=plate, vtype=vtype, confidence=0.97, bbox=[1, 2, 3, 4], frame_time=frame_time
    )


def set_threshold(db, key: str, value: str) -> None:
    row = db.query(m.SystemConfig).filter(m.SystemConfig.key == key).one()
    row.value = value
    db.commit()


# ---------------------------------------------------------------------------
# 1) 桩不存在 / 2) 车牌未绑定
# ---------------------------------------------------------------------------
def test_unknown_plate_returns_none(db):
    """车牌未绑定任何桩（Unknown plate）→ None，不是异常。"""
    assert judge(rec("京Z99999", VType.新能源), db) is None
    assert judge(rec("京Z99999", VType.燃油), db) is None


def test_empty_pile_table_returns_none(db):
    """桩表被清空（桩不存在）→ None，不抛错（如桩维护下线场景）。"""
    db.query(m.ChargingPile).delete()
    db.commit()
    assert judge(rec("京AD12345", VType.新能源), db) is None
    assert judge(rec("京A88888", VType.燃油), db) is None


# ---------------------------------------------------------------------------
# 3) 阈值为 0：判定条件是「严格大于」
# ---------------------------------------------------------------------------
def test_zero_idle_threshold_hits_only_after_strictly_positive(db):
    """规则② abnormal_park_min=0：同刻不命中；晚 1 秒即命中。"""
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-003").one()
    set_threshold(db, "abnormal_park_min", "0")

    at_arrival = datetime(2026, 9, 8, 8, 30, 0)  # == start_time，elapsed=0
    pile_copy = pile
    assert judge(rec(pile_copy.bound_plate, VType.新能源, at_arrival), db) is None

    one_sec_later = at_arrival + timedelta(seconds=1)  # elapsed≈0.017 > 0
    hit = judge(rec(pile_copy.bound_plate, VType.新能源, one_sec_later), db)
    assert hit is not None and hit.rule_hit == m.RULE_ABNORMAL


def test_zero_full_threshold_hits_only_after_strictly_positive(db):
    """规则③ full_timeout_min=0：同充满时刻不命中；晚 1 秒即命中。"""
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-002").one()
    set_threshold(db, "full_timeout_min", "0")

    at_full = datetime(2026, 9, 8, 9, 20, 0)  # == end_time，elapsed=0
    assert judge(rec(pile.bound_plate, VType.新能源, at_full), db) is None

    one_sec_later = at_full + timedelta(seconds=1)
    hit = judge(rec(pile.bound_plate, VType.新能源, one_sec_later), db)
    assert hit is not None and hit.rule_hit == m.RULE_FULL_NOT_MOVED


# ---------------------------------------------------------------------------
# 4) 时间倒挂：frame_time 早于基准时间（时钟回拨 / 数据错误）
# ---------------------------------------------------------------------------
def test_frame_time_before_arrival_does_not_hit(db):
    """规则②：frame_time 早于 start_time（倒挂 30 分钟）→ 时长按 0 → 不命中。"""
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-003").one()
    before_arrival = pile.start_time - timedelta(minutes=30)
    assert judge(rec(pile.bound_plate, VType.新能源, before_arrival), db) is None


def test_frame_time_before_full_time_does_not_hit(db):
    """规则③：frame_time 早于 end_time（倒挂 30 分钟）→ 不命中。"""
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-002").one()
    before_full = pile.end_time - timedelta(minutes=30)
    assert judge(rec(pile.bound_plate, VType.新能源, before_full), db) is None


def test_backwards_time_never_raises(db):
    """任意倒挂输入都不应抛异常（防御性：宁可漏报不可崩溃）。"""
    pile2 = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-002").one()
    pile3 = db.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-003").one()
    weird = datetime(2000, 1, 1)
    assert judge(rec(pile2.bound_plate, VType.新能源, weird), db) is None
    assert judge(rec(pile3.bound_plate, VType.新能源, weird), db) is None
