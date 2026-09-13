"""生成识别桩用的模拟测试帧（占位用）。

说明
----
识别桩 stub **不读图片内容**，只按 ``frame_ref`` 去 ``algo/samples/labels/``
取同名 JSON（CONTRACT §6.1 / §10）。本脚本生成的图片因此只是**占位帧**：
用于让 ``algo/samples/frames/`` 有真实文件、便于后台「实时识别预览」调试与
演示时肉眼对照。**第 2 周（M1 采集模块）请用真实摄像头/图片集替换。**

图片内容 = 车位线 + 充电桩 + 车辆色块 + 车牌，与同目录 JSON 的 plate 一致。

依赖：``pip install pillow``（仅本脚本需要，未列入项目依赖）
用法：``python algo/tools/make_mock_frames.py``
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.normpath(os.path.join(HERE, "..", "samples"))
FRAMES_DIR = os.path.join(SAMPLES, "frames")
LABELS_DIR = os.path.join(SAMPLES, "labels")

W, H = 1280, 720

# 与同目录 JSON 对应的场景说明（仅画在图上，便于人工核对）
SCENES = {
    "001": ("PILE-001", "充电中", "规则④ 正常充电 → 不提醒"),
    "002": ("PILE-004", "空闲", "规则① 燃油车占位 → 提醒"),
    "003": ("PILE-003", "空闲", "规则② 新能源未充电久停 → 提醒"),
    "004": ("PILE-002", "已充满", "规则③ 充满超时未移车 → 提醒"),
}

# 车牌牌面底色：绿牌 = 新能源，蓝牌 = 燃油（契约 §3.1 车型判定依据）
PLATE_GREEN = (0, 132, 84)
PLATE_BLUE = (20, 60, 150)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]


def load_font(size: int):
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_frame(name: str, panel_x: int) -> Image.Image:
    with open(os.path.join(LABELS_DIR, f"{name}.json"), encoding="utf-8") as f:
        label = json.load(f)

    pile_id, pile_status, scenario = SCENES[name]
    is_ev = label["vtype"] == "新能源"

    img = Image.new("RGB", (W, H), (58, 62, 68))
    d = ImageDraw.Draw(img)

    f_small = load_font(22)
    f_plate = load_font(46)
    f_title = load_font(34)

    # 地面 + 三个车位（当前车辆所在车位高亮）
    ground = (86, 90, 96)
    d.rectangle([0, 260, W, H], fill=ground)
    for i in range(4):
        x = 60 + i * 330
        d.line([(x, 300), (x, H - 40)], fill=(220, 220, 220), width=5)
    d.line([(60, H - 40), (60 + 3 * 330, H - 40)], fill=(220, 220, 220), width=5)

    slot_x = 60 + panel_x * 330
    d.rectangle([slot_x + 8, 306, slot_x + 322, H - 44], outline=(255, 214, 102), width=4)

    # 充电桩立柱
    pile_x = slot_x + 250
    d.rectangle([pile_x, 150, pile_x + 56, 330], fill=(210, 214, 220))
    d.rectangle([pile_x + 8, 170, pile_x + 48, 230], fill=(40, 44, 50))
    # 桩身闪电标记（矢量绘制，避免字体缺字）
    cx, cy = pile_x + 28, 200
    d.polygon(
        [
            (cx + 6, cy - 20),
            (cx - 8, cy + 3),
            (cx + 1, cy + 3),
            (cx - 5, cy + 20),
            (cx + 10, cy - 4),
            (cx + 1, cy - 4),
        ],
        fill=(255, 214, 102),
    )

    # 车辆色块（新能源偏绿、燃油偏蓝）
    body = (52, 122, 92) if is_ev else (60, 92, 168)
    car_l, car_t, car_r, car_b = slot_x + 26, 380, slot_x + 260, 590
    d.rounded_rectangle([car_l, car_t, car_r, car_b], radius=18, fill=body)
    d.rounded_rectangle(
        [car_l + 22, car_t + 34, car_r - 22, car_t + 128], radius=10, fill=(196, 214, 226)
    )

    # 车牌（绿牌/蓝牌）
    pw, ph = 214, 68
    px = (car_l + car_r) // 2 - pw // 2
    py = car_b - 86
    d.rounded_rectangle(
        [px, py, px + pw, py + ph], radius=8, fill=PLATE_GREEN if is_ev else PLATE_BLUE
    )
    d.text((px + 14, py + 8), label["plate"], font=f_plate, fill=(255, 255, 255))

    # 顶部信息条
    d.rectangle([0, 0, W, 116], fill=(24, 27, 32))
    d.text((36, 20), f"模拟帧（占位）  {name}.jpg", font=f_title, fill=(240, 242, 245))
    d.text(
        (36, 70),
        f"{pile_id} · {pile_status} · {label['vtype']} · "
        f"置信度 {label['confidence']:.2f} · {label['frame_time']}",
        font=f_small,
        fill=(178, 186, 196),
    )

    # 底部场景说明
    d.rectangle([0, H - 40, W, H], fill=(24, 27, 32))
    d.text((36, H - 34), scenario, font=f_small, fill=(255, 214, 102))

    return img


def main() -> None:
    os.makedirs(FRAMES_DIR, exist_ok=True)
    for idx, name in enumerate(sorted(SCENES)):
        img = draw_frame(name, panel_x=idx % 3)
        out = os.path.join(FRAMES_DIR, f"{name}.jpg")
        img.save(out, "JPEG", quality=88)
        print("generated", out)


if __name__ == "__main__":
    main()
