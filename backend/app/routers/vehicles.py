"""车辆信息 CRUD —— 对应 /api/vehicles（CONTRACT §6.6，v1.3 新增）。

背景（契约 §6.6）：§1.1 把「车辆信息管理」列为第 1 周范围，要求表格列 = `vehicle`
全字段且可增删改，但 §6 此前未定义 `vehicle` 的读接口，前端只能退化为 `localStorage`。

```text
GET    /api/vehicles               车辆列表（分页 + plate/vtype/owner 筛选）
POST   /api/vehicles               新增（201；车牌已存在 → 409）
PUT    /api/vehicles/{plate}       更新（仅 vtype/owner/phone，车牌不可改）
DELETE /api/vehicles/{plate}       删除（204，无 body）
```

**三条坑（契约 §6.6 点名，均有测试守）**：

1. **`plate` 是主键，不可改**。路径参数仅用于定位；`VehicleUpdate` 类型上根本不含
   `plate`，从类型层面杜绝改主键。
2. **`POST` 时车牌已存在 → `409`**（不是 `400`），前端靠状态码区分「车牌已存在」。
3. **`DELETE` 不级联删违规记录**：`occupation_record` 是事实记录，删车不该抹掉它。
   该列也**没有**外键约束（见 `models.py`），否则历史记录会被连带删除。
   —— 但 `charging_pile.bound_plate` 的 FK 声明了 `ondelete="SET NULL"`，
   而 SQLite 默认不强制外键，故删除时**显式**把关联桩的 `bound_plate` 置空，
   保证 SQLite 与 MySQL 行为一致，不留下指向已删车的悬空车牌。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.query import enum_exact, like_ci
from app.schemas import (
    Vehicle,
    VehicleCreate,
    VehiclePage,
    VehicleUpdate,
    normalize_plate,
)

router = APIRouter(tags=["vehicles"])


def _to_schema(row: m.Vehicle) -> Vehicle:
    """ORM 行 → 读模型（显式构造，与 records.py 风格一致）。"""
    return Vehicle(
        plate=row.plate,
        vtype=row.vtype,
        owner=row.owner,
        phone=row.phone,
        created_at=row.created_at,
    )


def _find_vehicle(db: Session, plate: str) -> m.Vehicle:
    """按车牌定位车辆；不存在 → 404（PUT / DELETE 共用）。

    路径参数先按与入库同一套规则统一化（去空白 + 转大写），
    这样前端从列表里拿到的车牌能原样用于更新/删除。
    """
    key = normalize_plate(plate)
    row = db.query(m.Vehicle).filter(m.Vehicle.plate == key).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"车辆不存在：{plate}")
    return row


@router.get("/api/vehicles", response_model=VehiclePage, summary="车辆列表（分页 + 筛选）")
def list_vehicles(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=200, description="每页条数"),
    plate: str | None = Query(None, description="车牌号，模糊匹配（忽略大小写）"),
    vtype: str | None = Query(None, description="车型，精确匹配（新能源 / 燃油）"),
    owner: str | None = Query(None, description="车主，模糊匹配"),
    db: Session = Depends(get_db),
) -> VehiclePage:
    """分页返回车辆，按 `created_at` 倒序（新录入在前），`total` 为**筛选后**总数。"""
    query = db.query(m.Vehicle)

    # 枚举参数：空串（前端「全部」）视为不筛选，拼错才 422
    vtype_value = enum_exact(vtype, m.VTYPES, "vtype")

    if plate and plate.strip():
        query = query.filter(like_ci(m.Vehicle.plate, plate))
    if vtype_value is not None:
        query = query.filter(m.Vehicle.vtype == vtype_value)
    if owner and owner.strip():
        query = query.filter(like_ci(m.Vehicle.owner, owner))

    total = query.count()  # 筛选后的总数（契约 §6.6 口径 5）

    rows = (
        query.order_by(m.Vehicle.created_at.desc(), m.Vehicle.plate.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return VehiclePage(items=[_to_schema(row) for row in rows], total=total, page=page, size=size)


@router.post(
    "/api/vehicles",
    response_model=Vehicle,
    status_code=status.HTTP_201_CREATED,
    summary="新增车辆（车牌已存在 → 409）",
)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)) -> Vehicle:
    """新增车辆；`created_at` 由服务端生成，请求体不传（契约 §6.6 口径 4）。"""
    if db.query(m.Vehicle).filter(m.Vehicle.plate == payload.plate).one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"车牌号已存在：{payload.plate}",
        )

    row = m.Vehicle(
        plate=payload.plate,
        vtype=payload.vtype.value,
        owner=payload.owner,
        phone=payload.phone,
        created_at=datetime.now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_schema(row)


@router.put(
    "/api/vehicles/{plate}",
    response_model=Vehicle,
    summary="更新车辆（车牌不可改）",
)
def update_vehicle(plate: str, payload: VehicleUpdate, db: Session = Depends(get_db)) -> Vehicle:
    """更新 `vtype` / `owner` / `phone`；**车牌的路径参数只用于定位，改不了主键**。

    只覆盖请求里**显式给出**的字段（`exclude_unset`）：前端永远三个都发，但这样
    也能安全支持「只改手机号」这类局部更新，且显式传 `null` 仍可清空字段。
    """
    row = _find_vehicle(db, plate)

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field == "vtype":
            value = value.value
        setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return _to_schema(row)


@router.delete(
    "/api/vehicles/{plate}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除车辆（不级联删违规记录）",
)
def delete_vehicle(plate: str, db: Session = Depends(get_db)) -> Response:
    """删除车辆，返回 `204` 无 body。

    - `occupation_record` 中该车牌的历史违规记录**原样保留**：历史是事实记录，
      但此后不再有手机号，**无法自动提醒**（前端确认弹窗已说明）。
    - 关联桩的 `bound_plate` 显式置空，避免 SQLite 下留下悬空车牌（见模块 docstring）。
    """
    row = _find_vehicle(db, plate)

    db.query(m.ChargingPile).filter(m.ChargingPile.bound_plate == row.plate).update(
        {"bound_plate": None}
    )
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
