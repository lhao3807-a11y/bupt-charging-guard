"""bbox 工具（坐标一律 ``xyxy``）。

单独成一个模块而不是散在调用方里，是因为**两个地方都要算 IoU 且口径必须一致**：

- ``recognize/plate.py``：整帧 OCR 会返回若干条结果，要靠 IoU 挑出"对应当前检测框"的那条
- ``tools/eval_real.py``：评估检测质量时算 IoU≥0.5 命中率

各写一份的话，一旦哪边的交并比写错（比如写成 交集/面积A），数字照样落在 0~1 之间，
没人看得出，评估报告就全假了。
"""

from __future__ import annotations


def iou(box_a, box_b) -> float:
    """两个 ``[x1, y1, x2, y2]`` 框的交并比；并集为 0（退化框）时返回 0。"""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0
