"""短信沙箱执行器 + 统一提醒服务 —— 契约 v1.9 §6.3（第 3 周 T2）。

**与第 1 周「短信沙箱」的区别**：v1.2 的 `/api/notify` 是「前端说已提醒就写已提醒」，
它只能证明接口通了，**不能证明提醒发生过**。本模块把「结果」的产出权收回到服务端：

```text
记录 → 取车主手机号 → 生成短信 → 沙箱执行（确定性）→ 把**实际结果**写回 occupation_record
```

沙箱**不访问运营商网络**（第 3 周不依赖真实账号，见 `WEEK3_PLAN.md` §2「不作为本周门槛的工作」），
但**结果与次数是真的**：成功/失败、尝试次数、失败原因全部持久化，进程重启不清零。

四条硬口径（改动前先改契约）：

1. **已成功不再发**：同一记录发送成功后，重复请求返回 `already_sent`，**不重发**。
2. **次数有上限**：`NOTIFY_MAX_ATTEMPTS`（环境变量，默认 3）。**刻意不放 `system_config`** ——
   那张表是业务判定阈值的唯一来源（契约 §7 红线），发送上限属部署配置。
3. **并发靠数据库状态约束**：用 `UPDATE ... WHERE notify_attempts = n` 的 `rowcount` 做乐观锁，
   不依赖 SQLite 不支持的行级锁，MySQL 8 下同样成立；抢不到的那一路返回 `conflict` 且不发送。
4. **缺手机号不算一次尝试**：车主没绑定手机号 / 车主被删除 → 记 `失败` + 原因，
   **不消耗尝试次数**，补绑定后人工重试仍可成功（验收 A06）。

维护人：汤瑾睿
"""

from __future__ import annotations

import dataclasses
import logging
import os
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app import models as m
from app.schemas import RULE_LABELS

logger = logging.getLogger("app.sms_sandbox")

#: 部署配置：单条记录的发送尝试上限（环境变量，不进 system_config）
MAX_ATTEMPTS_ENV = "NOTIFY_MAX_ATTEMPTS"
DEFAULT_MAX_ATTEMPTS = 3

#: 部署配置：沙箱发送器的确定性结果（ok / fail），用于演示「失败 → 恢复」
SANDBOX_RESULT_ENV = "SMS_SANDBOX_RESULT"
SANDBOX_OK = "ok"
SANDBOX_FAIL = "fail"
SANDBOX_RESULTS = (SANDBOX_OK, SANDBOX_FAIL)

#: 失败原因（人话，直接展示给前端）
REASON_NO_PHONE = "车主未绑定手机号"
REASON_VEHICLE_MISSING = "车主信息不存在（车辆已删除）"
REASON_SANDBOX_FAIL = "沙箱发送失败"
REASON_EXHAUSTED = f"已达发送尝试上限（{MAX_ATTEMPTS_ENV}）"
REASON_CONFLICT = "并发请求已被另一个请求处理"

#: 短信签名（沙箱文案，与真实模板结构保持一致，便于 T8 换真实供应商）
SIGN = "【桩点北邮】"


class RecordNotFound(LookupError):
    """违规记录不存在 —— 路由层据此返回 404。"""


@dataclass(frozen=True)
class NotifyOutcome:
    """一次提醒请求的结果。**每个字段都能在库里找到出处**，不靠调用方描述。"""

    record_id: int
    status: str  # 未提醒 / 已提醒 / 失败
    attempts: int  # 累计尝试次数
    max_attempts: int
    reason: str | None  # 失败原因（人话）
    already_sent: bool = False  # 此前已成功，本次未重发
    exhausted: bool = False  # 已达上限，本次未发送
    conflict: bool = False  # 并发冲突，本次未发送
    phone_masked: str | None = None  # 脱敏号码，仅用于日志/展示
    message: str | None = None  # 短信内容
    notify_time: datetime | None = None


def max_attempts() -> int:
    """读取部署配置的尝试上限；环境变量非法时回退默认值（不抛错阻断演示）。"""
    raw = os.environ.get(MAX_ATTEMPTS_ENV, "").strip()
    if not raw:
        return DEFAULT_MAX_ATTEMPTS
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r 不是整数，回退默认值 %d", MAX_ATTEMPTS_ENV, raw, DEFAULT_MAX_ATTEMPTS)
        return DEFAULT_MAX_ATTEMPTS
    return value if value > 0 else DEFAULT_MAX_ATTEMPTS


def mask_phone(phone: str | None) -> str | None:
    """手机号脱敏：``13800000001`` → ``138****0001``。日志与页面都不显示完整号码。"""
    if not phone:
        return None
    if len(phone) <= 7:
        return f"{phone[:3]}****"
    return f"{phone[:3]}****{phone[-4:]}"


def build_message(*, plate: str, pile_id: str | None, rule_hit: int) -> str:
    """按命中规则生成短信内容（沙箱文案，T8 换真实供应商时只改这里）。"""
    label = RULE_LABELS.get(rule_hit, "违规")
    where = f"{pile_id}" if pile_id else "充电车位"
    if rule_hit == m.RULE_FUEL_OCCUPY:
        return f"{SIGN}您的车辆{plate}（燃油车）占用{where}新能源充电车位，请立即驶离。"
    if rule_hit == m.RULE_ABNORMAL:
        return f"{SIGN}您的车辆{plate}停在{where}且长时间未充电，请尽快充电或驶离。"
    if rule_hit == m.RULE_FULL_NOT_MOVED:
        return f"{SIGN}您的车辆{plate}在{where}已充满，请及时移车，避免占用充电车位。"
    return f"{SIGN}您的车辆{plate}在{where}存在{label}行为，请及时处理。"


class SandboxSender:
    """确定性沙箱发送器：**同样的输入必然同样的输出**，不掷随机数、不联网。

    - 默认结果 ``ok``；环境变量 ``SMS_SANDBOX_RESULT=fail`` 时恒失败（用于演示失败与恢复）。
    - 测试可直接注入实例，不必改环境变量（避免测试之间互相污染）。
    """

    def __init__(self, result: str | None = None) -> None:
        if result is None:
            result = os.environ.get(SANDBOX_RESULT_ENV, SANDBOX_OK).strip().lower() or SANDBOX_OK
        if result not in SANDBOX_RESULTS:
            raise ValueError(
                f"沙箱结果非法：{result!r}（可选 {'/'.join(SANDBOX_RESULTS)}）"
                f"——请检查环境变量 {SANDBOX_RESULT_ENV}"
            )
        self.result = result

    def send(self, *, phone: str, content: str) -> bool:
        """执行一次「发送」。沙箱只记录日志并确定性返回，不访问运营商网络。"""
        ok = self.result == SANDBOX_OK
        logger.info(
            "[SMS-SANDBOX] phone=%s result=%s content=%s",
            mask_phone(phone),
            "OK" if ok else "FAIL",
            content,
        )
        return ok

    @property
    def forced_fail(self) -> bool:
        return self.result == SANDBOX_FAIL


def default_sender() -> SandboxSender:
    """按当前部署配置构造发送器（每次调用都重读环境变量，便于演示中途切换）。"""
    return SandboxSender()


def _load(db: Session, record_id: int) -> m.OccupationRecord:
    row = db.get(m.OccupationRecord, record_id)
    if row is None:
        raise RecordNotFound(f"违规记录不存在：id={record_id}")
    return row


def current_status(db: Session, record_id: int) -> NotifyOutcome:
    """只回显状态，**不发起发送**（`retry=false` 走这里，供第 2 页查状态用）。"""
    row = _load(db, record_id)
    limit = max_attempts()
    return NotifyOutcome(
        record_id=row.id,
        status=row.notify_status,
        attempts=row.notify_attempts,
        max_attempts=limit,
        reason=row.notify_error,
        already_sent=row.notify_status == m.NOTIFY_SENT,
        exhausted=row.notify_attempts >= limit and row.notify_status != m.NOTIFY_SENT,
        phone_masked=None,
        message=None,
        notify_time=row.notify_time,
    )


def _claim_attempt(db: Session, row: m.OccupationRecord) -> int | None:
    """乐观锁占位：把 `notify_attempts` 从 n 推到 n+1，成功返回 `n+1`，失败返回 `None`。

    **为什么不用 `SELECT ... FOR UPDATE`**：SQLite 不支持行级锁，用它等于把「能在本机跑」
    和「能在 MySQL 上跑」写成两套代码。条件更新的 `rowcount` 在两种库上语义一致。
    """
    before = row.notify_attempts
    updated = (
        db.query(m.OccupationRecord)
        .filter(
            m.OccupationRecord.id == row.id,
            m.OccupationRecord.notify_attempts == before,
        )
        .update({m.OccupationRecord.notify_attempts: before + 1}, synchronize_session=False)
    )
    db.commit()
    return before + 1 if updated == 1 else None


def _write_result(
    db: Session,
    row_id: int,
    *,
    attempt: int,
    status: str,
    when: datetime,
    error: str | None,
) -> None:
    """把执行结果写回记录；`attempt` 作为并发护栏（只改自己抢到的那一次）。"""
    (
        db.query(m.OccupationRecord)
        .filter(
            m.OccupationRecord.id == row_id,
            m.OccupationRecord.notify_attempts == attempt,
        )
        .update(
            {
                m.OccupationRecord.notify_status: status,
                m.OccupationRecord.notify_time: when,
                m.OccupationRecord.notify_error: error,
            },
            synchronize_session=False,
        )
    )
    db.commit()


def send_for_record(
    db: Session,
    record_id: int,
    *,
    sender: SandboxSender | None = None,
    now: datetime | None = None,
) -> NotifyOutcome:
    """对**一条**违规记录执行一次提醒；返回结果，并把结果写回库。

    :raises RecordNotFound: 记录不存在（路由层 → 404）。
    """
    row = _load(db, record_id)
    limit = max_attempts()
    when = now or datetime.now()
    active = sender or default_sender()

    # ① 已成功 → 不重发（验收 A07）
    if row.notify_status == m.NOTIFY_SENT:
        return NotifyOutcome(
            record_id=row.id,
            status=row.notify_status,
            attempts=row.notify_attempts,
            max_attempts=limit,
            reason=None,
            already_sent=True,
            phone_masked=None,
            message=build_message(plate=row.plate, pile_id=row.pile_id, rule_hit=row.rule_hit),
            notify_time=row.notify_time,
        )

    # ② 已达上限 → 不再自动发送（验收 A07）
    if row.notify_attempts >= limit:
        return NotifyOutcome(
            record_id=row.id,
            status=row.notify_status,
            attempts=row.notify_attempts,
            max_attempts=limit,
            reason=row.notify_error or REASON_EXHAUSTED,
            exhausted=True,
            notify_time=row.notify_time,
        )

    vehicle = db.get(m.Vehicle, row.plate)

    # ③ 无手机号 / 车主已删除 → 记失败但**不消耗尝试次数**（验收 A06：补绑定后还能重试）
    if vehicle is None:
        _write_result(
            db,
            row.id,
            attempt=row.notify_attempts,
            status=m.NOTIFY_FAILED,
            when=when,
            error=REASON_VEHICLE_MISSING,
        )
        return NotifyOutcome(
            record_id=row.id,
            status=m.NOTIFY_FAILED,
            attempts=row.notify_attempts,
            max_attempts=limit,
            reason=REASON_VEHICLE_MISSING,
            notify_time=when,
        )
    if not vehicle.phone:
        _write_result(
            db,
            row.id,
            attempt=row.notify_attempts,
            status=m.NOTIFY_FAILED,
            when=when,
            error=REASON_NO_PHONE,
        )
        return NotifyOutcome(
            record_id=row.id,
            status=m.NOTIFY_FAILED,
            attempts=row.notify_attempts,
            max_attempts=limit,
            reason=REASON_NO_PHONE,
            notify_time=when,
        )

    # ④ 抢一次尝试名额（并发护栏）
    attempt = _claim_attempt(db, row)
    if attempt is None:
        # 抢不到说明另一方刚刚动过这条记录 —— 回报**库里的真实状态**，
        # 而不是自己那份过期快照，否则前端会看到「冲突」与「未提醒」同时出现。
        db.refresh(row)
        return dataclasses.replace(
            current_status(db, row.id), conflict=True, reason=REASON_CONFLICT
        )

    content = build_message(plate=row.plate, pile_id=row.pile_id, rule_hit=row.rule_hit)
    ok = active.send(phone=vehicle.phone, content=content)
    status = m.NOTIFY_SENT if ok else m.NOTIFY_FAILED
    error = None if ok else REASON_SANDBOX_FAIL

    _write_result(db, row.id, attempt=attempt, status=status, when=when, error=error)

    logger.info(
        "[SMS-SANDBOX] record_id=%s occupancy_id=%s rule_hit=%s phone=%s attempt=%s/%s result=%s reason=%s",
        row.id,
        row.occupancy_id,
        row.rule_hit,
        mask_phone(vehicle.phone),
        attempt,
        limit,
        "OK" if ok else "FAIL",
        error or "-",
    )

    return NotifyOutcome(
        record_id=row.id,
        status=status,
        attempts=attempt,
        max_attempts=limit,
        reason=error,
        already_sent=False,
        exhausted=False,
        conflict=False,
        phone_masked=mask_phone(vehicle.phone),
        message=content,
        notify_time=when,
    )
