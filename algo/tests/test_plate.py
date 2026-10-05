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

# CV 环境守卫（任务 5.2）：算法环境没装时跳过本模块，而不是收集报错 exit 2
pytest.importorskip("numpy", reason="算法环境未就绪（见 algo/requirements-algo.txt）")

# 必须放在 importorskip 之后：plate 在模块级 import numpy
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


def test_crop_plate_roi_pads_and_clips():
    """`crop_plate_roi`：四周外扩约 8%，且不会越出图像边界。"""
    import numpy as np

    img = np.zeros((100, 200, 3), dtype=np.uint8)
    # 框 40x20 居中：外扩 max(4, 8%*40=3.2) = 4 像素
    roi = plate.crop_plate_roi(img, [80, 40, 120, 60])
    assert roi.shape[:2] == (28, 48), roi.shape  # 20+8 x 40+8

    # 贴边时只裁到边界内，不报错、不产生空图
    roi_edge = plate.crop_plate_roi(img, [0, 0, 30, 10])
    assert roi_edge.shape[0] == 14 and roi_edge.shape[1] == 34


def test_ocr_plate_rejects_non_plate_text():
    """`ocr_plate`：catcher 吐出非车牌字符串（HyperLPR 对合成牌的乱码）时返回空。"""
    import numpy as np

    roi = np.zeros((30, 90, 3), dtype=np.uint8)

    class _FakeCatcher:
        def __call__(self, _roi):
            return [["0.95080864", 0.9, 0, [0, 0, 1, 1]]]

    assert plate.ocr_plate(roi, _FakeCatcher()) == ("", 0.0)


def test_ocr_plate_parses_hyperlpr3_order():
    """**防回归**：hyperlpr3 返回 ``[号码, 置信度, 牌色, 框]``，顺序不能搞反。

    第 2 周真实集评估（任务 5.5）才发现早期版本按 ``(框, 号码, 置信度, 牌色)``
    解析 —— 于是拿置信度当号码、拿牌色当置信度，正则永远不过，
    OCR 静默地恒定返回空串，而合成集上的验收完全看不出来（合成牌本来就识别不出）。
    这条测试用「文本位与分数位互换会立刻掉到 0」的方式把顺序钉死。
    """
    import numpy as np

    roi = np.zeros((30, 90, 3), dtype=np.uint8)

    class _Catcher:
        def __call__(self, _roi):
            return [
                ["京A12345", 0.72, 0, [0, 0, 90, 30]],  # 低分
                ["京AD12345", 0.93, 1, [0, 0, 90, 30]],  # 高分，应被选中
            ]

    assert plate.ocr_plate(roi, _Catcher()) == ("京AD12345", 0.93)

    class _SwappedCatcher:
        """按错误顺序喂数据：分数排在文本位 → 必须判定为无效，不能误当成车牌。"""

        def __call__(self, _roi):
            return [[0.93, "京AD12345", 1, [0, 0, 90, 30]]]

    assert plate.ocr_plate(roi, _SwappedCatcher()) == ("", 0.0)


def test_ocr_plate_in_frame_picks_result_matching_box():
    """`ocr_plate_in_frame`：多块牌时按 IoU 挑**贴合检测框**的那条，而不是最高分那条。

    这条是"多车不认错车"的守卫：画面里同时有邻车车牌时，取最高分会串号，
    而串号意味着短信提醒发错人 —— 属于会直接造成用户投诉的错。
    """
    import numpy as np

    img = np.zeros((720, 1280, 3), dtype=np.uint8)

    class _TwoPlates:
        def __call__(self, _img):
            return [
                ["京B99999", 0.99, 0, [900, 100, 1100, 200]],  # 高分，但是隔壁车的
                ["京AD12345", 0.80, 1, [100, 100, 300, 200]],  # 低分，正是要的那块
            ]

    # prefer_box 贴合第二块 → 必须选它，尽管分数更低
    assert plate.ocr_plate_in_frame(img, _TwoPlates(), [110, 110, 290, 190]) == ("京AD12345", 0.80)
    # 不给 prefer_box 时退化为取最高分
    assert plate.ocr_plate_in_frame(img, _TwoPlates()) == ("京B99999", 0.99)

    class _Empty:
        def __call__(self, _img):
            return []

    assert plate.ocr_plate_in_frame(img, _Empty(), [0, 0, 10, 10]) == ("", 0.0)


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
    ex, ey, _ew, _eh = m["bbox_plate"]
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
