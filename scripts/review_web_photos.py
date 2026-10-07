"""网络实拍图的人工筛查工具（M1 第 2 步）。

``prescreen``：批量跑检测 + OCR，把**检出了车牌**的图渲染成联系表供人工目检，
并把结果写到 ``dataset_web_raw/preannotate.json``（供 ``annotate_web_photos.py`` 复用，
避免重复推理）。检不出车牌的图不进人工复核池。

``sheets``：把任意目录下的图拼成联系表（纯目检用，不跑模型）。

用法（仓库根目录）::

    .venv-algo\\Scripts\\python.exe scripts/review_web_photos.py prescreen
    .venv-algo\\Scripts\\python.exe scripts/review_web_photos.py sheets [目录] [--batch 48]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO, "algo", "dataset_web_raw")
SHEET = os.path.join(RAW, "sheets")
IMG = os.path.join(RAW, "images")

# 以脚本方式运行时仓库根不在 sys.path 上，algo.* 会导入失败
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _write_sheet(
    imgs: list[tuple[str, np.ndarray]], path: str, cell: int = 260, cols: int = 8
) -> None:
    rows = max(1, math.ceil(len(imgs) / cols))
    canvas = np.full((rows * cell, cols * cell, 3), 250, np.uint8)
    for i, (label, img) in enumerate(imgs):
        h, w = img.shape[:2]
        s = cell / max(h, w)
        img = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))))
        h, w = img.shape[:2]
        r, c = divmod(i, cols)
        y0, x0 = (cell - h) // 2, (cell - w) // 2
        canvas[r * cell + y0 : r * cell + y0 + h, c * cell + x0 : c * cell + x0 + w] = img
        cv2.putText(
            canvas,
            label,
            (c * cell + 6, r * cell + 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )
    cv2.imwrite(path, canvas)
    print("->", path)


def make_sheets(src_dir: str, batch: int = 48, cell: int = 260, cols: int = 8) -> None:
    os.makedirs(SHEET, exist_ok=True)
    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    for b in range(math.ceil(len(files) / batch)):
        chunk = files[b * batch : (b + 1) * batch]
        rows = math.ceil(len(chunk) / cols)
        sheet = np.full((rows * cell, cols * cell, 3), 250, np.uint8)
        for i, f in enumerate(chunk):
            img = cv2.imread(os.path.join(src_dir, f))
            if img is None:
                continue
            h, w = img.shape[:2]
            s = cell / max(h, w)
            img = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))))
            h, w = img.shape[:2]
            r, c = divmod(i, cols)
            y0, x0 = (cell - h) // 2, (cell - w) // 2
            sheet[r * cell + y0 : r * cell + y0 + h, c * cell + x0 : c * cell + x0 + w] = img
            cv2.putText(
                sheet,
                os.path.splitext(f)[0],
                (c * cell + 6, r * cell + 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
        p = os.path.join(SHEET, f"sheet_{b:02d}.jpg")
        cv2.imwrite(p, sheet)
        print("->", p)


def prescreen(conf: float) -> int:
    from hyperlpr3 import LicensePlateCatcher
    from ultralytics import YOLO

    from algo.recognize.plate import (
        DEFAULT_WEIGHTS,
        crop_plate_roi,
        judge_vtype_by_color,
        ocr_plate_in_frame,
    )

    files = sorted(f for f in os.listdir(IMG) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    model = YOLO(DEFAULT_WEIGHTS)
    catcher = LicensePlateCatcher()
    results: dict[str, dict] = {}
    box_imgs: list[tuple[str, np.ndarray]] = []
    roi_imgs: list[tuple[str, np.ndarray]] = []

    for i, f in enumerate(files):
        path = os.path.join(IMG, f)
        img = cv2.imread(path)
        if img is None:
            continue
        r = model.predict(path, conf=conf, device=0, verbose=False)[0]
        boxes = [
            {"xyxy": [float(v) for v in b.xyxy[0].tolist()], "conf": float(b.conf)}
            for b in r.boxes
            if r.names[int(b.cls)] == "plate"
        ]
        entry: dict = {"boxes": boxes, "shape": img.shape[:2]}
        if boxes:
            best = max(boxes, key=lambda b: b["conf"])
            roi = crop_plate_roi(img, best["xyxy"])
            text, score = ocr_plate_in_frame(img, catcher, best["xyxy"])
            entry["ocr"] = text
            entry["ocr_conf"] = round(score, 4)
            entry["vtype_auto"] = judge_vtype_by_color(roi)
            vis = img.copy()
            for bx in boxes:
                x1, y1, x2, y2 = (int(v) for v in bx["xyxy"])
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 180, 0), 3)
            box_imgs.append((os.path.splitext(f)[0], vis))
            if roi.size:
                k = max(1.0, 220.0 / max(1, roi.shape[1]))
                roi_big = cv2.resize(roi, (0, 0), fx=k, fy=k)
                cv2.putText(
                    roi_big,
                    f"{text or 'NONE'}|{entry['vtype_auto']}",
                    (4, 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )
                roi_imgs.append((os.path.splitext(f)[0], roi_big))
        results[f] = entry
        if i % 50 == 0:
            print(f"[prescreen] {i}/{len(files)}", flush=True)

    with open(os.path.join(RAW, "preannotate.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)

    os.makedirs(SHEET, exist_ok=True)
    for b in range(math.ceil(len(box_imgs) / 48)):
        _write_sheet(
            box_imgs[b * 48 : (b + 1) * 48],
            os.path.join(SHEET, f"keep_box_{b:02d}.jpg"),
            cell=260,
            cols=8,
        )
    for b in range(math.ceil(len(roi_imgs) / 72)):
        _write_sheet(
            roi_imgs[b * 72 : (b + 1) * 72],
            os.path.join(SHEET, f"keep_roi_{b:02d}.jpg"),
            cell=200,
            cols=9,
        )

    n_box = sum(1 for v in results.values() if v["boxes"])
    n_ocr = sum(1 for v in results.values() if v.get("ocr"))
    print(f"共 {len(files)} 张：检到车牌 {n_box}、OCR 出合法号码 {n_ocr}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_pre = sub.add_parser("prescreen")
    p_pre.add_argument("--conf", type=float, default=0.35)
    p_sheet = sub.add_parser("sheets")
    p_sheet.add_argument("src", nargs="?", default=IMG)
    p_sheet.add_argument("--batch", type=int, default=48)
    args = ap.parse_args()
    if args.cmd == "prescreen":
        return prescreen(args.conf)
    make_sheets(args.src, args.batch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
