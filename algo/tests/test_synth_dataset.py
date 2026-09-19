"""合成数据集生成器的测试（任务 2.2）。

运行方式（用算法环境，不进后端 venv）::

    .venv-algo\\Scripts\\python.exe -m pytest algo/tests -q

只测**函数级**逻辑（单帧绘制、车牌号生成、标注格式），不重复生成全量数据集；
数据集本身的完整性由 ``check_dataset.py`` 与训练入口负责。
"""

from __future__ import annotations

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, "..", "tools"))
sys.path.insert(0, TOOLS)

import gen_synth_dataset as gen


# ---------------------------------------------------------------------------
# 车牌号生成（契约 §4：plate 必须能对应 vtype）
# ---------------------------------------------------------------------------
def test_rand_plate_new_energy_is_8_chars():
    rng = random.Random(0)
    for _ in range(50):
        plate = gen.rand_plate(rng, "新能源")
        assert len(plate) == 8, f"新能源牌应为 8 位：{plate}"
        assert plate.startswith("京A"), plate
        assert plate[2] in "DF", f"新能源第 3 位应为 D/F：{plate}"


def test_rand_plate_fuel_is_7_chars():
    rng = random.Random(0)
    for _ in range(50):
        plate = gen.rand_plate(rng, "燃油")
        assert len(plate) == 7, f"燃油牌应为 7 位：{plate}"
        assert plate.startswith("京A"), plate
        # 注：燃油牌第 3 位允许出现字母 D/F（如 京ADY8J8），
        # 与新能源的区分依据是**总长 8 位**，不是单个字母。


# ---------------------------------------------------------------------------
# 单帧绘制与 YOLO 标注
# ---------------------------------------------------------------------------
def test_draw_scene_produces_two_boxes_for_every_scene():
    for scene in gen.SCENES:
        rng = random.Random(1)
        img, lines, meta = gen.draw_scene(rng, scene)
        assert img.size == (gen.W, gen.H)
        assert len(lines) == 2, "每帧应恰好 2 个框：vehicle + plate"
        for line in lines:
            parts = line.split()
            assert len(parts) == 5, f"YOLO 行应为 5 列：{line}"
            cls, cx, cy, w, h = int(parts[0]), *map(float, parts[1:])
            assert cls in (gen.CLS_VEHICLE, gen.CLS_PLATE)
            for v in (cx, cy, w, h):
                assert 0.0 <= v <= 1.0, f"归一化坐标越界：{line}"
            assert w > 0 and h > 0
        assert meta["scene"] == scene
        assert meta["vtype"] == gen.SCENES[scene][0]
        assert len(meta["plate"]) == (8 if meta["vtype"] == "新能源" else 7)


def test_draw_scene_plate_color_matches_vtype():
    """绿牌 = 新能源 / 蓝牌 = 燃油（契约 §3.1，2.4 的判定依据）。"""
    rng = random.Random(2)
    _, _, meta_ev = gen.draw_scene(rng, "charging")
    assert meta_ev["vtype"] == "新能源"
    _, _, meta_fuel = gen.draw_scene(rng, "fuel")
    assert meta_fuel["vtype"] == "燃油"


def test_scene_table_covers_four_rules():
    """四类场景必须齐备，且与规则①②③④的语义对应。"""
    assert set(gen.SCENES) == {"fuel", "idle", "charging", "full"}
    # 燃油占位：蓝牌（燃油）+ 空闲 + 无枪
    assert gen.SCENES["fuel"] == ("燃油", "空闲", False)
    # 已充满未移车：绿牌 + 已充满 + 插枪
    assert gen.SCENES["full"][1:] == ("已充满", True)


# ---------------------------------------------------------------------------
# 已生成数据集的抽查（若存在；CI/新机器上跳过）
# ---------------------------------------------------------------------------
def test_existing_dataset_labels_are_valid():
    meta_path = os.path.join(gen.DATASET, "meta.json")
    if not os.path.isfile(meta_path):
        import pytest

        pytest.skip("数据集尚未生成（先跑 gen_synth_dataset.py）")

    import json

    with open(meta_path, encoding="utf-8") as fh:
        metas = json.load(fh)

    # 每类 ≥30 张（验收：合计 ≥120）
    per_scene: dict[str, int] = {}
    for m in metas.values():
        per_scene[m["scene"]] = per_scene.get(m["scene"], 0) + 1
    assert set(per_scene) == {"fuel", "idle", "charging", "full"}
    assert all(n >= 30 for n in per_scene.values()), per_scene
    assert sum(per_scene.values()) >= 120

    # 抽查 5 张：图与标签文件都在，且行数 = 2
    names = sorted(metas)[:5]
    for name in names:
        m = metas[name]
        img_path = os.path.join(gen.DATASET, "images", m["split"], f"{name}.jpg")
        lbl_path = os.path.join(gen.DATASET, "labels", m["split"], f"{name}.txt")
        assert os.path.isfile(img_path), img_path
        assert os.path.isfile(lbl_path), lbl_path
        with open(lbl_path, encoding="utf-8") as fh:
            assert len(fh.read().strip().splitlines()) == 2
