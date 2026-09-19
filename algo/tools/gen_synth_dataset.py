"""生成校园充电桩车位**合成数据集**（PLAN §2.2 任务 2.2 的基线）。

为什么是合成帧
--------------
校园实拍需要人工采集与标注，第 1 周来不及；本脚本先用可控的合成帧把
「数据集 → 训练 → 推理 → 识别结果」整条链路跑通，**等实拍到位后直接替换重训**即可。
⚠️ 合成数据只能验证流程，**不能代表真实准确率**（见 algo/README.md §3）。

产出
----
```
algo/dataset/
├── data.yaml              # YOLO 训练配置（2 类：vehicle / plate）
├── images/train|val/*.jpg
├── labels/train|val/*.txt # YOLO 格式：cls cx cy w h（归一化）
└── meta.json              # 每张图的场景 / 车牌号 / vtype（供评估与测试用）
```

4 类场景（与规则引擎的四条规则一一对应），每类 ``--per-class`` 张（默认 33，合计 132）：

=====  ======================  ==========================
类别   场景                    视觉特征
=====  ======================  ==========================
fuel   燃油车占位（规则①）     蓝牌车 + 桩「空闲」+ 无枪
idle   新能源空闲久停（规则②） 绿牌车 + 桩「空闲」+ 无枪
charging 新能源充电中（规则④） 绿牌车 + 桩「充电中」+ 插枪
full   已充满未移车（规则③）   绿牌车 + 桩「已充满」+ 插枪
=====  ======================  ==========================

用法：``.venv-algo\\Scripts\\python.exe algo/tools/gen_synth_dataset.py [--per-class 33] [--seed 42]``
"""

from __future__ import annotations

import argparse
import json
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATASET = os.path.join(REPO, "algo", "dataset")

W, H = 1280, 720
VAL_RATIO = 0.2

# YOLO 类别（顺序即 class id，与 data.yaml 的 names 一致）
CLS_VEHICLE = 0
CLS_PLATE = 1
CLASS_NAMES = ["vehicle", "plate"]

# 车牌牌面底色：绿牌 = 新能源，蓝牌 = 燃油（契约 §3.1 车型判定依据）
PLATE_GREEN = (0, 132, 84)
PLATE_BLUE = (20, 60, 150)

# 场景 → (vtype, 桩状态文案, 是否插枪)
SCENES = {
    "fuel": ("燃油", "空闲", False),
    "idle": ("新能源", "空闲", False),
    "charging": ("新能源", "充电中", True),
    "full": ("新能源", "已充满", True),
}

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]

# 车牌省份简称（只用京牌，贴合北邮校园场景）
PLATE_PREFIX = "京A"
DIGITS = "0123456789"
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # 去掉 I/O，贴近真实车牌规则


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def rand_plate(rng: random.Random, vtype: str) -> str:
    """生成合法形态的车牌号：新能源 8 位（含 D/F 字母位），燃油 7 位。"""
    if vtype == "新能源":
        return PLATE_PREFIX + rng.choice("DF") + "".join(rng.choice(DIGITS) for _ in range(5))
    return PLATE_PREFIX + "".join(rng.choice(DIGITS + LETTERS) for _ in range(5))


def _yolo_box(x: int, y: int, w: int, h: int) -> tuple[float, float, float, float]:
    """左上角+宽高 → YOLO 归一化 (cx, cy, w, h)。"""
    return ((x + w / 2) / W, (y + h / 2) / H, w / W, h / H)


def draw_scene(rng: random.Random, scene: str):
    """画一帧，返回 (PIL 图像, YOLO 标注行列表, meta 字典)。"""
    vtype, pile_status, plugged = SCENES[scene]
    plate = rand_plate(rng, vtype)
    is_ev = vtype == "新能源"

    img = Image.new("RGB", (W, H), (58, 62, 68))
    d = ImageDraw.Draw(img)

    f_small = load_font(22)
    f_plate = load_font(44)
    f_title = load_font(30)

    # ---- 地面 + 车位线（车辆所在车位随机 0~2）----
    slot_idx = rng.randint(0, 2)
    ground = (86, 90, 96)
    d.rectangle([0, 260, W, H], fill=ground)
    for i in range(4):
        x = 60 + i * 330
        d.line([(x, 300), (x, H - 40)], fill=(220, 220, 220), width=5)
    d.line([(60, H - 40), (60 + 3 * 330, H - 40)], fill=(220, 220, 220), width=5)

    slot_x = 60 + slot_idx * 330

    # ---- 充电桩立柱 + 状态屏 ----
    pile_x = slot_x + 250
    d.rectangle([pile_x, 150, pile_x + 56, 330], fill=(210, 214, 220))
    screen = (
        (255, 214, 102)
        if pile_status == "充电中"
        else ((120, 200, 120) if pile_status == "已充满" else (150, 154, 160))
    )
    d.rectangle([pile_x + 8, 170, pile_x + 48, 230], fill=screen)
    d.text((pile_x + 12, 182), pile_status[:2], font=f_small, fill=(24, 27, 32))
    d.text((pile_x + 12, 206), pile_status[2:], font=f_small, fill=(24, 27, 32))

    # ---- 车辆（颜色/尺寸轻微随机，避免所有样本一模一样）----
    body = (
        (rng.randint(30, 90), rng.randint(100, 160), rng.randint(70, 120))
        if is_ev
        else (rng.randint(40, 80), rng.randint(80, 120), rng.randint(140, 200))
    )
    car_l = slot_x + 26 + rng.randint(-8, 8)
    car_t = 380 + rng.randint(-10, 10)
    car_r = car_l + 234 + rng.randint(-10, 10)
    car_b = car_t + 210
    d.rounded_rectangle([car_l, car_t, car_r, car_b], radius=18, fill=body)
    d.rounded_rectangle(
        [car_l + 22, car_t + 34, car_r - 22, car_t + 128], radius=10, fill=(196, 214, 226)
    )

    # ---- 充电枪线（插枪场景才画）----
    if plugged:
        gx, gy = pile_x + 28, 250
        socket_x, socket_y = car_r - 18, car_t + 120
        d.line([(gx, gy), (gx - 30, gy + 60), (socket_x, socket_y)], fill=(40, 44, 50), width=6)
        d.ellipse([socket_x - 10, socket_y - 10, socket_x + 10, socket_y + 10], fill=(40, 44, 50))

    # ---- 车牌 ----
    pw, ph = rng.randint(200, 224), 68
    px = (car_l + car_r) // 2 - pw // 2
    py = car_b - 86
    d.rounded_rectangle(
        [px, py, px + pw, py + ph], radius=8, fill=PLATE_GREEN if is_ev else PLATE_BLUE
    )
    d.text((px + 12, py + 8), plate, font=f_plate, fill=(255, 255, 255))

    # ---- 顶部信息条（模拟真实监控 OSD，训练时属于干扰信息）----
    d.rectangle([0, 0, W, 116], fill=(24, 27, 32))
    d.text((36, 20), f"SYNTH  {scene}", font=f_title, fill=(240, 242, 245))
    d.text(
        (36, 70),
        f"PILE-{slot_idx + 1:03d} · {pile_status} · {vtype} · {plate}",
        font=f_small,
        fill=(178, 186, 196),
    )

    # ---- 光照抖动 + 噪声：让模型不至于只认固定像素 ----
    arr = np.asarray(img).astype(np.float32)
    arr *= rng.uniform(0.82, 1.12)
    arr += np.random.normal(0, rng.uniform(2, 7), arr.shape)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    lines = [
        f"{CLS_VEHICLE} "
        + " ".join(f"{v:.6f}" for v in _yolo_box(car_l, car_t, car_r - car_l, car_b - car_t)),
        f"{CLS_PLATE} " + " ".join(f"{v:.6f}" for v in _yolo_box(px, py, pw, ph)),
    ]
    meta = {
        "scene": scene,
        "vtype": vtype,
        "plate": plate,
        "pile_status": pile_status,
        "plugged": plugged,
        "bbox_vehicle": [car_l, car_t, car_r - car_l, car_b - car_t],
        "bbox_plate": [px, py, pw, ph],
    }
    return img, lines, meta


def write_data_yaml() -> None:
    """写 YOLO 训练配置（ultralytics 读取）。"""
    abs_path = DATASET.replace("\\", "/")
    content = (
        f"# 由 algo/tools/gen_synth_dataset.py 自动生成，勿手改\n"
        f"path: {abs_path}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"nc: {len(CLASS_NAMES)}\n"
        f"names: {CLASS_NAMES}\n"
    )
    with open(os.path.join(DATASET, "data.yaml"), "w", encoding="utf-8") as fh:
        fh.write(content)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--per-class", type=int, default=33, help="每类场景生成几张（默认 33，合计 132）"
    )
    ap.add_argument("--seed", type=int, default=42, help="随机种子，保证可复现")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    for split in ("train", "val"):
        os.makedirs(os.path.join(DATASET, "images", split), exist_ok=True)
        os.makedirs(os.path.join(DATASET, "labels", split), exist_ok=True)

    metas: dict[str, dict] = {}
    idx = 0
    for scene in sorted(SCENES):
        for n in range(args.per_class):
            img, lines, meta = draw_scene(rng, scene)
            name = f"{scene}_{n:03d}"
            split = "val" if rng.random() < VAL_RATIO else "train"

            img.save(os.path.join(DATASET, "images", split, f"{name}.jpg"), "JPEG", quality=90)
            with open(
                os.path.join(DATASET, "labels", split, f"{name}.txt"), "w", encoding="utf-8"
            ) as fh:
                fh.write("\n".join(lines) + "\n")

            meta["split"] = split
            metas[name] = meta
            idx += 1

    write_data_yaml()
    with open(os.path.join(DATASET, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(metas, fh, ensure_ascii=False, indent=2)

    n_train = sum(1 for m in metas.values() if m["split"] == "train")
    print(f"生成 {idx} 张：train {n_train} / val {idx - n_train}")
    print(f"数据集目录：{DATASET}")
    print(f"类别：{CLASS_NAMES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
