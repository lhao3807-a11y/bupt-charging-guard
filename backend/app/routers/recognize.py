"""识别桩 stub —— 对应 POST /api/recognize（CONTRACT §6.1）。

职责：按 ``frame_ref`` 拼路径读取标注 JSON，原样返回 ``RecognitionResult``。
**不读图片本身**（契约 §6.1 明确），只做「文件名 → 标注 JSON」的映射。

真实 CV（YOLOv8 + HyperLPR）后续替换本模块，返回结构完全一致，
前端与规则引擎零改动。
"""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException, status

from app.schemas import FrameRef, RecognitionResult

router = APIRouter(tags=["recognize"])

#: 标注目录：<repo>/algo/samples/labels/
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REPO_DIR = os.path.dirname(_BACKEND_DIR)
LABELS_DIR = os.path.join(_REPO_DIR, "algo", "samples", "labels")


def label_path_for(frame_ref: str) -> str:
    """把 ``frame_ref``（如 ``001.jpg``）映射为标注文件路径（``001.json``）。

    仅取 basename 并强制 ``.json`` 后缀，防止 ``../`` 越界读取（契约 §6.1
    规定 frame_ref 是**相对 algo/samples/frames/ 的文件名**）。
    """
    stem = os.path.splitext(os.path.basename(frame_ref))[0]
    return os.path.join(LABELS_DIR, f"{stem}.json")


@router.post(
    "/api/recognize", response_model=RecognitionResult, summary="输入帧 → 识别结果（stub）"
)
def recognize(req: FrameRef) -> RecognitionResult:
    """读 ``algo/samples/labels/<同名>.json`` 并返回。

    标注文件缺失 → ``404``（与吕浩对齐：不返回兜底假数据，避免掩盖联调中的路径错误）。
    """
    path = label_path_for(req.frame_ref)
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"识别桩未找到标注文件：{req.frame_ref} → 期望 {path}。"
                "请确认 frame_ref 与 algo/samples/labels/ 下的 JSON 同名。"
            ),
        )

    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)

    return RecognitionResult.model_validate(payload)
