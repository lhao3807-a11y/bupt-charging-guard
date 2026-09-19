"""车牌识别与车型判定（PLAN §2.2 任务 2.4）。

流程
----
输入帧 → YOLO 检出车牌区域（任务 2.3 的 best.pt）→ 裁剪 ROI →
HyperLPR3 识别号码 → **HSV 颜色统计判定绿牌/蓝牌** → 输出与契约 ``RecognitionResult``
**字段完全一致**的 dict（``plate`` / ``vtype`` / ``confidence`` / ``bbox`` / ``frame_time``）。

为什么用颜色统计而不是 OCR 库的牌色枚举：
HyperLPR3 的 plate_type 枚举随版本变动，而「绿=新能源 / 蓝=燃油」本质是**底色**问题
（契约 §3.1 已把车型标签绑到车牌底色），HSV 统计可解释、不依赖第三方内部约定。

⚠️ 当前模型/OCR 在**合成帧**上训练与测试；校园实拍替换数据集后需重训再评估（algo/README.md §3）。
"""

from __future__ import annotations

import os
import re
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ALGO = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ALGO, ".."))

#: 任务 2.3 训练产出的车牌检测权重
DEFAULT_WEIGHTS = os.path.join(ALGO, "runs", "detect", "train", "weights", "best.pt")

# HSV 底色判定阈值（OpenCV H∈[0,180]）：绿牌深绿 ≈ 35~90，蓝牌深蓝 ≈ 100~130
_HSV_GREEN_LO, _HSV_GREEN_HI = (35, 60, 40), (90, 255, 255)
_HSV_BLUE_LO, _HSV_BLUE_HI = (100, 80, 40), (130, 255, 255)

VTYPE_NEW_ENERGY = "新能源"
VTYPE_FUEL = "燃油"

# 中国大陆车牌格式：省份汉字 + 发牌机关字母 + 5 位（燃油）/ 6 位（新能源）尾号。
# OCR 输出不匹配即视为识别失败（HyperLPR 对合成牌会吐出乱码，如小数）。
PLATE_RE = re.compile(
    r"[京津沪渝冀晋蒙辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云藏陕甘青宁新使]"
    r"[A-HJ-NP-Z][A-HJ-NP-Z0-9]{5,6}"
)


def is_valid_plate_text(text: str) -> bool:
    """粗校验 OCR 出的字符串是否像一张中国车牌号。"""
    return bool(PLATE_RE.fullmatch(text))


def judge_vtype_by_color(roi_bgr: np.ndarray) -> str:
    """按车牌 ROI 的绿/蓝像素占比判定车型；平票视为燃油（保守）。"""
    import cv2

    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    green = int(cv2.inRange(hsv, _HSV_GREEN_LO, _HSV_GREEN_HI).sum())
    blue = int(cv2.inRange(hsv, _HSV_BLUE_LO, _HSV_BLUE_HI).sum())
    return VTYPE_NEW_ENERGY if green > blue else VTYPE_FUEL


def _ocr_plate(roi_bgr: np.ndarray, catcher) -> tuple[str, float]:
    """用 HyperLPR3 识别 ROI 里的车牌号，返回 (号码, 置信度)。

    识别不出或结果不像车牌号（``is_valid_plate_text`` 不过）都返回 ("", 0.0)。
    """
    results = catcher(roi_bgr) or []
    if not results:
        return "", 0.0
    # HyperLPR3 返回形如 [(box, text, score, plate_type), ...]，取分最高的一条
    best = max(results, key=lambda r: float(r[2]))
    text = str(best[1]).strip().replace("·", "").replace("-", "").upper()
    if not is_valid_plate_text(text):
        return "", 0.0
    return text, float(best[2])


def recognize_frame(
    image_path: str,
    *,
    frame_time: datetime | None = None,
    weights: str | None = None,
    conf: float = 0.4,
) -> dict | None:
    """完整识别：帧文件 → ``RecognitionResult`` 兼容 dict；未检出租车牌返回 ``None``。

    ``frame_time`` 缺省取当前时间；``weights`` 缺省用任务 2.3 训练出的 best.pt。
    """
    import cv2

    from algo.train.detect import detect_boxes

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"读不到图片：{image_path}")

    boxes = detect_boxes(image_path, conf=conf, weights=weights or DEFAULT_WEIGHTS)
    plates = [b for b in boxes if b["name"] == "plate"]
    if not plates:
        return None
    plate_box = max(plates, key=lambda b: b["conf"])
    x1, y1, x2, y2 = (int(v) for v in plate_box["bbox_xyxy"])

    # ROI 外扩一点，补偿检测框偏紧导致的 OCR 失败
    pad = max(4, int(0.08 * max(x2 - x1, y2 - y1)))
    h, w = img.shape[:2]
    roi = img[max(0, y1 - pad) : min(h, y2 + pad), max(0, x1 - pad) : min(w, x2 + pad)]

    from hyperlpr3 import LicensePlateCatcher

    text, ocr_score = _ocr_plate(roi, LicensePlateCatcher())
    vtype = judge_vtype_by_color(roi)

    return {
        "plate": text,
        "vtype": vtype,
        "confidence": (
            min(float(plate_box["conf"]), ocr_score) if text else float(plate_box["conf"])
        ),
        "bbox": [x1, y1, x2 - x1, y2 - y1],  # 契约 §4：[x, y, w, h]
        "frame_time": (frame_time or datetime.now()).isoformat(timespec="seconds"),
    }
