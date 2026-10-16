"""规则终版评审的**行为测试**（第 3 周 T6 / 验收 A08、A13）。

真值表与三人确认记录见 `docs/week3/T6_RULE_TRUTH_TABLE.md`；本文件钉死其中
「可写成断言」的四条语义：

1. **改阈值不回溯历史**：已落库的记录（规则、命中时间、提醒结果）**一个字节都不变**
2. **已发送成功的提醒不因改阈值重发**：历史结果不被新一轮判定推翻
3. **新判定用新阈值**：对**仍在占用**的车，下一次判定立刻采用新值
4. **缺参数不得静默兜底**：`system_config` 缺键 → `ConfigMissingError`（接口 500），
   非法值也要明确报错，而不是悄悄用 30

另附「车型未知 / 未绑定桩 / 多车同帧」的可解释性断言：
这些情况一律**返回 None（不可判定）**，不猜桩、不猜车型。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app import models as m
from app import notification
from app.db import Base
from app.rule_engine import ConfigMissingError, judge, save_violation
from app.schemas import RecognitionResult, VType
from sqlalchemy import create_engine
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

NOW = datetime(2026, 9, 8, 10, 0, 0)


@pytest.fixture()
def db():
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


def ev(plate: str, at: datetime = NOW) -> RecognitionResult:
    return RecognitionResult(
        plate=plate, vtype=VType.新能源, confidence=0.97, bbox=[1, 2, 3, 4], frame_time=at
    )


def _hit_and_save(db, plate: str = "京AD24680", at: datetime = NOW):
    hit = judge(ev(plate, at), db, now=at)
    assert hit is not None
    return save_violation(db, hit)


def _set_threshold(db, key: str, value: str) -> None:
    row = db.get(m.SystemConfig, key)
    row.value = value
    db.commit()


# ---------------------------------------------------------------------------
# 1) 改阈值不回溯历史（A08）
# ---------------------------------------------------------------------------
def test_threshold_change_does_not_rewrite_history(db):
    """阈值从 30 改成 120：**已落库的记录一个字段都不许变**。

    历史记录是「当时按当时的阈值判出来的证据」，回溯重算等于把证据改没了 ——
    第 2/4 页的数字会随配置漂移，验收也就无从核对。
    """
    saved = _hit_and_save(db)  # PILE-003 久停 90 分钟 > 30 → 规则②
    snapshot = (
        saved.rule_hit,
        saved.occur_time,
        saved.notify_status,
        saved.notify_attempts,
        saved.pile_id,
    )

    _set_threshold(db, "abnormal_park_min", "120")

    row = db.get(m.OccupationRecord, saved.id)
    assert (row.rule_hit, row.occur_time, row.notify_status, row.notify_attempts, row.pile_id) == (
        snapshot
    )


def test_threshold_change_does_not_resend_already_sent(db):
    """**已成功提醒的记录**，改阈值后重新判定也不会再发一次。"""
    saved = _hit_and_save(db)
    notification.send_for_record(db, saved.id, sender=notification.SandboxSender("ok"))

    _set_threshold(db, "abnormal_park_min", "120")

    again = notification.send_for_record(db, saved.id, sender=notification.SandboxSender("ok"))
    assert again.already_sent is True
    assert db.get(m.OccupationRecord, saved.id).notify_attempts == 1


# ---------------------------------------------------------------------------
# 2) 新判定用新阈值（A08 的另一半）
# ---------------------------------------------------------------------------
def test_loosened_threshold_stops_new_hits_for_still_occupied_car(db):
    """阈值放宽到 120：同一辆车仍在占用 → **下一次判定不再命中**。"""
    assert _hit_and_save(db).rule_hit == m.RULE_ABNORMAL

    _set_threshold(db, "abnormal_park_min", "120")
    assert judge(ev("京AD24680", NOW), db, now=NOW) is None


def test_tightened_threshold_hits_earlier(db):
    """阈值收紧到 10：原本不命中的 20 分钟久停，现在命中。"""
    pile = db.get(m.ChargingPile, "PILE-003")
    pile.start_time = NOW - timedelta(minutes=20)
    db.commit()
    assert judge(ev("京AD24680", NOW), db, now=NOW) is None

    _set_threshold(db, "abnormal_park_min", "10")
    hit = judge(ev("京AD24680", NOW), db, now=NOW)
    assert hit is not None and hit.rule_hit == m.RULE_ABNORMAL


def test_tightened_threshold_creates_a_new_record_not_a_rewrite(db):
    """收紧阈值后命中 → **新增**一条记录，原记录保持原样（不是改写历史）。"""
    pile = db.get(m.ChargingPile, "PILE-003")
    pile.start_time = NOW - timedelta(minutes=90)
    db.commit()

    first = _hit_and_save(db)  # 阈值 30 → 命中
    _set_threshold(db, "abnormal_park_min", "10")
    # 同一占用 + 同一规则 → 判重键不变，仍复用（不会因为改阈值就多一条）
    second = _hit_and_save(db)
    assert second.id == first.id
    assert db.query(m.OccupationRecord).count() == 1


# ---------------------------------------------------------------------------
# 3) 缺参数不得静默兜底（契约 §7）
# ---------------------------------------------------------------------------
def test_missing_threshold_raises_config_missing_error(db):
    db.query(m.SystemConfig).filter(m.SystemConfig.key == "full_timeout_min").delete()
    db.commit()
    with pytest.raises(ConfigMissingError, match="full_timeout_min"):
        judge(ev("京AD67890"), db)


def test_non_integer_threshold_raises_config_missing_error(db):
    _set_threshold(db, "full_timeout_min", "三十分钟")
    with pytest.raises(ConfigMissingError, match="不是合法整数"):
        judge(ev("京AD67890"), db)


def test_missing_threshold_surfaces_as_500_not_silent_default(client, db_session):
    """接口层同样不兜底：缺阈值 → 500 且带上键名，前端/验收一眼能看到。"""
    db_session.query(m.SystemConfig).filter(m.SystemConfig.key == "abnormal_park_min").delete()
    db_session.commit()

    resp = client.post(
        "/api/judge",
        json={
            "plate": "京AD24680",
            "vtype": "新能源",
            "confidence": 0.97,
            "bbox": [1, 2, 3, 4],
            "frame_time": NOW.isoformat(),
        },
    )
    assert resp.status_code == 500
    assert "abnormal_park_min" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 4) 不可判定的情况：一律 None，不猜桩、不猜车型
# ---------------------------------------------------------------------------
def test_unregistered_plate_without_pile_returns_none(db):
    """未录入的车牌也没绑桩 → 不在判定范围（返回 None，不是异常、不猜车型）。"""
    pile = db.get(m.ChargingPile, "PILE-003")
    pile.bound_plate = "京Z99999"  # 未录入 vehicle 表的车
    db.commit()
    # 判定只对「桩上这辆车」有意义；这辆车换了牌就等于原车牌不再占用任何桩
    assert judge(ev("京AD24680"), db) is None


def test_plate_not_bound_to_any_pile_returns_none(db):
    """车牌没绑桩 → 不在本系统判定范围（不是错误）。"""
    assert judge(ev("京AD33333"), db) is None


def test_same_plate_bound_to_two_piles_is_not_silently_picked(db):
    """同一车牌绑了两个桩（数据错误）→ **明确报错**，不静默挑一个。

    挑一个就等于替运维做决定，而且第 2 页显示的桩 ID 可能与另一半数据对不上。
    """
    db.add(
        m.ChargingPile(
            pile_id="PILE-999",
            status=m.PILE_IDLE,
            bound_plate="京AD24680",  # 与 PILE-003 重复
            start_time=NOW - timedelta(hours=3),
        )
    )
    db.commit()
    with pytest.raises(MultipleResultsFound):
        judge(ev("京AD24680"), db)


def test_rule_labels_cover_all_hits():
    """四条规则的中文标签齐全（第 4 页图例与短信文案共用，缺一个就是空白图例）。"""
    from app.schemas import RULE_LABELS

    assert set(RULE_LABELS) == {0, 1, 2, 3}
    assert all(RULE_LABELS[i] for i in RULE_LABELS)
