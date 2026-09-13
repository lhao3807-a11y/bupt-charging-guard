"""短信沙箱 —— 对应 POST /api/notify（CONTRACT §6.3）。

职责：按记录 ``id`` 更新 ``occupation_record.notify_status`` / ``notify_time``，
并写沙箱日志。**不调真实短信 API**（MVP 边界，见契约 §1）。

入参口径（2026-09-13 与吕浩对齐，契约升 v1.2）：
    ``{"id": 1, "notify_status": "已提醒"}``
``id`` 取自 ``/api/judge`` 返回的记录。
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import rule_engine
from app.db import get_db
from app.schemas import NotifyReq, NotifyResp

router = APIRouter(tags=["notify"])

logger = logging.getLogger("app.sms_sandbox")


@router.post("/api/notify", response_model=NotifyResp, summary="违规 → 短信沙箱（写库+日志）")
def notify(req: NotifyReq, db: Session = Depends(get_db)) -> NotifyResp:
    """更新提醒状态并落沙箱日志；记录不存在 → ``404``。"""
    when = datetime.now()
    found = rule_engine.mark_notified(db, req.id, req.notify_status.value, when=when)

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"违规记录不存在：id={req.id}。请确认该记录已由 /api/judge 落库。",
        )

    # 短信沙箱：只记日志，不真发短信
    logger.info(
        "[SMS-SANDBOX] record_id=%s status=%s at=%s",
        req.id,
        req.notify_status.value,
        when.isoformat(),
    )

    return NotifyResp(notify_status=req.notify_status)
