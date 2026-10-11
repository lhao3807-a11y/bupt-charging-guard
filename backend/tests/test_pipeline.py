"""自动闭环编排测试（契约 v1.9 §6.11 / 第 3 周 T3 / 验收 A01、A04、A05、A09、A10）。

钉死六件事：

1. **整链跑通**：帧 → 识别 → 判定 → 落库 → 沙箱发送，一条龙不需要人点
2. **正常不打扰**：规则④ 的帧不落库、**不调用发送器**（A04）
3. **无新帧也重判时间规则**：识别结果可复用，但久停/超时仍按当前时刻判（否则规则②③形同废止）
4. **单帧失败不中断**：坏帧只让自己失败，其余帧照常处理（A10）
5. **同次占用不重复提醒**：连跑 10 轮只有 1 条记录、1 次成功发送（A05）
6. **状态只读**：`GET /api/pipeline/status` 不产生任何写操作
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from app import models as m
from app import notification
from app import pipeline as pl
from app.db import Base
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

T_0950 = datetime(2026, 9, 8, 9, 50, 0)
T_1000 = datetime(2026, 9, 8, 10, 0, 0)

#: 与 algo/samples/labels/*.json 一一对应（stub 识别按文件名读标注）
FRAME_NORMAL = "001.jpg"  # 京AD12345 新能源 → PILE-001 充电中 → 规则④ 正常
FRAME_FUEL = "002.jpg"  # 京A88888 燃油 → PILE-004 → 规则①
FRAME_IDLE = "003.jpg"  # 京AD24680 新能源 → PILE-003 空闲久停 → 规则②
FRAME_MISSING_LABEL = "999.jpg"  # 没有同名标注 → 识别 404


class CountingSender(notification.SandboxSender):
    """记录调用次数的沙箱发送器 —— 用来证明「正常场景一次都没发」。"""

    def __init__(self, result: str = "ok") -> None:
        super().__init__(result)
        self.calls = 0

    def send(self, *, phone: str, content: str) -> bool:
        self.calls += 1
        return super().send(phone=phone, content=content)


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


@pytest.fixture()
def frames(tmp_path):
    """建一个临时取帧目录；文件名决定 stub 读哪份标注，内容随便。"""

    def _make(*names: str, with_content: bool = True) -> str:
        for name in names:
            (tmp_path / name).write_bytes(b"fake-jpeg-bytes" if with_content else b"")
        return str(tmp_path)

    return _make


def _worker(db, frame_dir, **kwargs) -> pl.Pipeline:
    return pl.Pipeline(db, frame_dir=frame_dir, **kwargs)


# ---------------------------------------------------------------------------
# 1) 整链跑通（A01）
# ---------------------------------------------------------------------------
def test_run_once_judges_persists_and_notifies(db, frames):
    frame_dir = frames(FRAME_FUEL)
    sender = CountingSender()

    run = _worker(db, frame_dir, sender=sender).run_once(now=T_1000)

    assert run.frame_count == 1
    assert run.recognized == 1
    assert run.violations == 1
    assert run.notified == 1
    assert sender.calls == 1

    frame = run.frames[0]
    assert frame.plate == "京A88888"
    assert frame.pile_id == "PILE-004"
    assert frame.rule_hit == m.RULE_FUEL_OCCUPY
    assert frame.record_id is not None
    assert frame.notify_status == m.NOTIFY_SENT

    row = db.get(m.OccupationRecord, frame.record_id)
    assert row.notify_status == m.NOTIFY_SENT and row.notify_attempts == 1


# ---------------------------------------------------------------------------
# 2) 正常场景不落库、不发送（A04）
# ---------------------------------------------------------------------------
def test_normal_frame_does_not_persist_or_send(db, frames):
    frame_dir = frames(FRAME_NORMAL)
    sender = CountingSender()

    run = _worker(db, frame_dir, sender=sender).run_once(now=T_1000)

    assert run.violations == 0
    assert run.notified == 0
    assert sender.calls == 0, "正常充电的帧不得调用发送器"
    assert db.query(m.OccupationRecord).count() == 0


# ---------------------------------------------------------------------------
# 3) 无新帧也要重判时间规则（T3 口径 1）
# ---------------------------------------------------------------------------
def test_unchanged_frame_reuses_recognition_but_rejudges_time(db, frames):
    """**防回归**：内容没变只省 CV，**时间规则必须按当前时刻重判**。

    若因为「没有新帧」就整帧跳过，规则②③永远等不到超时 —— 自动轮询等于只判规则①。
    """
    frame_dir = frames(FRAME_IDLE)  # PILE-003：08:30 到达，阈值 30 分钟
    worker = _worker(db, frame_dir)

    before_threshold = worker.run_once(now=datetime(2026, 9, 8, 8, 50))
    assert before_threshold.violations == 0
    assert before_threshold.skipped_unchanged == 0  # 首轮是真正识别的

    after_threshold = worker.run_once(now=T_1000)
    assert after_threshold.frames[0].reused is True, "内容未变应复用识别结果"
    assert after_threshold.violations == 1
    assert after_threshold.frames[0].rule_hit == m.RULE_ABNORMAL


def test_changed_content_is_re_recognized(db, frames):
    """内容变了 → 重新识别（不复用），`reused` 必须为 False。"""
    frame_dir = frames(FRAME_FUEL)
    worker = _worker(db, frame_dir)
    worker.run_once(now=T_1000)

    with open(os.path.join(frame_dir, FRAME_FUEL), "wb") as fh:
        fh.write(b"different-bytes")

    run = worker.run_once(now=T_1000 + timedelta(minutes=1))
    assert run.frames[0].reused is False
    assert run.frames[0].recognized is True


# ---------------------------------------------------------------------------
# 4) 单帧失败不中断（A10）
# ---------------------------------------------------------------------------
def test_missing_label_frame_is_reported_not_fatal(db, frames):
    frame_dir = frames(FRAME_MISSING_LABEL, FRAME_FUEL)
    run = _worker(db, frame_dir).run_once(now=T_1000)

    by_id = {f.frame_id: f for f in run.frames}
    assert by_id[FRAME_MISSING_LABEL].error and "识别失败" in by_id[FRAME_MISSING_LABEL].error
    assert by_id[FRAME_MISSING_LABEL].recognized is False
    assert by_id[FRAME_FUEL].rule_hit == m.RULE_FUEL_OCCUPY, "坏帧不应拖垮好帧"


def test_recognizer_exception_is_captured(db, frames):
    """识别器抛异常（缺权重 / 坏模型）→ 记进 `error`，**不伪造结果、不静默切 stub**。"""

    def boom(frame_ref: str):
        raise RuntimeError("模型权重缺失：runs/detect/train_real/weights/best.pt")

    run = _worker(db, frames(FRAME_FUEL), recognize=boom).run_once(now=T_1000)
    assert "模型权重缺失" in run.frames[0].error
    assert run.frames[0].recognized is False
    assert db.query(m.OccupationRecord).count() == 0


def test_http_exception_detail_is_kept(db, frames):
    """real 模式检测到无车牌时返回 422，编排要把**原因**带出来。"""

    def no_plate(frame_ref: str):
        raise HTTPException(status_code=422, detail="real 模式未在画面中检出租车牌")

    run = _worker(db, frames(FRAME_FUEL), recognize=no_plate).run_once(now=T_1000)
    assert "422" in run.frames[0].error
    assert "未" in run.frames[0].error


def test_empty_or_missing_frame_dir_is_not_an_error(db, tmp_path):
    frame_dir = tmp_path / "nope"
    run = _worker(db, str(frame_dir)).run_once(now=T_1000)
    assert run.frame_count == 0
    assert run.frames == []


# ---------------------------------------------------------------------------
# 5) 同次占用不重复提醒（A05）
# ---------------------------------------------------------------------------
def test_ten_rounds_produce_one_record_and_one_send(db, frames):
    """**验收 A05**：连跑 10 轮，同一次占用只有 1 条记录、1 次成功发送。"""
    frame_dir = frames(FRAME_FUEL)
    sender = CountingSender()
    worker = _worker(db, frame_dir, sender=sender)

    for i in range(10):
        run = worker.run_once(now=T_1000 + timedelta(seconds=i * 30))

    assert run.violations == 1
    assert db.query(m.OccupationRecord).count() == 1
    assert sender.calls == 1
    row = db.query(m.OccupationRecord).one()
    assert row.notify_attempts == 1
    assert row.notify_status == m.NOTIFY_SENT


def test_failure_then_recovery_sends_only_once_more(db, frames):
    """沙箱失败 → 后续轮次重试；恢复后成功，且**不新增记录**（A06 的自动侧）。"""
    frame_dir = frames(FRAME_FUEL)
    worker = _worker(db, frame_dir, sender=CountingSender("fail"))
    worker.run_once(now=T_1000)

    row = db.query(m.OccupationRecord).one()
    assert row.notify_status == m.NOTIFY_FAILED
    assert row.notify_attempts == 1

    worker._sender = CountingSender("ok")
    worker.run_once(now=T_1000 + timedelta(minutes=1))

    assert db.query(m.OccupationRecord).count() == 1
    row = db.query(m.OccupationRecord).one()
    assert row.notify_status == m.NOTIFY_SENT
    assert row.notify_attempts == 2


# ---------------------------------------------------------------------------
# 6) 帧 → 桩绑定（显式映射）
# ---------------------------------------------------------------------------
def test_bind_map_creates_occupancy_for_new_car(db, frames):
    """映射表里写明「这帧对应哪个桩」才绑定；没写就不猜。"""
    frame_dir = frames(FRAME_FUEL)  # 京A88888
    pile = db.get(m.ChargingPile, "PILE-001")  # 原本绑 京AD12345
    # 种子里 京A88888 还绑在 PILE-004 上：先摘掉，否则「按车牌反查桩」会查出两行
    db.get(m.ChargingPile, "PILE-004").bound_plate = None
    db.commit()

    worker = _worker(db, frame_dir, bind_map={FRAME_FUEL: "PILE-001"})
    worker.run_once(now=T_1000)

    assert pile.bound_plate == "京A88888"
    assert pile.occupancy_id
    assert db.query(m.OccupationRecord).count() == 1  # 燃油占位


def test_unmapped_frame_does_not_invent_pile_binding(db, frames):
    """没有映射 → 不做任何绑定（编造桩关联是本项目明令禁止的）。"""
    frame_dir = frames(FRAME_FUEL)
    pile = db.get(m.ChargingPile, "PILE-001")
    before = (pile.bound_plate, pile.occupancy_id)

    _worker(db, frame_dir).run_once(now=T_1000)
    assert (pile.bound_plate, pile.occupancy_id) == before


# ---------------------------------------------------------------------------
# 7) 状态文件与只读接口
# ---------------------------------------------------------------------------
def test_write_and_load_status_roundtrip(db, frames, tmp_path):
    frame_dir = frames(FRAME_FUEL, FRAME_NORMAL)
    run = _worker(db, frame_dir).run_once(now=T_1000)

    target = str(tmp_path / "pipeline_status.json")
    pl.write_status(run, target)

    data = pl.load_status(target)
    assert data["frame_count"] == 2
    assert data["violations"] == 1
    assert data["notified"] == 1
    assert {f["frame_id"] for f in data["frames"]} == {FRAME_FUEL, FRAME_NORMAL}


def test_load_status_missing_file_returns_none(tmp_path):
    assert pl.load_status(str(tmp_path / "nope.json")) is None


def test_empty_status_is_valid_skeleton():
    data = pl.empty_status()
    assert data["frame_count"] == 0
    assert data["frames"] == []
    assert data["finished_at"] is None


def test_pipeline_status_endpoint_is_read_only(client, monkeypatch, tmp_path, frames):
    """**口径 6**：刷新该接口不产生任何识别/判定/发送副作用。"""
    monkeypatch.setenv(pl.PIPELINE_STATUS_ENV, str(tmp_path / "status.json"))

    resp = client.get("/api/pipeline/status")  # 状态文件尚不存在
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["frame_count"] == 0
    assert body["last_run_at"] is None
    assert body["running"] is False

    assert client.get("/api/records").json()["total"] == 0, "只读接口不该产生记录"


def test_pipeline_status_endpoint_reports_last_run(
    client, monkeypatch, tmp_path, frames, db_session
):
    """编排跑过一轮后，接口回报的正是那一轮（UI 与日志按帧可追溯，A09）。"""
    status_file = tmp_path / "status.json"
    monkeypatch.setenv(pl.PIPELINE_STATUS_ENV, str(status_file))

    run = _worker(db_session, frames(FRAME_FUEL)).run_once(now=T_1000)
    pl.write_status(run, str(status_file))

    body = client.get("/api/pipeline/status").json()
    assert body["frame_count"] == 1
    assert body["violations"] == 1
    assert body["notified"] == 1
    assert body["frames"][0]["frame_id"] == FRAME_FUEL
    assert body["frames"][0]["record_id"] is not None
    assert body["last_run_at"] is not None


def test_frame_digest_changes_with_content(tmp_path):
    path = tmp_path / "a.jpg"
    path.write_bytes(b"one")
    first = pl.frame_digest(str(path))
    path.write_bytes(b"two")
    assert pl.frame_digest(str(path)) != first


def test_list_frames_is_sorted_and_filters_non_images(tmp_path):
    (tmp_path / "b.jpg").write_bytes(b"x")
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("x")
    assert pl.list_frames(str(tmp_path)) == ["a.png", "b.jpg"]
