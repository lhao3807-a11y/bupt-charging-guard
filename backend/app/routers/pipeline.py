"""编排结果只读接口 —— 对应 GET /api/pipeline/status（契约 v1.9 §6.11 / 第 3 周 T3）。

**只回报，不干活**：编排跑在**独立进程**（`scripts/run_pipeline.py`）里，
把每轮结果写到状态文件；本端点读该文件返回。

这样分工是刻意的：

- 浏览器刷新页面**不会**触发识别、判定或发送（「刷新即发短信」是最难查的演示事故）；
- 编排进程崩了，页面仍能显示**最后一轮**的结果，而不是一片空白；
- 第六页（L4）与验收（A09/A10）拿到的是同一份 JSON，UI 与日志可以对帧。

状态文件不存在（编排从未运行）→ 返回空骨架 + `200`，**不是错误**。
"""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter

from app import pipeline
from app.schemas import PipelineStatus

router = APIRouter(tags=["pipeline"])

#: 状态文件更新后多久内算「编排正在运行」
RUNNING_WINDOW_SEC = 60


def _infer_running(finished_at: datetime | None) -> bool:
    """按状态文件的新鲜度推断编排是否还在跑（进程没写心跳也能判断）。"""
    if finished_at is None:
        return False
    return (datetime.now() - finished_at).total_seconds() <= RUNNING_WINDOW_SEC


@router.get(
    "/api/pipeline/status",
    response_model=PipelineStatus,
    summary="编排最近一轮结果（只读，无副作用）",
)
def pipeline_status() -> PipelineStatus:
    """返回编排最近一轮的处理结果；从未运行过返回空骨架（200）。"""
    data = pipeline.load_status()
    if data is None:
        return PipelineStatus()

    finished = data.get("finished_at")
    status = PipelineStatus.model_validate(data)
    status.running = _infer_running(
        datetime.fromisoformat(finished) if isinstance(finished, str) else None
    )
    status.last_run_at = (
        datetime.fromisoformat(finished) if isinstance(finished, str) else status.last_run_at
    )
    return status


def status_file_hint() -> str:
    """给运维提示状态文件路径（排查「页面一直空」时第一步就看它）。"""
    return os.path.relpath(pipeline.status_path(), pipeline.repo_root())
