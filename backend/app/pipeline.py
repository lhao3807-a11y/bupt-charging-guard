"""自动闭环编排：取帧 → 识别 → 判定 → 落库 → 沙箱发送（契约 v1.9 §6.11 / 第 3 周 T3）。

**为什么需要它**：第 2 周之前，「识别—判断—提醒」要人点三次接口才能走完一遍，
第六页只是显示一张静态图 —— 显示一张图**不证明它参与了识别和判定**。
本模块把这条链串起来，作为**唯一的自动入口**：

```text
帧目录 ──▶ 识别（stub/real 自动跟随 RECOGNITION_MODE）──▶ 规则判定 ──▶ 落库 ──▶ 沙箱发送
```

五条口径（改动前先改契约）：

1. **无新帧也要重判时间规则**：内容没变的图片可以复用上次识别结果（省一次 CV），
   但**久停 / 充满超时仍然按当前时刻重新判定** —— 否则「没有新帧」就等于
   时间规则永远不触发，规则②③直接失效。
2. **单帧失败不中断**：坏图 / 无牌 / 缺权重只让**这一帧**失败并给出原因，
   其余帧照常处理。不伪造识别结果、不静默切回 stub。
3. **正常场景不调用发送器**：只有落库成功的违规才会走提醒流程（验收 A04）。
4. **判定交回规则引擎、发送交回提醒服务**：本模块不自己写 `rule_hit`、
   不自己写 `notify_status`，避免与 `/api/judge`、`/api/notify` 口径打架。
5. **状态只读外置**：编排通常跑在**独立进程**里，结果写到状态文件，
   `GET /api/pipeline/status` 只读该文件，**不承担编排职责、不触发任何副作用**。

维护人：汤瑾睿
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models as m
from app import notification, occupancy
from app.rule_engine import judge, save_violation
from app.schemas import RecognitionResult

#: 取帧目录（部署配置，不进 system_config —— 契约 §7）
FRAME_SOURCE_DIR_ENV = "FRAME_SOURCE_DIR"
DEFAULT_FRAME_DIRNAME = os.path.join("algo", "samples", "frames")

#: 状态文件（编排进程写、API 只读）；默认落在凭据目录里
PIPELINE_STATUS_ENV = "PIPELINE_STATUS_FILE"
DEFAULT_STATUS_PATH = os.path.join("docs", "acceptance", "week3", "pipeline_status.json")

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


@dataclass
class FrameOutcome:
    """单帧的处理结果 —— 一帧一行证据，UI 与验收都据此追溯。"""

    frame_id: str
    frame_digest: str | None = None
    recognized: bool = False
    reused: bool = False
    plate: str | None = None
    vtype: str | None = None
    pile_id: str | None = None
    rule_hit: int | None = None
    record_id: int | None = None
    notify_status: str | None = None
    notify_reason: str | None = None
    error: str | None = None


@dataclass
class PipelineRun:
    """一轮编排的结果。"""

    started_at: datetime
    finished_at: datetime | None = None
    frames: list[FrameOutcome] = field(default_factory=list)

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def recognized(self) -> int:
        return sum(1 for f in self.frames if f.recognized)

    @property
    def violations(self) -> int:
        return sum(1 for f in self.frames if f.rule_hit)

    @property
    def notified(self) -> int:
        return sum(1 for f in self.frames if f.notify_status == m.NOTIFY_SENT)

    @property
    def skipped_unchanged(self) -> int:
        return sum(1 for f in self.frames if f.reused)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["finished_at"] = self.finished_at.isoformat() if self.finished_at else None
        payload.update(
            frame_count=self.frame_count,
            recognized=self.recognized,
            violations=self.violations,
            notified=self.notified,
            skipped_unchanged=self.skipped_unchanged,
        )
        return payload


def repo_root() -> str:
    """仓库根目录（backend/app/pipeline.py → 上三级）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def default_frame_dir() -> str:
    env = os.environ.get(FRAME_SOURCE_DIR_ENV, "").strip()
    if env:
        return env if os.path.isabs(env) else os.path.join(repo_root(), env)
    return os.path.join(repo_root(), DEFAULT_FRAME_DIRNAME)


def status_path() -> str:
    env = os.environ.get(PIPELINE_STATUS_ENV, "").strip()
    if env:
        return env if os.path.isabs(env) else os.path.join(repo_root(), env)
    return os.path.join(repo_root(), DEFAULT_STATUS_PATH)


def list_frames(frame_dir: str) -> list[str]:
    """列出取帧目录下的图片文件名（升序，保证处理顺序可预期）。"""
    if not os.path.isdir(frame_dir):
        return []
    names = [
        name
        for name in os.listdir(frame_dir)
        if name.lower().endswith(IMAGE_EXTS) and os.path.isfile(os.path.join(frame_dir, name))
    ]
    return sorted(names)


def frame_digest(path: str) -> str:
    """文件内容 MD5 —— 帧标识。内容变了才重新识别。"""
    digest = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_recognize(frame_ref: str) -> RecognitionResult:
    """默认识别入口：**复用** `/api/recognize` 的同一套实现。

    刻意不在这里另写一份 stub/real 分支 —— 两个入口各写一份，
    迟早出现「接口能识别、编排识别不了」的分叉。
    """
    from app.routers.recognize import _recognize_real, _recognize_stub, get_recognition_mode

    if get_recognition_mode() == "real":
        return _recognize_real(frame_ref)
    return _recognize_stub(frame_ref)


class Pipeline:
    """一次实例化 = 一个编排工作进程。识别结果缓存在内存里。"""

    def __init__(
        self,
        db: Session,
        *,
        frame_dir: str | None = None,
        recognize=None,
        sender: notification.SandboxSender | None = None,
        bind_map: dict[str, str] | None = None,
    ) -> None:
        self.db = db
        self.frame_dir = frame_dir or default_frame_dir()
        self._recognize = recognize or default_recognize
        self._sender = sender
        self.bind_map = dict(bind_map or {})
        self._digests: dict[str, str] = {}
        self._cache: dict[str, RecognitionResult] = {}

    # -- 单帧 -------------------------------------------------------------
    def _bind_if_mapped(self, frame_id: str, recognition: RecognitionResult, now: datetime) -> None:
        """帧 → 桩的**显式**绑定（来自映射表，不是猜的）。

        只在「映射的桩当前绑的不是这辆车」时才动 —— 同车持续占用必须保持原标识。
        没有映射的帧**不做任何绑定**：猜桩等于编造桩关联（本项目一贯纪律）。
        """
        pile_id = self.bind_map.get(frame_id)
        if not pile_id:
            return
        pile = self.db.get(m.ChargingPile, pile_id)
        if pile is None:
            return
        if pile.bound_plate == recognition.plate:
            return
        occupancy.begin_occupancy(pile, recognition.plate, now, db=self.db)

    def process_frame(self, frame_id: str, now: datetime) -> FrameOutcome:
        """处理一帧；**任何异常都变成 `error` 字段返回**，不向外抛。"""
        outcome = FrameOutcome(frame_id=frame_id)
        path = os.path.join(self.frame_dir, frame_id)

        try:
            outcome.frame_digest = frame_digest(path)
        except OSError as exc:
            outcome.error = f"读取帧失败：{exc}"
            return outcome

        recognition = self._cache.get(frame_id)
        if recognition is not None and self._digests.get(frame_id) == outcome.frame_digest:
            outcome.reused = True  # 内容未变，复用上次识别结果
        else:
            try:
                recognition = self._recognize(frame_id)
            except HTTPException as exc:
                outcome.error = f"识别失败（{exc.status_code}）：{exc.detail}"
                return outcome
            except Exception as exc:  # noqa: BLE001 - CV 链路的异常类型不可控
                # 缺依赖/坏模型/解码失败都在这层兜住：**记下来，不伪造结果**
                outcome.error = f"识别异常：{type(exc).__name__}: {exc}"
                return outcome
            self._cache[frame_id] = recognition
            self._digests[frame_id] = outcome.frame_digest

        outcome.recognized = True
        outcome.plate = recognition.plate
        outcome.vtype = recognition.vtype.value

        try:
            self._bind_if_mapped(frame_id, recognition, now)
            # 判定时刻显式传 now：复用识别结果也**必须按当前时刻重判时间规则**（口径 1）
            hit = judge(recognition, self.db, now=now)
            if hit is None:
                return outcome  # 规则④ 正常：不落库、不发送（A04）

            outcome.pile_id = hit.pile_id
            outcome.rule_hit = hit.rule_hit
            saved = save_violation(self.db, hit)
            outcome.record_id = saved.id

            result = notification.send_for_record(self.db, saved.id, sender=self._sender, now=now)
            outcome.notify_status = result.status
            outcome.notify_reason = result.reason or (
                "此前已成功提醒，本次未重发" if result.already_sent else None
            )
        except Exception as exc:  # noqa: BLE001 - 单帧失败不得中断整轮（口径 2）
            self.db.rollback()
            outcome.error = f"判定/提醒失败：{type(exc).__name__}: {exc}"
        return outcome

    # -- 整轮 -------------------------------------------------------------
    def run_once(self, now: datetime | None = None) -> PipelineRun:
        """处理取帧目录下的全部图片，返回本轮结果。"""
        moment = now or datetime.now()
        run = PipelineRun(started_at=moment)

        for frame_id in list_frames(self.frame_dir):
            run.frames.append(self.process_frame(frame_id, moment))

        run.finished_at = now or datetime.now()
        return run


def write_status(run: PipelineRun, path: str | None = None) -> str:
    """把本轮结果写到状态文件（编排进程写）。"""
    target = path or status_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(run.to_dict(), fh, ensure_ascii=False, indent=2)
    return target


def load_status(path: str | None = None) -> dict | None:
    """读取状态文件（API 只读）；不存在或坏文件 → `None`（不是错误）。"""
    target = path or status_path()
    if not os.path.isfile(target):
        return None
    try:
        with open(target, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def empty_status() -> dict:
    """编排进程从未跑过时的响应骨架（§6.11 口径 4：仍是 200）。"""
    return PipelineRun(started_at=datetime.now()).to_dict()
