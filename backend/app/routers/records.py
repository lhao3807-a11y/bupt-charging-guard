"""违规记录分页查询 —— 对应 GET /api/records（CONTRACT §6.4）。

返回 ``{items, total, page, size}``，``total`` **反映筛选后的总数**（前端分页条依赖它，
不是全表总数）。默认按 ``occur_time`` 倒序（最新违规在前），与后台页直觉一致。

筛选（契约 v1.3 §6.4）：7 个可选参数，多参数之间 **AND**；不传（或传空串，前端清空筛选框
常见）即跳过 —— 无筛选时行为与 v1.2 全表分页完全一致。

- ``plate`` / ``pile_id``：模糊匹配，忽略大小写
- ``vtype`` / ``rule_hit`` / ``notify_status``：精确匹配
- ``start_time`` / ``end_time``：``occur_time`` 的闭区间上下界；只给日期时按**当日 23:59:59.999999**
  解释上界，避免「选同一天查不到数据」（契约 §6.4 特意点名的坑）
- ``start_time > end_time``：自然返回空列表，不报错（契约要求）
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import NotifyStatus, RecordPage, ViolationRecord, VType

router = APIRouter(tags=["records"])

#: ``YYYY-MM-DD`` 的长度；用于识别「只给日期」的入参
_DATE_ONLY_LEN = 10
_END_OF_DAY = "23:59:59.999999"


def _parse_time_bound(raw: str, *, upper: bool) -> datetime:
    """把查询串解析成 ``occur_time`` 的时间边界（含边界）。

    只给日期（``2026-09-19``）时：下界补 ``00:00:00``，上界补 ``23:59:59.999999``。
    其余按 ISO 8601 解析；格式非法 → 422（不静默忽略，免得前端筛了却没生效）。
    """
    text = raw.strip()
    if len(text) == _DATE_ONLY_LEN:
        text = f"{text} {_END_OF_DAY}" if upper else f"{text} 00:00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"时间格式非法：{raw!r}。支持 ISO 8601（如 2026-09-19T10:00:00）"
                "或纯日期（如 2026-09-19）。"
            ),
        ) from exc


def _like_ci(column, value: str):
    """大小写不敏感的模糊匹配。

    显式套 ``lower()``，不依赖各库 ``LIKE`` 的默认排序规则（SQLite ASCII 不敏感、
    MySQL 取决于 collation）—— 换库行为一致。中文不受 lower 影响，故 ``京A`` 仍能
    匹配 ``京AD12345``。
    """
    return func.lower(column).like(f"%{value.strip().lower()}%")


@router.get("/api/records", response_model=RecordPage, summary="后台查询违规记录（分页 + 筛选）")
def list_records(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=200, description="每页条数"),
    plate: str | None = Query(None, description="车牌号，模糊匹配（忽略大小写）"),
    vtype: VType | None = Query(None, description="车型，精确匹配"),
    pile_id: str | None = Query(None, description="桩 ID，模糊匹配（忽略大小写）"),
    rule_hit: int | None = Query(None, ge=0, le=3, description="命中规则 0~3，精确匹配"),
    notify_status: NotifyStatus | None = Query(None, description="提醒状态，精确匹配"),
    start_time: str | None = Query(
        None, description="occur_time 下界（含），ISO 8601 或 YYYY-MM-DD"
    ),
    end_time: str | None = Query(
        None, description="occur_time 上界（含），纯日期按当日 23:59:59.999999"
    ),
    db: Session = Depends(get_db),
) -> RecordPage:
    """按筛选条件分页返回违规记录，``total`` 为**筛选后**总数（契约 §6.4）。"""
    query = db.query(m.OccupationRecord)

    if plate and plate.strip():
        query = query.filter(_like_ci(m.OccupationRecord.plate, plate))
    if vtype is not None:
        query = query.filter(m.OccupationRecord.vtype == vtype.value)
    if pile_id and pile_id.strip():
        query = query.filter(_like_ci(m.OccupationRecord.pile_id, pile_id))
    if rule_hit is not None:
        query = query.filter(m.OccupationRecord.rule_hit == rule_hit)
    if notify_status is not None:
        query = query.filter(m.OccupationRecord.notify_status == notify_status.value)
    if start_time and start_time.strip():
        query = query.filter(
            m.OccupationRecord.occur_time >= _parse_time_bound(start_time, upper=False)
        )
    if end_time and end_time.strip():
        query = query.filter(
            m.OccupationRecord.occur_time <= _parse_time_bound(end_time, upper=True)
        )

    # 先 filter 再 count —— total 必须是筛选后的总数（契约 §6.4 明确）
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
