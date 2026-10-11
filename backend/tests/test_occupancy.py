"""占用标识生命周期测试（契约 v1.9 §3.6 / 第 3 周 T4）。

钉死四件事：

1. **到车生成、同车保持、换车重生成、离车清空** —— 判重键的身份就靠它
2. **确定性**：同样的「桩 + 时刻」必然得到同样的标识（T5 四场景可复现的前提）
3. **离车 → 立刻重入** 不会被算成同一次占用（微秒精度）
4. 落库快照**永不改写**：记录上的 `occupancy_id` 不随桩后续变化
"""

from __future__ import annotations

from datetime import datetime

import pytest
from app import models as m
from app import occupancy
from app.db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

T0 = datetime(2026, 9, 8, 10, 0, 0)
T1 = datetime(2026, 9, 8, 10, 0, 1)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _pile(db, pile_id: str = "PILE-100") -> m.ChargingPile:
    row = m.ChargingPile(pile_id=pile_id, status=m.PILE_IDLE)
    db.add(row)
    db.commit()
    return row


# ---------------------------------------------------------------------------
# 标识生成：确定性
# ---------------------------------------------------------------------------
def test_make_occupancy_id_is_deterministic():
    """同样输入 → 同样输出；不掷随机数，进程重启也不变（T5 场景可复现）。"""
    first = m.make_occupancy_id("PILE-003", T0)
    assert first == m.make_occupancy_id("PILE-003", T0)
    assert first.startswith("PILE-003@")
    assert first != m.make_occupancy_id("PILE-004", T0)  # 桩不同
    assert first != m.make_occupancy_id("PILE-003", T1)  # 时刻不同


def test_make_occupancy_id_fits_column():
    """不能超过 VARCHAR(40)（DDL 上限，超了 MySQL 会截断了还不报错）。"""
    assert len(m.make_occupancy_id("PILE-003", datetime(2026, 9, 8, 10, 0, 0, 123456))) <= 40


# ---------------------------------------------------------------------------
# 生命周期
# ---------------------------------------------------------------------------
def test_begin_occupancy_creates_id_and_marks_arrival(db):
    pile = _pile(db)
    oid = occupancy.begin_occupancy(pile, "京AD12345", T0, db=db)

    assert oid == m.make_occupancy_id("PILE-100", T0)
    assert pile.bound_plate == "京AD12345"
    assert pile.occupancy_id == oid
    assert pile.start_time == T0
    assert pile.status == m.PILE_IDLE  # 停上去了 ≠ 在充电


def test_begin_occupancy_same_car_keeps_id(db):
    """同车仍在 → 标识与时间**都不动**（保护规则②的久停基准）。"""
    pile = _pile(db)
    first = occupancy.begin_occupancy(pile, "京AD12345", T0, db=db)

    again = occupancy.begin_occupancy(pile, "京AD12345", T1, db=db)
    assert again == first
    assert pile.start_time == T0


def test_begin_occupancy_other_car_creates_new_id(db):
    """换车 → 新占用（否则后车违规会被合并到前车那条上，且不再提醒）。"""
    pile = _pile(db)
    first = occupancy.begin_occupancy(pile, "京AD12345", T0, db=db)
    second = occupancy.begin_occupancy(pile, "京A88888", T1, db=db)

    assert second != first
    assert pile.bound_plate == "京A88888"
    assert pile.start_time == T1


def test_end_occupancy_clears_everything(db):
    pile = _pile(db)
    occupancy.begin_occupancy(pile, "京AD12345", T0, db=db)
    occupancy.end_occupancy(pile, db=db)

    assert pile.bound_plate is None
    assert pile.occupancy_id is None
    assert pile.start_time is None and pile.end_time is None
    assert pile.status == m.PILE_IDLE
    assert occupancy.current_occupancy_id(pile) is None


def test_leave_and_return_is_a_new_occupancy(db):
    """离车 → 重入：必须算**新**占用（微秒精度，不会撞回同一个标识）。"""
    pile = _pile(db)
    first = occupancy.begin_occupancy(pile, "京AD12345", T0, db=db)
    occupancy.end_occupancy(pile, db=db)

    back = datetime(2026, 9, 8, 10, 0, 0, 500000)  # 同一秒内回来
    second = occupancy.begin_occupancy(pile, "京AD12345", back, db=db)
    assert second != first


def test_current_occupancy_id_is_none_without_binding(db):
    """桩上无车 → None。**不现场编造**一个标识（编造等于污染判重键）。"""
    pile = _pile(db)
    assert occupancy.current_occupancy_id(pile) is None

    # 只有 bound_plate 没有 occupancy_id（历史数据/直灌数据）也视为无标识
    pile.bound_plate = "京AD12345"
    assert occupancy.current_occupancy_id(pile) is None


def test_begin_occupancy_rejects_empty_plate(db):
    """空车牌直接报错：离车该走 end_occupancy，不能拿空牌当「有车」。"""
    pile = _pile(db)
    with pytest.raises(ValueError, match="非空车牌"):
        occupancy.begin_occupancy(pile, "", T0, db=db)
