"""SQLite + SQLAlchemy 等价验证 —— 对应 backend/sql/schema.sql（CONTRACT §2「方案 b」）。

验证目标：四表能建、种子能灌、按车牌能反查到桩状态、阈值能从库中读出。
MySQL 8 真机验证延至第 2 周接入真实库时执行（以 schema.sql 为准）。
"""

from __future__ import annotations

import pytest
from app import models as m
from app.db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db():
    """内存 SQLite + 建表 + 种子。"""
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


def test_tables_created_for_four_entities(db):
    """契约 §3 四表都能建、种子都灌得进去。"""
    assert db.query(m.Vehicle).count() == len(m.SEED_VEHICLES) == 4
    assert db.query(m.ChargingPile).count() == len(m.SEED_PILES) == 4
    assert db.query(m.SystemConfig).count() == len(m.DEFAULT_CONFIG) == 2
    assert db.query(m.OccupationRecord).count() == 0  # 违规记录由闭环产生


def test_seed_covers_all_pile_statuses(db):
    """种子须覆盖 空闲 / 充电中 / 已充满 三种状态（供四条规则各自动作）。"""
    statuses = {p.status for p in db.query(m.ChargingPile).all()}
    assert statuses == set(m.PILE_STATUSES)


def test_vtype_values_follow_contract(db):
    """车型只能是契约 §3.1 的两种取值。"""
    vtypes = {v.vtype for v in db.query(m.Vehicle).all()}
    assert vtypes == set(m.VTYPES)
    assert vtypes == {"新能源", "燃油"}


def test_lookup_pile_by_bound_plate(db):
    """规则引擎的桩关联口径：按 bound_plate 反查车辆所在桩。"""
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.bound_plate == "京AD12345").one()
    assert pile.pile_id == "PILE-001"
    assert pile.status == m.PILE_CHARGING


def test_fuel_vehicle_is_bound_to_pile_for_occupancy_rule(db):
    """燃油车占位场景：燃油车也写入 bound_plate，规则①才有桩可查。"""
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.bound_plate == "京A88888").one()
    assert pile.pile_id == "PILE-004"
    assert pile.status == m.PILE_IDLE

    vehicle = db.query(m.Vehicle).filter(m.Vehicle.plate == "京A88888").one()
    assert vehicle.vtype == m.VTYPE_FUEL
    assert vehicle.phone  # 有手机号才能发提醒


def test_config_thresholds_readable(db):
    """契约 §7：两项阈值必须从 system_config 读得到。"""
    cfg = {c.key: c.value for c in db.query(m.SystemConfig).all()}
    assert cfg["full_timeout_min"] == "30"
    assert cfg["abnormal_park_min"] == "30"


def test_every_seeded_pile_plate_exists_in_vehicle(db):
    """bound_plate 必须能在 vehicle 里找到（对应 MySQL 侧的外键约束）。"""
    plates = {v.plate for v in db.query(m.Vehicle).all()}
    for pile in db.query(m.ChargingPile).all():
        assert pile.bound_plate in plates, f"{pile.pile_id} 的车牌不在 vehicle 表中"


def test_seed_is_idempotent(db):
    """重复灌种子不应产生重复数据（联调脚本会反复调用）。"""
    before = db.query(m.Vehicle).count()
    m.seed_db(db)
    assert db.query(m.Vehicle).count() == before
