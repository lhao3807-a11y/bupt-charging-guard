"""真实集评估脚本的纯函数测试（任务 5.5）。

`eval_real.py` 里真正需要单测的是**两个纯函数**——IoU 与字符级准确率。
它们一旦算错，评估报告上那些百分比就全是假的，而且错得很隐蔽
（比如 IoU 写成交集/面积 A，数字照样在 0~1 之间，没人看得出）。
端到端跑评估的部分依赖 GPU + 权重 + 数据集，不在单测范围内。

运行方式（用算法环境）::

    .venv-algo\\Scripts\\python.exe -m pytest algo/tests -q
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="算法环境未就绪（见 algo/requirements-algo.txt）")

from algo.tools import eval_real


@pytest.mark.parametrize(
    "a,b,expect",
    [
        ([0, 0, 10, 10], [0, 0, 10, 10], 1.0),  # 完全相同
        ([0, 0, 10, 10], [20, 20, 30, 30], 0.0),  # 完全不相交
        ([0, 0, 10, 10], [5, 0, 15, 10], 5 / 15),  # 半重叠：交 50 / 并 150
        ([0, 0, 10, 10], [0, 5, 10, 15], 5 / 15),  # 纵向半重叠
        ([0, 0, 0, 0], [0, 0, 10, 10], 0.0),  # 退化框：不能除零
    ],
)
def test_iou(a: list[float], b: list[float], expect: float):
    assert eval_real.iou(a, b) == pytest.approx(expect)


def test_iou_symmetric():
    """IoU 必须对称——顺序颠倒结果一样，否则说明哪一侧的框被特殊对待了。"""
    a, b = [3, 4, 30, 40], [10, 20, 45, 55]
    assert eval_real.iou(a, b) == pytest.approx(eval_real.iou(b, a))


@pytest.mark.parametrize(
    "pred,gt,expect",
    [
        ("京AD12345", "京AD12345", 1.0),  # 全对
        ("京AD12346", "京AD12345", 0.875),  # 8 位错 1 位
        # 位数不齐时从第 3 位起整体错位，只剩前两位（京/A）命中 → 2/8。
        # 这正是想要的行为：少认一位不是「差一点」，而是后面全错。
        ("京A12345", "京AD12345", 0.25),
        ("", "京AD12345", 0.0),  # 没识别出来
        ("京", "京", 1.0),
    ],
)
def test_char_accuracy(pred: str, gt: str, expect: float):
    assert eval_real.char_accuracy(pred, gt) == pytest.approx(expect)


def test_char_accuracy_empty_gt_is_zero():
    """真值为空（标注缺失）时不能抛 ZeroDivisionError。"""
    assert eval_real.char_accuracy("京A12345", "") == 0.0


def test_load_samples_split_filter(tmp_path):
    """`load_samples`：按 split 过滤，且跳过图片文件不存在的条目。"""
    import json
    import os

    import numpy as np

    pytest.importorskip("cv2")
    import cv2

    data = tmp_path / "ds"
    for split in ("train", "val"):
        (data / "images" / split).mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(data / "images" / "val" / "v1.jpg"), np.zeros((20, 60, 3), dtype=np.uint8))
    # t1.jpg 只写进 meta 不写图片文件 → 应被跳过
    (data / "meta.json").write_text(
        json.dumps(
            {
                "v1.jpg": {
                    "split": "val",
                    "plate": "京AD12345",
                    "vtype": "新能源",
                    "bbox_plate": [0, 0, 10, 10],
                },
                "v2.jpg": {
                    "split": "val",
                    "plate": "京A12345",
                    "vtype": "燃油",
                    "bbox_plate": [0, 0, 10, 10],
                },
                "t1.jpg": {
                    "split": "train",
                    "plate": "京A12345",
                    "vtype": "燃油",
                    "bbox_plate": [0, 0, 10, 10],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    got = eval_real.load_samples(str(data), "val", 0)
    assert [os.path.basename(p) for p, _ in got] == ["v1.jpg"]

    got_all = eval_real.load_samples(str(data), "all", 1)
    assert len(got_all) == 1, "--limit 应生效"
