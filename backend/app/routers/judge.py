"""违规判定 —— 对应 POST /api/judge（CONTRACT §6.2）。

职责：入参 ``RecognitionResult`` → 调 ``rule_engine.judge()`` 判定 →
命中即落库（``rule_engine.save_violation()``，含同桩+同规则去重）→ 返回带 ``id`` 的
``ViolationRecord``；命中规则④（正常充电）返回 ``null``。

落库口径：**judge 命中即落库**（2026-09-13 与吕浩对齐）。
- 前端拿到返回的 ``id`` 后，可直接调 ``/api/notify`` 更新提醒状态、或查 ``/api/records``。
- 去重规则见 ``rule_engine.save_violation``：同 ``pile_id`` + 同 ``rule_hit`` 且
  仍未提醒时复用原记录，避免轮询产生重复行。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import rule_engine
from app.db import get_db
from app.schemas import RecognitionResult, ViolationRecord

router = APIRouter(tags=["judge"])


@router.post(
    "/api/judge",
    response_model=ViolationRecord | None,
    summary="识别结果 → 违规判定（命中即落库）",
)
def judge(
    recognition: RecognitionResult,
    db: Session = Depends(get_db),
) -> ViolationRecord | None:
    """四条规则判定；命中①②③ 落库并返回记录，规则④ 返回 ``null``。

    ``system_config`` 缺阈值 → ``500``。契约 §7 要求阈值必须来自该表，
    此处不静默兜底，让配置缺失暴露出来。
    """
    try:
        record = rule_engine.judge(recognition, db)
    except rule_engine.ConfigMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"系统参数缺失，无法判定：{exc}",
        ) from exc

    if record is None:
        return None

    return rule_engine.save_violation(db, record)
