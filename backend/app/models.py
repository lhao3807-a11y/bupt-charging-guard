"""SQLAlchemy ORM 模型 —— 与 docs/CONTRACT.md §3 四表一一对应。

设计约定（CONTRACT §2「开发期 SQLite 约束」）：
- 开发期连 SQLite，目标库 MySQL 8；换库只改 app/db.py 的 DATABASE_URL。
- `vtype` / `status` / `notify_status` 在 MySQL DDL 里是 ENUM，在此统一映射为
  ``String`` —— 枚举合法性由 Pydantic 层（app/schemas.py）校验。
  **禁止在业务代码里依赖数据库原生 ENUM 行为**，否则换库必炸。
- 建表语句的正式交付物是 ``backend/sql/schema.sql``（MySQL 8 语法）；
  本文件的 ``init_db()`` / ``seed_db()`` 仅用于开发期 SQLite 等价验证，
  种子数据与 schema.sql 保持一致。

维护人：汤瑾睿
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# ---------------------------------------------------------------------------
# 枚举取值（与 CONTRACT §3 的 ENUM 定义逐字一致）
# ---------------------------------------------------------------------------
VTYPE_NEW_ENERGY = "新能源"
VTYPE_FUEL = "燃油"
VTYPES = (VTYPE_NEW_ENERGY, VTYPE_FUEL)

PILE_IDLE = "空闲"
PILE_CHARGING = "充电中"
PILE_FULL = "已充满"
PILE_STATUSES = (PILE_IDLE, PILE_CHARGING, PILE_FULL)

NOTIFY_PENDING = "未提醒"
NOTIFY_SENT = "已提醒"
NOTIFY_FAILED = "失败"
NOTIFY_STATUSES = (NOTIFY_PENDING, NOTIFY_SENT, NOTIFY_FAILED)

# rule_hit 取值（CONTRACT §3.3）
RULE_NORMAL = 0  # 正常
RULE_FUEL_OCCUPY = 1  # 燃油车占充电位
RULE_ABNORMAL = 2  # 新能源车未充电且久停
RULE_FULL_NOT_MOVED = 3  # 新能源车充满超时未移车


# ---------------------------------------------------------------------------
# 1. vehicle　车辆信息
# ---------------------------------------------------------------------------
class Vehicle(Base):
    __tablename__ = "vehicle"

    plate: Mapped[str] = mapped_column(String(15), primary_key=True)
    vtype: Mapped[str] = mapped_column(String(10), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(50), default=None)
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ---------------------------------------------------------------------------
# 2. charging_pile　充电桩状态（模拟）
# ---------------------------------------------------------------------------
class ChargingPile(Base):
    """充电桩。

    - ``bound_plate``：当前占用该桩的车牌。充电车与占位车（含燃油车）都写入这里，
      规则引擎即以 ``bound_plate`` 反查「这辆车停在哪个桩」。
    - ``start_time``：绑定 / 到达该桩的时间。新能源车停着不充电（``status=空闲``）时，
      规则②以 ``now - start_time > abnormal_park_min`` 判定「异常占位 · 久停」。
    - ``end_time``：充满时间，规则③以 ``now - end_time > full_timeout_min`` 判定。
    """

    __tablename__ = "charging_pile"

    pile_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default=PILE_IDLE)
    bound_plate: Mapped[str | None] = mapped_column(
        String(15),
        ForeignKey("vehicle.plate", onupdate="CASCADE", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, default=None)


# ---------------------------------------------------------------------------
# 3. occupation_record　违规记录
# ---------------------------------------------------------------------------
class OccupationRecord(Base):
    __tablename__ = "occupation_record"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    plate: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    vtype: Mapped[str] = mapped_column(String(10), nullable=False)
    pile_id: Mapped[str | None] = mapped_column(String(20), default=None)
    rule_hit: Mapped[int] = mapped_column(Integer, nullable=False, default=RULE_NORMAL)
    occur_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notify_status: Mapped[str] = mapped_column(String(10), nullable=False, default=NOTIFY_PENDING)
    notify_time: Mapped[datetime | None] = mapped_column(DateTime, default=None)


# ---------------------------------------------------------------------------
# 4. system_config　系统参数
# ---------------------------------------------------------------------------
class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(30), primary_key=True)
    value: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(String(100), default=None)


# ---------------------------------------------------------------------------
# 建表 / 种子（开发期 SQLite 等价验证用；与 backend/sql/schema.sql 保持一致）
# ---------------------------------------------------------------------------
#: 契约 §7 默认阈值（分钟）——仅作为种子数据，业务代码一律查库，不得直接引用
DEFAULT_CONFIG = (
    ("full_timeout_min", "30", "充满超时阈值（分钟）：已充满后超过该时长未移车即命中规则③"),
    ("abnormal_park_min", "30", "异常占位久停阈值（分钟）：未充电停放超过该时长即命中规则②"),
    ("recognition_mode", "stub", "识别桩模式：stub=读标注（默认，demo 稳定）/ real=真实 CV 模型"),
)

#: 种子车辆（与 schema.sql 的 INSERT 一致）
SEED_VEHICLES = (
    ("京AD12345", VTYPE_NEW_ENERGY, "汤瑾睿", "13800000001"),
    ("京AD67890", VTYPE_NEW_ENERGY, "吕浩", "13800000002"),
    ("京AD24680", VTYPE_NEW_ENERGY, "吴和庆", "13800000003"),
    ("京A88888", VTYPE_FUEL, "张伟", "13800000004"),
)

#: 种子充电桩（与 schema.sql 的 INSERT 一致）
SEED_PILES = (
    # pile_id, status, bound_plate, start_time, end_time
    ("PILE-001", PILE_CHARGING, "京AD12345", datetime(2026, 9, 8, 9, 50), None),
    ("PILE-002", PILE_FULL, "京AD67890", datetime(2026, 9, 8, 8, 0), datetime(2026, 9, 8, 9, 20)),
    ("PILE-003", PILE_IDLE, "京AD24680", datetime(2026, 9, 8, 8, 30), None),
    ("PILE-004", PILE_IDLE, "京A88888", datetime(2026, 9, 8, 9, 0), None),
)


def init_db(engine=None) -> None:
    """按 ORM 模型建表（开发期 SQLite 等价验证；正式交付物是 schema.sql）。"""
    if engine is None:
        from app.db import engine as default_engine

        engine = default_engine
    Base.metadata.create_all(bind=engine)


def seed_db(session) -> None:
    """灌入与 schema.sql 一致的种子数据；已存在则跳过。"""
    if session.query(SystemConfig).count() == 0:
        session.add_all(SystemConfig(key=k, value=v, note=n) for k, v, n in DEFAULT_CONFIG)
    if session.query(Vehicle).count() == 0:
        session.add_all(
            Vehicle(plate=p, vtype=t, owner=o, phone=ph, created_at=datetime(2026, 9, 1, 9, 0))
            for p, t, o, ph in SEED_VEHICLES
        )
        session.flush()
    if session.query(ChargingPile).count() == 0:
        session.add_all(
            ChargingPile(pile_id=pid, status=st, bound_plate=bp, start_time=s, end_time=e)
            for pid, st, bp, s, e in SEED_PILES
        )
    session.commit()


def setup_sqlite_db(engine=None):
    """建表 + 灌种子，返回 SessionLocal。供联调/脚本一键初始化开发库。"""
    from app.db import SessionLocal

    init_db(engine)
    session = SessionLocal()
    seed_db(session)
    return session
