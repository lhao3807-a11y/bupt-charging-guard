"""短信沙箱 —— 对应 POST /api/notify（契约 v1.9 §6.3，第 3 周重写）。

**v1.9 与 v1.2 的区别**：v1.2 是「前端提交 `notify_status`，服务端照抄进库」，
这样写出来的「已提醒」只证明接口通了，**不证明提醒真的发过** —— 第 3 周要做
「自动判定 → 自动提醒」，就必须让结果由**发送器的实际执行**产生。

```
请求 {id, retry}  ──▶  app/notification.send_for_record()
                            ├─ 取车主手机号（没有 → 失败 + 原因，不算一次尝试）
                            ├─ 抢一次尝试名额（乐观锁，防并发重复发送）
                            ├─ 沙箱执行（确定性，不联网）
                            └─ 把实际结果写回 occupation_record
响应 {notify_status, notify_attempts, reason, already_sent, exhausted, conflict}
```

`retry=false` 时**只回显状态、不发送**，供第 2 页在不触发副作用的前提下查状态。

**不调真实短信 API**（第 3 周边界）：`app/notification.SandboxSender` 是确定性的，
不访问运营商网络；T8 若要接真实供应商，替换该发送器即可，本路由无需改动。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import notification
from app.db import get_db
from app.schemas import NotifyReq, NotifyResp

router = APIRouter(tags=["notify"])


@router.post(
    "/api/notify",
    response_model=NotifyResp,
    summary="违规 → 短信沙箱执行并把结果写库（v1.9）",
)
def notify(req: NotifyReq, db: Session = Depends(get_db)) -> NotifyResp:
    """对指定记录发起一次提醒（或只回显状态）；记录不存在 → ``404``。

    - ``retry=true``（默认）：发起一次发送尝试；已成功过的记录**不发第二次**。
    - ``retry=false``：只回显当前状态，不产生任何副作用。
    - 请求里的 ``notify_status`` 是 v1.2 遗留字段，**服务端忽略**（契约 §6.3）。
    """
    try:
        if req.retry:
            outcome = notification.send_for_record(db, req.id)
        else:
            outcome = notification.current_status(db, req.id)
    except notification.RecordNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{exc}。请确认该记录已由 /api/judge 落库。",
        ) from exc

    return NotifyResp(
        id=outcome.record_id,
        notify_status=outcome.status,
        notify_attempts=outcome.attempts,
        max_attempts=outcome.max_attempts,
        reason=outcome.reason,
        already_sent=outcome.already_sent,
        exhausted=outcome.exhausted,
        conflict=outcome.conflict,
        message=outcome.message,
    )
