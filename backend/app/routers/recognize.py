"""识别桩 —— 对应 POST /api/recognize（CONTRACT §6.1）。

双模式（PLAN §2.2 任务 2.5），经环境变量 ``RECOGNITION_MODE`` 切换：

- ``stub``（**默认**）：按 ``frame_ref`` 拼路径读标注 JSON 原样返回，**不读图片**
  （契约 §6.1），demo 稳定、不被模型拖累。
- ``real``：读 ``algo/samples/frames/<frame_ref>`` 真图 → YOLO 检测 + HyperLPR3
  识别 + 绿蓝牌判定（``algo/recognize/plate.py``），返回结构**与 stub 完全一致**。

开关**刻意不放 `system_config` 表**：契约 §7 的系统配置项只含业务阈值
（``full_timeout_min`` / ``abnormal_park_min``），识别模式属部署期/调试开关，
按「先改契约再动代码」的纪律不擅自扩表。

模式非法 / real 模式缺 CV 依赖 / 真图缺失或无车牌 → 明确的 4xx/5xx，不静默兜底。
"""

from __future__ import annotations

import json
import os
import sys

from fastapi import APIRouter, HTTPException, status

from app.schemas import FrameRef, RecognitionResult

router = APIRouter(tags=["recognize"])

#: 标注目录：<repo>/algo/samples/{labels,frames}/
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REPO_DIR = os.path.dirname(_BACKEND_DIR)
LABELS_DIR = os.path.join(_REPO_DIR, "algo", "samples", "labels")
FRAMES_DIR = os.path.join(_REPO_DIR, "algo", "samples", "frames")

#: 模式开关：环境变量，未设置或为空 → 默认 stub
MODE_ENV_VAR = "RECOGNITION_MODE"
VALID_MODES = ("stub", "real")
DEFAULT_MODE = "stub"


def label_path_for(frame_ref: str) -> str:
    """把 ``frame_ref``（如 ``001.jpg``）映射为标注文件路径（``001.json``）。

    仅取 basename 并强制 ``.json`` 后缀，防止 ``../`` 越界读取（契约 §6.1
    规定 frame_ref 是**相对 algo/samples/frames/ 的文件名**）。
    """
    stem = os.path.splitext(os.path.basename(frame_ref))[0]
    return os.path.join(LABELS_DIR, f"{stem}.json")


def frame_path_for(frame_ref: str) -> str:
    """real 模式：``frame_ref`` → 真实图片路径（同样只取 basename 防越界）。"""
    name = os.path.basename(frame_ref)
    if not name.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"real 模式的 frame_ref 必须是图片文件名（.jpg/.png）：{frame_ref!r}",
        )
    return os.path.join(FRAMES_DIR, name)


def get_recognition_mode() -> str:
    """解析当前识别模式：``RECOGNITION_MODE`` 环境变量，未设置/为空 → ``stub``。"""
    env = os.environ.get(MODE_ENV_VAR, "").strip().lower()
    if not env:
        return DEFAULT_MODE
    if env not in VALID_MODES:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{MODE_ENV_VAR} 非法：{env!r}（可选 {'/'.join(VALID_MODES)}）",
        )
    return env


def _recognize_stub(frame_ref: str) -> RecognitionResult:
    """stub：读同名标注 JSON 原样返回（契约 §6.1）。"""
    path = label_path_for(frame_ref)
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"识别桩未找到标注文件：{frame_ref} → 期望 {path}。"
                "请确认 frame_ref 与 algo/samples/labels/ 下的 JSON 同名。"
            ),
        )

    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)

    return RecognitionResult.model_validate(payload)


def _recognize_real(frame_ref: str) -> RecognitionResult:
    """real：读真图跑 CV 链路（检测 → OCR → 绿蓝牌判定）。

    CV 依赖（torch/ultralytics/hyperlpr3）只在算法环境 ``.venv-algo`` 里，
    后端进程缺依赖时返回 503 并给出可操作的提示，而不是让 demo 崩掉。
    """
    path = frame_path_for(frame_ref)
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"real 模式未找到图片：{frame_ref} → 期望 {path}",
        )

    if _REPO_DIR not in sys.path:
        sys.path.insert(0, _REPO_DIR)
    try:
        from algo.recognize.plate import recognize_frame
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "real 模式需要算法环境依赖（torch/ultralytics/hyperlpr3）。"
                f"导入失败：{exc}。请用 .venv-algo 运行后端，"
                f"或去掉 {MODE_ENV_VAR}=real（回到默认 stub）。"
            ),
        ) from exc

    result = recognize_frame(path)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"real 模式未在画面中检出租车牌：{frame_ref}",
        )
    return RecognitionResult.model_validate(result)


@router.post(
    "/api/recognize", response_model=RecognitionResult, summary="输入帧 → 识别结果（stub/real）"
)
def recognize(req: FrameRef) -> RecognitionResult:
    """按当前模式返回 ``RecognitionResult``（两种模式结构完全一致，契约 §4）。"""
    if get_recognition_mode() == "real":
        return _recognize_real(req.frame_ref)
    return _recognize_stub(req.frame_ref)
