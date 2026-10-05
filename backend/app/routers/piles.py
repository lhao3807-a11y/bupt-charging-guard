"""充电桩列表 —— 对应 GET /api/piles（CONTRACT §6.7，v1.6 新增，供第 3 页）。

背景（契约 §6.7）：§1.1 第 3 页「充电状态展示」要求表格列 = `charging_pile` 全字段
（§3.5 已登记 P3 五列）并支持按状态筛选，但 §6 此前没有桩的读接口，前端只能写死假数据。

```text
GET /api/piles?page=&size=&status=&pile_id=   → PilePage
```

**两条容易踩的口径**：

1. **`summary` 是筛选后的计数**，不是全表计数。第 3 页的「状态总览卡」直接取它，
   若前端按全表算，就会出现「筛了充电中、总览卡还是 4 个桩」的错觉。
2. **`status` 用 `enum_exact` 规整**：空串（前端「全部」）视为不筛选，拼错才 422。
   与 §6.4 / §6.6 两个后台页保持同一手感（见 `app/query.py`）。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.query import enum_exact, like_ci
from app.schemas import PileChange, PileItem, PilePage, SimulateReq, SimulateResp
from app.simulator import advance

router = APIRouter(tags=["piles"])


def _to_schema(row: m.ChargingPile) -> PileItem:
    """ORM 行 → 读模型（显式构造，与 records.py / vehicles.py 风格一致）。"""
    return PileItem(
        pile_id=row.pile_id,
        status=row.status,
        bound_plate=row.bound_plate,
        start_time=row.start_time,
        end_time=row.end_time,
    )


def _build_summary(query, total: int) -> dict[str, int]:
    """按状态分组计数 —— **基于已筛选的 query**（契约 §6.7 口径 2）。

    未出现的状态补 0：第 3 页的三个总览卡永远有数字可显示，不必前端判空。
    """
    counts = dict(
        query.with_entities(m.ChargingPile.status, func.count())
        .group_by(m.ChargingPile.status)
        .all()
    )
    summary = {status: counts.get(status, 0) for status in m.PILE_STATUSES}
    summary["total"] = total
    return summary


@router.get("/api/piles", response_model=PilePage, summary="充电桩列表（状态筛选 + 计数总览）")
def list_piles(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=200, description="每页条数"),
    status: str | None = Query(None, description="运行状态，精确匹配（空闲 / 充电中 / 已充满）"),
    pile_id: str | None = Query(None, description="桩 ID，模糊匹配（忽略大小写）"),
    db: Session = Depends(get_db),
) -> PilePage:
    """分页返回充电桩，按 `pile_id` 升序；`summary` 为**筛选后**的各状态计数。"""
    query = db.query(m.ChargingPile)

    # 枚举参数：空串（前端「全部」）视为不筛选，拼错才 422
    status_value = enum_exact(status, m.PILE_STATUSES, "status")

    if status_value is not None:
        query = query.filter(m.ChargingPile.status == status_value)
    if pile_id and pile_id.strip():
        query = query.filter(like_ci(m.ChargingPile.pile_id, pile_id))

    total = query.count()
    summary = _build_summary(query, total)

    rows = query.order_by(m.ChargingPile.pile_id.asc()).offset((page - 1) * size).limit(size).all()

    return PilePage(
        items=[_to_schema(row) for row in rows],
        total=total,
        page=page,
        size=size,
        summary=summary,
    )


@router.post(
    "/api/piles/simulate",
    response_model=SimulateResp,
    summary="推进充电状态模拟器一步（演示用，契约 §6.10）",
)
def simulate_piles(
    payload: SimulateReq | None = None,
    db: Session = Depends(get_db),
) -> SimulateResp:
    """把桩状态按时间推进**一步**，让第 3 页能看到「状态在变」。

    - `at` 用于演示快进（把「现在」设为若干小时后，一次走完流转）；不传取服务端时钟。
    - 一次调用每个桩最多跳一档 —— 连续推进请多调几次（契约 §6.10 口径 1）。
    - 响应带 `statuses` 全量快照，前端不必再发一次 `GET /api/piles`。
    """
    body = payload or SimulateReq()
    moment = body.at
    if isinstance(moment, str):  # 理论上 Pydantic 已解析，兜住手改调用
        try:
            moment = datetime.fromisoformat(moment)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"时间格式非法：{moment!r}（支持 ISO 8601，如 2026-09-08T10:30:00）",
            ) from exc

    result = advance(db, now=moment)

    statuses = {
        row.pile_id: row.status
        for row in db.query(m.ChargingPile).order_by(m.ChargingPile.pile_id.asc()).all()
    }
    return SimulateResp(
        advanced_at=result.advanced_at,
        changed_count=result.changed_count,
        changes=[
            PileChange(
                pile_id=change.pile_id,
                from_status=change.from_status,
                to_status=change.to_status,
                reason=change.reason,
            )
            for change in result.changes
        ],
        statuses=statuses,
    )
