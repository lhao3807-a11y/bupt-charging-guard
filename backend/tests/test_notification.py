"""统一提醒服务测试（契约 v1.9 §6.3 / 第 3 周 T2）。

钉死七件事（对应验收 A06 / A07）：

1. **成功**：库里的状态来自**发送器的实际执行**，不是回显请求
2. **已成功不再发**（`already_sent`），重复人工请求返回已有结果
3. **无手机号 / 车主已删除** → 记失败 + 原因，且**不消耗尝试次数**（补绑定后还能重试）
4. **失败后可重试**，累计 `notify_attempts`；恢复后重试成功
5. **上限**：达到 `NOTIFY_MAX_ATTEMPTS` 后明确 `exhausted`，不再自动发送
6. **并发**：两个请求抢同一条记录，只有一个真正发送（乐观锁 rowcount）
7. **重启**：尝试次数与结果持久化，新会话（= 新进程）读到的是同一份

另有一条纪律：**沙箱不联网**。本文件所有用例都不产生网络访问。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app import models as m
from app import notification
from app.db import Base
from app.rule_engine import judge, save_violation
from app.schemas import RecognitionResult, VType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

NOW = datetime(2026, 9, 8, 10, 0, 0)


@pytest.fixture()
def db():
    """独立内存库（建表 + 种子）。"""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    m.seed_db(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def file_db(tmp_path):
    """**文件库** fixture —— 用于「重启恢复」与「并发」两个需要多会话的场景。"""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'notify.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, future=True)
    session = factory()
    m.seed_db(session)
    try:
        yield factory
    finally:
        session.close()
        engine.dispose()


def _make_violation(db, plate: str = "京A88888", vtype: VType = VType.燃油) -> int:
    """造一条已落库的违规记录，返回它的 id。"""
    hit = judge(
        RecognitionResult(
            plate=plate, vtype=vtype, confidence=1.0, bbox=[0, 0, 0, 0], frame_time=NOW
        ),
        db,
    )
    assert hit is not None
    return save_violation(db, hit).id


def _row(db, record_id: int) -> m.OccupationRecord:
    return db.get(m.OccupationRecord, record_id)


# ---------------------------------------------------------------------------
# 1) 成功：状态来自发送器
# ---------------------------------------------------------------------------
def test_send_success_writes_status_and_attempt(db):
    record_id = _make_violation(db)
    outcome = notification.send_for_record(db, record_id, sender=notification.SandboxSender("ok"))

    assert outcome.status == m.NOTIFY_SENT
    assert outcome.attempts == 1
    assert outcome.reason is None
    assert outcome.already_sent is False
    assert outcome.message and "京A88888" in outcome.message

    row = _row(db, record_id)
    assert row.notify_status == m.NOTIFY_SENT
    assert row.notify_attempts == 1
    assert row.notify_time is not None
    assert row.notify_error is None


def test_send_logs_masked_phone(db, caplog):
    """日志里出现脱敏号码，不出现完整号码（凭据目录里也不能有真号）。"""
    record_id = _make_violation(db)
    with caplog.at_level("INFO", logger="app.sms_sandbox"):
        notification.send_for_record(db, record_id, sender=notification.SandboxSender("ok"))

    text = caplog.text
    assert "138****0004" in text
    assert "13800000004" not in text


def test_mask_phone():
    assert notification.mask_phone("13800000004") == "138****0004"
    assert notification.mask_phone(None) is None
    assert notification.mask_phone("123") == "123****"


def test_build_message_per_rule():
    assert "燃油车" in notification.build_message(
        plate="京A88888", pile_id="PILE-004", rule_hit=m.RULE_FUEL_OCCUPY
    )
    assert "未充电" in notification.build_message(
        plate="京AD24680", pile_id="PILE-003", rule_hit=m.RULE_ABNORMAL
    )
    assert "已充满" in notification.build_message(
        plate="京AD67890", pile_id="PILE-002", rule_hit=m.RULE_FULL_NOT_MOVED
    )


# ---------------------------------------------------------------------------
# 2) 已成功不再发（A07）
# ---------------------------------------------------------------------------
def test_already_sent_is_not_resent(db):
    record_id = _make_violation(db)
    sender = notification.SandboxSender("ok")
    notification.send_for_record(db, record_id, sender=sender)

    again = notification.send_for_record(db, record_id, sender=sender)
    assert again.already_sent is True
    assert again.status == m.NOTIFY_SENT
    assert again.attempts == 1, "已成功的记录不应再消耗尝试次数"
    assert _row(db, record_id).notify_attempts == 1


# ---------------------------------------------------------------------------
# 3) 无手机号 / 车主已删除（A06）
# ---------------------------------------------------------------------------
def test_missing_phone_fails_without_consuming_attempt(db):
    record_id = _make_violation(db)
    vehicle = db.get(m.Vehicle, "京A88888")
    vehicle.phone = None
    db.commit()

    outcome = notification.send_for_record(db, record_id, sender=notification.SandboxSender("ok"))
    assert outcome.status == m.NOTIFY_FAILED
    assert outcome.reason == notification.REASON_NO_PHONE
    assert outcome.attempts == 0, "缺手机号不是一次发送尝试，不该消耗次数"

    row = _row(db, record_id)
    assert row.notify_attempts == 0
    assert row.notify_error == notification.REASON_NO_PHONE


def test_retry_succeeds_after_phone_is_bound(db):
    """**失败恢复**：补绑定手机号后人工重试成功，且不新增违规记录（A06）。"""
    record_id = _make_violation(db)
    vehicle = db.get(m.Vehicle, "京A88888")
    vehicle.phone = None
    db.commit()

    failed = notification.send_for_record(db, record_id, sender=notification.SandboxSender("ok"))
    assert failed.status == m.NOTIFY_FAILED

    vehicle.phone = "13800000004"
    db.commit()

    retried = notification.send_for_record(db, record_id, sender=notification.SandboxSender("ok"))
    assert retried.status == m.NOTIFY_SENT
    assert retried.attempts == 1
    assert db.query(m.OccupationRecord).count() == 1, "重试不该新增违规记录"


def test_deleted_vehicle_fails_with_reason(db):
    record_id = _make_violation(db)
    plate = _row(db, record_id).plate
    db.delete(db.get(m.Vehicle, plate))
    db.commit()

    outcome = notification.send_for_record(db, record_id, sender=notification.SandboxSender("ok"))
    assert outcome.status == m.NOTIFY_FAILED
    assert outcome.reason == notification.REASON_VEHICLE_MISSING


# ---------------------------------------------------------------------------
# 4) 失败 → 重试成功；5) 上限（A07）
# ---------------------------------------------------------------------------
def test_failed_then_retry_succeeds_accumulates_attempts(db):
    record_id = _make_violation(db)

    first = notification.send_for_record(db, record_id, sender=notification.SandboxSender("fail"))
    assert first.status == m.NOTIFY_FAILED
    assert first.attempts == 1
    assert first.reason == notification.REASON_SANDBOX_FAIL
    assert _row(db, record_id).notify_error == notification.REASON_SANDBOX_FAIL

    second = notification.send_for_record(db, record_id, sender=notification.SandboxSender("ok"))
    assert second.status == m.NOTIFY_SENT
    assert second.attempts == 2
    assert _row(db, record_id).notify_error is None


def test_exhausted_after_max_attempts(db, monkeypatch):
    monkeypatch.setenv(notification.MAX_ATTEMPTS_ENV, "2")
    record_id = _make_violation(db)
    fail = notification.SandboxSender("fail")

    notification.send_for_record(db, record_id, sender=fail)
    notification.send_for_record(db, record_id, sender=fail)

    third = notification.send_for_record(db, record_id, sender=notification.SandboxSender("ok"))
    assert third.exhausted is True
    assert third.status == m.NOTIFY_FAILED
    assert third.attempts == 2
    assert _row(db, record_id).notify_attempts == 2, "达到上限后不再自增"


def test_max_attempts_comes_from_deployment_config(monkeypatch):
    """上限来自环境变量，**不进 system_config**（契约 §7 红线）。"""
    monkeypatch.delenv(notification.MAX_ATTEMPTS_ENV, raising=False)
    assert notification.max_attempts() == notification.DEFAULT_MAX_ATTEMPTS

    monkeypatch.setenv(notification.MAX_ATTEMPTS_ENV, "5")
    assert notification.max_attempts() == 5

    monkeypatch.setenv(notification.MAX_ATTEMPTS_ENV, "not-a-number")
    assert notification.max_attempts() == notification.DEFAULT_MAX_ATTEMPTS


def test_sandbox_sender_is_deterministic(monkeypatch):
    """同样的配置 → 同样的结果；非法取值直接报错，不静默兜底。"""
    monkeypatch.setenv(notification.SANDBOX_RESULT_ENV, "fail")
    assert notification.default_sender().send(phone="13800000004", content="x") is False

    monkeypatch.setenv(notification.SANDBOX_RESULT_ENV, "whatever")
    with pytest.raises(ValueError, match="沙箱结果非法"):
        notification.default_sender()


# ---------------------------------------------------------------------------
# 6) 并发（A07）
# ---------------------------------------------------------------------------
def test_claim_attempt_loses_when_another_session_won(file_db):
    """**乐观锁本体**：两个会话各自读到 attempts=0，只有一个能把 0→1 抢到手。

    `UPDATE ... WHERE notify_attempts = 0` 的 rowcount 就是判据 —— 不依赖 SQLite
    不支持的行级锁，MySQL 8 下同样成立（契约 §6.3 口径 3）。
    """
    session_a, session_b = file_db(), file_db()
    record_id = _make_violation(session_a)
    row_a = session_a.get(m.OccupationRecord, record_id)
    row_b = session_b.get(m.OccupationRecord, record_id)
    assert row_a.notify_attempts == row_b.notify_attempts == 0

    assert notification._claim_attempt(session_b, row_b) == 1
    assert notification._claim_attempt(session_a, row_a) is None, "过期的那一路必须抢不到"


def test_concurrent_request_reflects_db_truth(file_db):
    """并发的**结果**必须来自库：后到的那一路看到「已提醒」而不是自己那份过期快照。"""
    session_a = file_db()
    record_id = _make_violation(session_a)

    session_b = file_db()
    ok = notification.send_for_record(session_b, record_id, sender=notification.SandboxSender("ok"))
    assert ok.status == m.NOTIFY_SENT

    session_a.expire_all()  # 模拟「新的一次请求」重新读库
    later = notification.send_for_record(
        session_a, record_id, sender=notification.SandboxSender("ok")
    )
    assert later.already_sent is True
    assert _row(session_a, record_id).notify_attempts == 1


# ---------------------------------------------------------------------------
# 7) 重启恢复（A07）
# ---------------------------------------------------------------------------
def test_attempts_survive_process_restart(file_db):
    """进程重启（= 新会话）后，已成功状态与尝试次数都在，不会被清零重发。"""
    first_session = file_db()
    record_id = _make_violation(first_session)
    notification.send_for_record(
        first_session, record_id, sender=notification.SandboxSender("fail")
    )
    first_session.close()

    restarted = file_db()  # 模拟进程重启后的新会话
    row = _row(restarted, record_id)
    assert row.notify_attempts == 1
    assert row.notify_status == m.NOTIFY_FAILED

    again = notification.send_for_record(
        restarted, record_id, sender=notification.SandboxSender("ok")
    )
    assert again.attempts == 2


def test_restart_does_not_resend_already_sent(file_db):
    session = file_db()
    record_id = _make_violation(session)
    notification.send_for_record(session, record_id, sender=notification.SandboxSender("ok"))
    session.close()

    restarted = file_db()
    outcome = notification.send_for_record(
        restarted, record_id, sender=notification.SandboxSender("ok")
    )
    assert outcome.already_sent is True
    assert _row(restarted, record_id).notify_attempts == 1


# ---------------------------------------------------------------------------
# 记录不存在 / current_status
# ---------------------------------------------------------------------------
def test_unknown_record_raises_record_not_found(db):
    with pytest.raises(notification.RecordNotFound):
        notification.send_for_record(db, 999999)


def test_current_status_does_not_send(db):
    """`retry=false` 只回显，**不产生任何副作用**。"""
    record_id = _make_violation(db)
    outcome = notification.current_status(db, record_id)

    assert outcome.status == m.NOTIFY_PENDING
    assert outcome.attempts == 0
    row = _row(db, record_id)
    assert row.notify_attempts == 0
    assert row.notify_time is None


def test_notify_time_records_last_attempt(db):
    record_id = _make_violation(db)
    when = NOW + timedelta(minutes=5)
    notification.send_for_record(db, record_id, sender=notification.SandboxSender("fail"), now=when)
    assert _row(db, record_id).notify_time == when


def test_sandbox_never_touches_network(monkeypatch):
    """**纪律防回归**：沙箱发送器不得访问网络。任何 socket 创建都视为失败。"""
    import socket

    def _boom(*args, **kwargs):  # pragma: no cover - 只在被调用时才需要
        raise AssertionError("沙箱发送器不应产生网络访问")

    monkeypatch.setattr(socket, "create_connection", _boom)
    # 不抛错即通过
    assert notification.SandboxSender("ok").send(phone="13800000004", content="测试") is True


def test_module_defaults_match_contract(monkeypatch):
    """默认值与契约 §7 表格一致（改默认值必须同步改契约与文档）。"""
    monkeypatch.delenv(notification.MAX_ATTEMPTS_ENV, raising=False)
    monkeypatch.delenv(notification.SANDBOX_RESULT_ENV, raising=False)
    assert notification.DEFAULT_MAX_ATTEMPTS == 3
    assert notification.default_sender().result == notification.SANDBOX_OK
