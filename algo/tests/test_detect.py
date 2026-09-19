"""YOLOv8 检测训练/推理的测试（任务 2.3）。

运行方式（用算法环境）::

    .venv-algo\\Scripts\\python.exe -m pytest algo/tests -q

训练产物（best.pt）不入库：权重缺失时相关用例自动 skip，
先跑 ``algo/train/detect.py train`` 再跑完整测试。
"""

from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALGO = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ALGO, ".."))
sys.path.insert(0, os.path.join(ALGO, "train"))

import detect


def _best_pt() -> str | None:
    return detect.BEST_PT if os.path.isfile(detect.BEST_PT) else None


def test_data_yaml_ready_for_training():
    """训练前提：data.yaml 存在且指向存在的目录、类别 = vehicle/plate。"""
    assert os.path.isfile(detect.DATA_YAML), "先跑 algo/tools/gen_synth_dataset.py"
    with open(detect.DATA_YAML, encoding="utf-8") as fh:
        text = fh.read()
    assert "vehicle" in text and "plate" in text
    assert os.path.isdir(os.path.join(detect.RUN_DIR, "..", "..", "dataset", "images", "train"))


def test_predict_detects_vehicle_and_plate():
    """验收标准（PLAN §2.2 任务 2.3）：测试图上框出车辆/车牌并输出 bbox。"""
    import pytest

    if _best_pt() is None:
        pytest.skip("best.pt 不存在（先跑 algo/train/detect.py train）")

    val_imgs = sorted(glob.glob(os.path.join(REPO, "algo", "dataset", "images", "val", "*.jpg")))
    assert val_imgs, "val 集为空"

    boxes = detect.detect_boxes(val_imgs[0], conf=0.5)
    names = {b["name"] for b in boxes}
    assert "vehicle" in names, f"未检出车辆：{boxes}"
    assert "plate" in names, f"未检出租车牌：{boxes}"
    for b in boxes:
        _x, _y, w, h = b["bbox_xywh"]
        assert w > 0 and h > 0
        assert 0.0 <= b["conf"] <= 1.0


def test_plate_box_inside_vehicle_box():
    """车牌框应落在车辆框内（合成标注的几何约束，防止标注错位）。"""
    import pytest

    if _best_pt() is None:
        pytest.skip("best.pt 不存在")

    val_imgs = sorted(glob.glob(os.path.join(REPO, "algo", "dataset", "images", "val", "*.jpg")))
    boxes = detect.detect_boxes(val_imgs[0], conf=0.5)
    by_name = {b["name"]: b["bbox_xyxy"] for b in boxes}
    if "vehicle" not in by_name or "plate" not in by_name:
        import pytest

        pytest.fail("vehicle/plate 检测不完整")

    vx1, vy1, vx2, vy2 = by_name["vehicle"]
    px1, py1, px2, py2 = by_name["plate"]
    assert vx1 <= px1 and vy1 <= py1 and px2 <= vx2 and py2 <= vy2


def test_meta_matches_dataset_layout():
    """meta.json 的 split 与 images/labels 目录布局一致（数据集完整性）。"""
    meta_path = os.path.join(detect.DATA_YAML.replace("data.yaml", "meta.json"))
    if not os.path.isfile(meta_path):
        import pytest

        pytest.skip("数据集尚未生成")

    with open(meta_path, encoding="utf-8") as fh:
        metas = json.load(fh)
    for name, m in list(metas.items())[:10]:
        img = os.path.join(os.path.dirname(detect.DATA_YAML), "images", m["split"], f"{name}.jpg")
        assert os.path.isfile(img), img
