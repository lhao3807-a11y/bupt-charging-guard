"""车牌识别 + 绿牌/蓝牌判定的测试（任务 2.4）。

运行方式（用算法环境）::

    .venv-algo\\Scripts\\python.exe -m pytest algo/tests -q

口径说明：HyperLPR 对**合成牌**识别不出号码（它只在真实车牌照片上有意义），
因此本周验收落在三件确定的事上——检测框正确、**车型判定正确**、
输出结构与契约 ``RecognitionResult`` 完全一致；OCR 号码校验用正则单测覆盖。
"""

from __future__ import annotations

import json
import os

import pytest

from algo.recognize import plate

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# OCR 结果校验（纯函数，不依赖模型）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,ok",
    [
        ("京AD12345", True),  # 新能源 8 位
        ("京A12345", True),  # 燃油 7 位
        ("京ADY8J8", True),  # 新能源含字母尾号
        ("0.95080864", False),  # HyperLPR 对合成牌的乱码输出
        ("", False),
        ("AD12345", False),  # 缺省份
        ("京A1234567", False),  # 位数超了
    ],
)
def test_is_valid_plate_text(text: str, ok: bool):
    assert plate.is_valid_plate_text(text) is ok


# ---------------------------------------------------------------------------
# vtype 底色判定（从合成数据集的真实车牌位置裁剪）
# ---------------------------------------------------------------------------
def _meta_and_roi(scene: str):
    meta_path = os.path.join(REPO, "algo", "dataset", "meta.json")
    if not os.path.isfile(meta_path):
        pytest.skip("数据集尚未生成（先跑 gen_synth_dataset.py）")

    import cv2

    with open(meta_path, encoding="utf-8") as fh:
        metas = json.load(fh)
    name, m = next((n, m) for n, m in sorted(metas.items()) if m["scene"] == scene)
    img_path = os.path.join(REPO, "algo", "dataset", "images", m["split"], f"{name}.jpg")
    img = cv2.imread(img_path)
    assert img is not None, img_path

    x, y, w, h = m["bbox_plate"]
    return img[y : y + h, x : x + w], m


@pytest.mark.parametrize("scene,vtype", [("fuel", "燃油"), ("charging", "新能源")])
def test_judge_vtype_by_color(scene: str, vtype: str):
    roi, m = _meta_and_roi(scene)
    assert m["vtype"] == vtype  # 前提：meta 标注一致
    assert plate.judge_vtype_by_color(roi) == vtype


# ---------------------------------------------------------------------------
# 端到端 recognize_frame（依赖 best.pt；缺失时 skip）
# ---------------------------------------------------------------------------
def _best_available() -> bool:
    return os.path.isfile(plate.DEFAULT_WEIGHTS)


@pytest.mark.skipif(
    not _best_available(), reason="best.pt 不存在（先跑 algo/train/detect.py train）"
)
def test_recognize_frame_structure_matches_contract():
    """契约 §4：输出字段与 RecognitionResult 完全一致。"""
    meta_path = os.path.join(REPO, "algo", "dataset", "meta.json")
    with open(meta_path, encoding="utf-8") as fh:
        metas = json.load(fh)
    name, m = next(iter(sorted(metas.items())))
    img_path = os.path.join(REPO, "algo", "dataset", "images", m["split"], f"{name}.jpg")

    result = plate.recognize_frame(img_path)
    assert result is not None, "合成帧上应能检出租车牌"
    assert set(result) == {"plate", "vtype", "confidence", "bbox", "frame_time"}
    assert result["vtype"] in ("新能源", "燃油")
    assert result["vtype"] == m["vtype"], "车型判定应与数据集标注一致"
    assert 0.0 <= result["confidence"] <= 1.0
    x, y, w, h = result["bbox"]
    assert w > 0 and h > 0
    # 车牌框应落在标注框附近（±30px，检测有抖动是正常的）
    ex, ey, ew, eh = m["bbox_plate"]
    assert abs(x - ex) < 30 and abs(y - ey) < 30
    # 合成牌 OCR 大概率失败 → plate 允许为空，但类型必须是 str
    assert isinstance(result["plate"], str)


@pytest.mark.skipif(not _best_available(), reason="best.pt 不存在")
def test_recognize_frame_none_when_no_plate(tmp_path):
    """画面里没有车牌 → 返回 None（不是报错）。"""
    import cv2
    import numpy as np

    blank = np.full((720, 1280, 3), 90, dtype=np.uint8)
    p = tmp_path / "blank.jpg"
    cv2.imwrite(str(p), blank)
    assert plate.recognize_frame(str(p)) is None
