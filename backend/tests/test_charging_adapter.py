"""充电状态适配器与四场景测试（第 3 周 T5 / 验收 A02–A04、A12）。

钉死四件事：

1. **外部状态映射**：登记过的词映射正确，**未登记的词明确报错**（不静默兜底成「空闲」）
2. **四个场景各自命中预期规则**：燃油① / 久停② / 充满超时③ / 正常④ 不违规
3. **演示语义不越界**：燃油车摆不进「正常充电」，新能源车摆不进「燃油占位」
4. **确定性**：同样的输入与时刻 → 同样的结果（阈值来自库，改阈值场景跟着变）

场景是**夹具**，不是判定逻辑本身；判定一律交回 `rule_engine.judge()`。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app import charging_adapter as ca
from app import models as m
from app.db import Base
from app.rule_engine import judge
from app.schemas import RecognitionResult
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

AT = datetime(2026, 9, 8, 10, 0, 0)


@pytest.fixture()
def db():
    """内存库 + 种子车辆/配置，但**清空种子桩**。

    种子桩已经把 4 块车牌绑定到 PILE-001..004 上；本文件的用例要自己摆桩，
    留着种子桩会让「按车牌反查桩」查出两行（`MultipleResultsFound`）。
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    m.seed_db(session)
    session.query(m.ChargingPile).delete()
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _pile(db, pile_id: str = "PILE-D1") -> m.ChargingPile:
    row = m.ChargingPile(pile_id=pile_id, status=m.PILE_IDLE)
    db.add(row)
    db.commit()
    return row


def _rule_hit(db, pile: m.ChargingPile, at: datetime = AT) -> int | None:
    """按桩当前状态走**真实规则引擎**判定（只读）。"""
    vehicle = db.get(m.Vehicle, pile.bound_plate)
    hit = judge(
        RecognitionResult(
            plate=pile.bound_plate,
            vtype=vehicle.vtype,
            confidence=1.0,
            bbox=[0, 0, 0, 0],
            frame_time=at,
        ),
        db,
        now=at,
    )
    return None if hit is None else hit.rule_hit


# ---------------------------------------------------------------------------
# 1) 外部状态映射
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "external,expected",
    [
        ("available", m.PILE_IDLE),
        ("  Charging ", m.PILE_CHARGING),
        ("FULL", m.PILE_FULL),
        ("charging_completed", m.PILE_FULL),
        ("suspended", m.PILE_IDLE),
    ],
)
def test_map_status_known_words(external, expected):
    assert ca.map_status(external) == expected


def test_map_status_unknown_word_raises():
    """未登记的状态词**明确报错**：静默当成「空闲」会让演示里的状态说不清来源。"""
    with pytest.raises(ca.UnknownChargingStatus, match="未知的外部充电状态"):
        ca.map_status("plugged_but_broken")


# ---------------------------------------------------------------------------
# 2) 四场景各自命中预期规则
# ---------------------------------------------------------------------------
def test_fuel_occupy_scenario_hits_rule1(db):
    pile = _pile(db)
    ca.apply_scenario(pile, "京A88888", ca.SCENARIO_FUEL, AT, db)

    assert pile.status == m.PILE_IDLE
    assert pile.scenario == ca.SCENARIO_FUEL
    assert _rule_hit(db, pile) == m.RULE_FUEL_OCCUPY


def test_idle_park_scenario_hits_rule2(db):
    pile = _pile(db)
    ca.apply_scenario(pile, "京AD24680", ca.SCENARIO_IDLE, AT, db)

    # 默认「阈值 + 10 分钟」：阈值 30 → 到达时间应落在 09:20
    assert pile.start_time == AT - timedelta(minutes=40)
    assert _rule_hit(db, pile) == m.RULE_ABNORMAL


def test_full_timeout_scenario_hits_rule3(db):
    pile = _pile(db)
    ca.apply_scenario(pile, "京AD67890", ca.SCENARIO_FULL, AT, db)

    assert pile.end_time == AT - timedelta(minutes=40)
    assert _rule_hit(db, pile) == m.RULE_FULL_NOT_MOVED


def test_normal_scenario_hits_nothing(db):
    """**验收 A04**：正常充电 → 不违规、不落库、不调用发送器。"""
    pile = _pile(db)
    ca.apply_scenario(pile, "京AD12345", ca.SCENARIO_NORMAL, AT, db)

    assert pile.status == m.PILE_CHARGING
    assert _rule_hit(db, pile) is None


@pytest.mark.parametrize("minutes", [0, 29, 30])
def test_idle_park_below_or_equal_threshold_does_not_hit(db, minutes):
    """**验收 A02**：阈值**前**与**恰好相等**都不提醒（判定是严格大于）。"""
    pile = _pile(db)
    ca.apply_scenario(pile, "京AD24680", ca.SCENARIO_IDLE, AT, db, overshoot_min=minutes - 30)

    assert pile.start_time == AT - timedelta(minutes=minutes)
    assert _rule_hit(db, pile) is None


def test_full_timeout_equal_threshold_does_not_hit(db):
    """**验收 A03**：恰好等于阈值不命中，超过才命中。"""
    pile = _pile(db)
    ca.apply_scenario(pile, "京AD67890", ca.SCENARIO_FULL, AT, db, overshoot_min=0)
    assert _rule_hit(db, pile) is None

    ca.apply_scenario(pile, "京AD67890", ca.SCENARIO_FULL, AT, db, overshoot_min=1)
    assert _rule_hit(db, pile) == m.RULE_FULL_NOT_MOVED


# ---------------------------------------------------------------------------
# 3) 演示语义不越界
# ---------------------------------------------------------------------------
def test_fuel_car_cannot_be_seeded_as_normal_charging(db):
    """**T5 明确要求**：燃油车不能被演示成正常充电。"""
    pile = _pile(db)
    with pytest.raises(ValueError, match="需要新能源车"):
        ca.apply_scenario(pile, "京A88888", ca.SCENARIO_NORMAL, AT, db)


def test_ev_cannot_be_seeded_as_fuel_occupy(db):
    pile = _pile(db)
    with pytest.raises(ValueError, match="需要燃油车"):
        ca.apply_scenario(pile, "京AD24680", ca.SCENARIO_FUEL, AT, db)


def test_unknown_scenario_raises(db):
    pile = _pile(db)
    with pytest.raises(ValueError, match="未知场景"):
        ca.apply_scenario(pile, "京AD24680", "made_up", AT, db)


def test_holds_charging_prevents_auto_charging(db):
    """久停/燃油占位场景的桩**不会被模拟器推进成充电中**（A02 的前提）。"""
    pile = _pile(db)
    ca.apply_scenario(pile, "京AD24680", ca.SCENARIO_IDLE, AT, db)
    assert ca.holds_charging(pile) is True

    ca.apply_scenario(pile, "京AD12345", ca.SCENARIO_NORMAL, AT, db)
    assert ca.holds_charging(pile) is False


# ---------------------------------------------------------------------------
# 4) 确定性与阈值来源
# ---------------------------------------------------------------------------
def test_scenario_follows_config_threshold(db):
    """阈值改成 120 → 场景的到达时间跟着变成 130 分钟前，演示仍然命中。

    若夹具写死 30 分钟，改完阈值演示就散了（契约 §7：阈值只从 `system_config` 来）。
    """
    pile = _pile(db)
    cfg = db.get(m.SystemConfig, "abnormal_park_min")
    cfg.value = "120"
    db.commit()

    ca.apply_scenario(pile, "京AD24680", ca.SCENARIO_IDLE, AT, db)
    assert pile.start_time == AT - timedelta(minutes=130)
    assert _rule_hit(db, pile) == m.RULE_ABNORMAL


def test_scenario_is_deterministic():
    """同样的输入与时刻 → 同样的结果（A12 通过标准）。"""

    def _run() -> tuple[str, datetime, datetime | None]:
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
            row = m.ChargingPile(pile_id="PILE-D9", status=m.PILE_IDLE)
            session.add(row)
            session.commit()
            oid = ca.apply_scenario(row, "京AD67890", ca.SCENARIO_FULL, AT, session)
            return oid, row.start_time, row.end_time
        finally:
            session.close()
            engine.dispose()

    assert _run() == _run()


def test_scenario_assigns_occupancy_identity(db):
    """场景布置也走 `begin_occupancy`，判重键才有身份（不绕过占用生命周期）。"""
    pile = _pile(db)
    oid = ca.apply_scenario(pile, "京AD24680", ca.SCENARIO_IDLE, AT, db)
    assert oid == pile.occupancy_id
    assert oid.startswith("PILE-D1@")
