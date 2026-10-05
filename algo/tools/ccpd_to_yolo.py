"""把 CCPD 公开数据集转成 YOLO 格式（PLAN 任务 5.3–5.4 的备料工具）。

**CCPD 的标注规则**：没有独立的标注文件，全部信息编码在**文件名**里::

    [area]-[tilt]-[bbox]-[four_points]-[label]-[brightness]-[blur].jpg
    025-95_113-154&383_386&473-386&473_177&454_154&383_363&402-0_0_22_27_27_33_16-37-15.jpg
         ↑              ↑ 车牌外接框（左上 & 右下）      ↑ 7/8 位字符索引

**为什么只标 `plate` 一类**：CCPD 只提供车牌框，**没有车辆框**。
本项目合成集是 `vehicle` + `plate` 两类，若把 CCPD 混进去训练，
真实图上的车会被当成背景（漏标），反而把 `vehicle` 类教坏。
故本脚本产出**单类（plate）的真实数据集**，单独训练与评估，
`vehicle` 类仍由合成集负责 —— 校园实拍补标车辆框后再合并（见 algo/README.md）。

用法::

    .venv-algo\\Scripts\\python.exe algo\\tools\\ccpd_to_yolo.py --zip algo/dataset_raw/ccpd2020-green.zip
    .venv-algo\\Scripts\\python.exe algo\\tools\\ccpd_to_yolo.py --zip <zip> --max 400 --val-ratio 0.2

产出 ``algo/dataset_real/``（data.yaml / images / labels / meta.json），**不入库**。
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ALGO = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ALGO, ".."))
OUT_DIR = os.path.join(ALGO, "dataset_real")

# CCPD 字符集（与官方定义一致）
PROVINCES = [
    "皖", "沪", "津", "渝", "冀", "晋", "蒙", "辽", "吉", "黑", "苏", "浙", "京", "闽",
    "赣", "鲁", "豫", "鄂", "湘", "粤", "桂", "琼", "川", "贵", "云", "藏", "陕", "甘",
    "青", "宁", "新", "警", "学", "O",
]
ALPHABETS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R",
    "S", "T", "U", "V", "W", "X", "Y", "Z", "O",
]
ADS = ALPHABETS[:-1] + ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "O"]


def parse_ccpd_name(name: str) -> dict | None:
    """从 CCPD 文件名解析出 bbox 与车牌号；解析不了返回 None。"""
    stem = os.path.splitext(os.path.basename(name))[0]
    parts = stem.split("-")
    if len(parts) < 5:
        return None

    # 字段 3：bbox，形如 154&383_386&473
    try:
        left, right = parts[2].split("_")
        x1, y1 = (int(v) for v in left.split("&"))
        x2, y2 = (int(v) for v in right.split("&"))
    except ValueError:
        return None
    if x2 <= x1 or y2 <= y1:
        return None

    # 字段 5：字符索引，形如 0_0_22_27_27_33_16（绿牌 8 位）
    idx = [int(v) for v in parts[4].split("_") if v.isdigit()]
    if len(idx) < 7:
        return None
    try:
        plate = PROVINCES[idx[0]] + ALPHABETS[idx[1]] + "".join(ADS[i] for i in idx[2:])
    except IndexError:
        return None

    return {
        "bbox": [x1, y1, x2, y2],
        "plate": plate,
        "vtype": "新能源" if len(idx) >= 8 else "燃油",
    }


def _to_yolo_line(bbox: list[int], width: int, height: int) -> str:
    """CCPD 外接框 → YOLO `cls cx cy w h`（归一化，cls=0 即 plate）。"""
    x1, y1, x2, y2 = bbox
    cx = ((x1 + x2) / 2) / width
    cy = ((y1 + y2) / 2) / height
    w = (x2 - x1) / width
    h = (y2 - y1) / height
    return f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def extract(zip_path: str, work_dir: str) -> str:
    """解压到工作目录，返回图片所在根目录。"""
    os.makedirs(work_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(work_dir)
    return work_dir


def build(zip_path: str, max_images: int, val_ratio: float, seed: int) -> dict:
    import cv2

    work = os.path.join(OUT_DIR, "_extracted")
    extract(zip_path, work)

    samples = []
    for root, _dirs, files in os.walk(work):
        for filename in files:
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            info = parse_ccpd_name(filename)
            if info is None:
                continue
            samples.append((os.path.join(root, filename), info))
    if not samples:
        raise SystemExit(f"没解析出任何 CCPD 样本：{zip_path}（确认是不是 CCPD 命名格式）")

    rng = random.Random(seed)
    rng.shuffle(samples)
    samples = samples[:max_images]

    # 先清掉旧产出，避免多次运行残留
    for split in ("train", "val"):
        shutil.rmtree(os.path.join(OUT_DIR, "images", split), ignore_errors=True)
        shutil.rmtree(os.path.join(OUT_DIR, "labels", split), ignore_errors=True)
        os.makedirs(os.path.join(OUT_DIR, "images", split), exist_ok=True)
        os.makedirs(os.path.join(OUT_DIR, "labels", split), exist_ok=True)

    val_count = max(1, int(len(samples) * val_ratio))
    meta: dict[str, dict] = {}
    for i, (src, info) in enumerate(samples):
        split = "val" if i < val_count else "train"
        img = cv2.imread(src)
        if img is None:
            continue
        height, width = img.shape[:2]
        name = f"real_{i:04d}"
        cv2.imwrite(os.path.join(OUT_DIR, "images", split, f"{name}.jpg"), img)
        with open(
            os.path.join(OUT_DIR, "labels", split, f"{name}.txt"), "w", encoding="utf-8"
        ) as fh:
            fh.write(_to_yolo_line(info["bbox"], width, height) + "\n")
        meta[f"{name}.jpg"] = {
            "split": split,
            "vtype": info["vtype"],
            "plate": info["plate"],
            "bbox_plate": info["bbox"],
            "source": os.path.relpath(src, REPO),
            "scene": "public-real",
        }

    with open(os.path.join(OUT_DIR, "data.yaml"), "w", encoding="utf-8") as fh:
        fh.write(f"path: {OUT_DIR}\ntrain: images/train\nval: images/val\n")
        fh.write("names:\n  0: plate\n")
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    return {
        "total": len(meta),
        "train": sum(1 for m in meta.values() if m["split"] == "train"),
        "val": sum(1 for m in meta.values() if m["split"] == "val"),
        "green": sum(1 for m in meta.values() if m["vtype"] == "新能源"),
        "blue": sum(1 for m in meta.values() if m["vtype"] == "燃油"),
        "out": OUT_DIR,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CCPD → YOLO 数据集转换")
    parser.add_argument("--zip", required=True, help="CCPD 压缩包路径")
    parser.add_argument("--max", type=int, default=400, help="最多取多少张")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="验证集比例")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()

    summary = build(args.zip, args.max, args.val_ratio, args.seed)
    print(
        "转换完成：共 {total} 张（train {train} / val {val}），"
        "绿牌 {green} / 蓝牌 {blue}".format(**summary)
    )
    print(f"输出目录：{summary['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
