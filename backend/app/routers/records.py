"""违规记录分页查询 —— 对应 GET /api/records（CONTRACT §6.4）。

返回 ``{items, total, page, size}``，``total`` 供前端分页条使用。
默认按 ``occur_time`` 倒序（最新违规在前），与后台「违规记录查询」页直觉一致。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import RecordPage, ViolationRecord

router = APIRouter(tags=["records"])


@router.get("/api/records", response_model=RecordPage, summary="后台查询违规记录（分页）")
def list_records(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
) -> RecordPage:
    """分页返回违规记录，按 ``occur_time`` 倒序。"""
    query = db.query(m.OccupationRecord)
    total = query.count()

    rows = (
        query.order_by(m.OccupationRecord.occur_time.desc(), m.OccupationRecord.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = [
        ViolationRecord(
            id=row.id,
            plate=row.plate,
            vtype=row.vtype,
            pile_id=row.pile_id,
            rule_hit=row.rule_hit,
            occur_time=row.occur_time,
            notify_status=row.notify_status,
        )
        for row in rows
    ]

    return RecordPage(items=items, total=total, page=page, size=size)
