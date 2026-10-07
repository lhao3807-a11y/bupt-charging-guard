"""网络实拍图的预标注 + 落盘（M1 第 3 步）。

流程
----
1. 读 ``dataset_web_raw/review.json``（人工筛查结论：保留/剔除 + 四类场景标签；
   模型漏检/误检的图可填 ``boxes_override`` 手工兜底）。
2. 优先复用 ``dataset_web_raw/preannotate.json``（prescreen 的检测+OCR 结果）；
   没有才现场推理。
3. 产出 ``algo/dataset_web/``：
   - images/{train,val}/  labels/{train,val}/（YOLO 格式，单类 plate=0）
   - meta.json（对齐 dataset_real：key 带 .jpg，bbox_plate=[x1,y1,x2,y2]）
   - licenses.csv（每张图的来源页/许可/作者，满足"可核查数据清单"）
   - data.yaml

用法（仓库根目录）::

    .venv-algo\\Scripts\\python.exe scripts/annotate_web_photos.py [--conf 0.3]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

import cv2

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO, "algo", "dataset_web_raw")
DST = os.path.join(REPO, "algo", "dataset_web")
SHEET = os.path.join(RAW, "sheets")

# 以脚本方式运行时仓库根不在 sys.path 上，algo.* 会导入失败
if REPO not in sys.path:
    sys.path.insert(0, REPO)

CLASS_ID = 0  # YOLO 单类：plate
CLASS_NAME = "plate"


def _load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dump_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _detect_all(keep: dict, conf: float) -> dict[str, dict]:
    """对保留图跑检测 + OCR；有 preannotate.json 就直接复用。"""
    pre_path = os.path.join(RAW, "preannotate.json")
    if os.path.isfile(pre_path):
        pre = _load_json(pre_path)
        missing = [f for f in keep if f not in pre]
        if not missing:
            print(f"复用 prescreen 结果（{len(pre)} 条）")
            return pre
        print(f"prescreen 缺 {len(missing)} 张，需补推理")

    from hyperlpr3 import LicensePlateCatcher
    from ultralytics import YOLO

    from algo.recognize.plate import (
        DEFAULT_WEIGHTS,
        crop_plate_roi,
        judge_vtype_by_color,
        ocr_plate_in_frame,
    )

    model = YOLO(DEFAULT_WEIGHTS)
    catcher = LicensePlateCatcher()
    results: dict[str, dict] = {}
    for f in sorted(keep):
        path = os.path.join(RAW, "images", f)
        img = cv2.imread(path)
        if img is None:
            print("[skip 读不到]", f)
            continue
        r = model.predict(path, conf=conf, device=0, verbose=False)[0]
        boxes = [
            {"xyxy": [float(v) for v in b.xyxy[0].tolist()], "conf": float(b.conf)}
            for b in r.boxes
            if r.names[int(b.cls)] == CLASS_NAME
        ]
        entry: dict = {"boxes": boxes, "shape": img.shape[:2]}
        if boxes:
            best = max(boxes, key=lambda b: b["conf"])
            roi = crop_plate_roi(img, best["xyxy"])
            text, score = ocr_plate_in_frame(img, catcher, best["xyxy"])
            entry["ocr"] = text
            entry["ocr_conf"] = round(score, 4)
            entry["vtype_auto"] = judge_vtype_by_color(roi)
        results[f] = entry
    _dump_json(pre_path, results)
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conf", type=float, default=0.3)
    ap.add_argument("--val-frac", type=int, default=25, help="val 占比（按文件名哈希，百分比）")
    args = ap.parse_args()

    review_path = os.path.join(RAW, "review.json")
    if not os.path.isfile(review_path):
        print("缺少 review.json（先完成人工筛查）")
        return 1
    review = _load_json(review_path)
    cand_meta = {
        c["file"]: c for c in _load_json(os.path.join(RAW, "meta_candidates.json")) if c.get("file")
    }

    keep = {f: v for f, v in review.items() if v.get("keep")}
    print(f"review.json：保留 {len(keep)} / 剔除 {len(review) - len(keep)}")
    results = _detect_all(keep, args.conf)

    # ---- 落盘 dataset_web ---------------------------------------------------
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        os.makedirs(os.path.join(DST, sub), exist_ok=True)
    meta: dict[str, dict] = {}
    no_box: list[str] = []
    for f, r in sorted(results.items()):
        info = keep.get(f)
        if info is None:
            continue
        boxes = (
            [{"xyxy": [float(v) for v in bx], "conf": 1.0} for bx in info["boxes_override"]]
            if info.get("boxes_override")
            else r.get("boxes", [])
        )
        if not boxes:
            no_box.append(f)
            continue
        h, w = r["shape"]
        # 同车牌必须同 split（同车多角度若跨 train/val 会造成指标虚高）
        group = info.get("plate") or f
        split = (
            "val"
            if int(hashlib.md5(group.encode()).hexdigest(), 16) % 100 < args.val_frac
            else "train"
        )
        img = cv2.imread(os.path.join(RAW, "images", f))
        if img is None:
            continue
        stem = os.path.splitext(f)[0]
        new_name = f"web_{stem}{os.path.splitext(f)[1].lower()}"
        cv2.imwrite(os.path.join(DST, "images", split, new_name), img)
        lines = []
        for bx in boxes:
            x1, y1, x2, y2 = bx["xyxy"]
            cx, cy, bw, bh = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h
            lines.append(f"{CLASS_ID} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        _write_text(
            os.path.join(DST, "labels", split, os.path.splitext(new_name)[0] + ".txt"),
            "\n".join(lines) + "\n",
        )
        src = cand_meta.get(f, {})
        meta[new_name] = {
            "split": split,
            "vtype": info.get("vtype") or r.get("vtype_auto", ""),
            "plate": info.get("plate") or r.get("ocr", ""),
            "scene": info.get("scene", ""),
            "bbox_plate": [round(v) for v in max(boxes, key=lambda b: b["conf"])["xyxy"]],
            "source": src.get("page") or src.get("url", ""),
            "license": src.get("license", ""),
            "artist": src.get("artist", ""),
            "scene_source_query": src.get("query", ""),
        }

    _dump_json(os.path.join(DST, "meta.json"), meta)
    with open(os.path.join(DST, "licenses.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh)
        wr.writerow(["file", "scene", "source_page", "license", "artist"])
        for k, v in sorted(meta.items()):
            wr.writerow([k, v["scene"], v["source"], v["license"], v["artist"]])

    _write_text(
        os.path.join(DST, "data.yaml"),
        f"path: {DST}\ntrain: images/train\nval: images/val\nnames:\n  0: {CLASS_NAME}\n",
    )
    print(f"完成：{len(meta)} 张入库（train/val 见 meta），无框待处理 {len(no_box)}：{no_box[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
