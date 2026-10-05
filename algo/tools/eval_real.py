"""在**真实数据集**（CCPD 转换产出）上评估端到端识别质量（PLAN 任务 5.5）。

为什么要单独一个评估脚本
------------------------
第 1 周的验收指标（mAP50=0.995）是在**合成集**上跑出来的，那个数字虚高：
合成牌是程序画出来的，无噪声、无倾斜、无逆光，模型在真实图上完全是另一回事。
任务 5.5 要求"在真实集上评估 OCR + 绿蓝牌判定"，所以这里把**检测 / OCR / 牌色**
三段拆开分别打分——只有拆开，才能看出掉点的是哪一段（否则一个端到端准确率
掉到 40%，你根本不知道该重训检测器还是调 HSV 阈值）。

三段指标
--------
1. **检测**：检出率（至少出一个框）、IoU≥0.5 命中率、平均 IoU
2. **OCR**：号码**整串完全匹配率** + 字符级准确率（只在拿到 ROI 的样本上算）
3. **牌色**：``judge_vtype_by_color`` 判定正确率（绿=新能源 / 蓝=燃油）

以及两段端到端：**E2E-OCR**（号码对，含检不出算错）、**E2E-全对**（号码+牌色都对）。

``--gt-box`` 用法
-----------------
带这个开关时**跳过检测器**，直接用 CCPD 文件名里带的真值框裁 ROI。
这用来隔离"OCR 本身行不行"和"检测器框得准不准"：若 ``--gt-box`` 下 OCR 有 90%
而不带只有 60%，说明瓶颈在检测而不是 OCR，该去补数据重训而不是调阈值。

用法::

    .venv-algo\\Scripts\\python.exe algo/tools/eval_real.py --split val
    .venv-algo\\Scripts\\python.exe algo/tools/eval_real.py --split val --gt-box
    .venv-algo\\Scripts\\python.exe algo/tools/eval_real.py --weights algo/runs/detect/train_real/weights/best.pt

产出 ``docs/acceptance/algo/05-eval-real.json``（入库，作为验收凭据）。
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ALGO = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ALGO, ".."))

DATA_DIR = os.path.join(ALGO, "dataset_real")
REAL_BEST_PT = os.path.join(ALGO, "runs", "detect", "train_real", "weights", "best.pt")
OUT_JSON = os.path.join(REPO, "docs", "acceptance", "algo", "05-eval-real.json")

#: IoU 达到该值才算"框中了车牌"（COCO 常用阈值）
IOU_HIT = 0.5


def iou(box_a: list[float], box_b: list[float]) -> float:
    """两个 xyxy 框的交并比。"""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def char_accuracy(pred: str, gt: str) -> float:
    """字符级准确率：逐位比对，长度不一致时缺位记 0 分。

    整串完全匹配率过于苛刻（8 位错 1 位就归零），字符级准确能反映"是不是快对了"，
    调阈值时看它比看整串率更容易判断方向。
    """
    if not gt:
        return 0.0
    hit = sum(1 for i, ch in enumerate(gt) if i < len(pred) and pred[i] == ch)
    return hit / len(gt)


def load_samples(data_dir: str, split: str, limit: int) -> list[tuple[str, dict]]:
    """从 meta.json 读出样本（图片路径 + 真值），按 split 过滤。"""
    meta_path = os.path.join(data_dir, "meta.json")
    if not os.path.isfile(meta_path):
        raise SystemExit(f"缺少 {meta_path}，请先跑 algo/tools/ccpd_to_yolo.py")

    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    out = []
    for name, info in sorted(meta.items()):
        if split != "all" and info.get("split") != split:
            continue
        img_path = os.path.join(data_dir, "images", info["split"], name)
        if not os.path.isfile(img_path):
            continue
        out.append((img_path, info))
    return out[:limit] if limit else out


def evaluate(
    samples: list[tuple[str, dict]],
    *,
    weights: str,
    conf: float,
    gt_box: bool,
) -> dict:
    """逐样本跑 检测 → OCR → 牌色，汇总成指标字典。"""
    import cv2
    from hyperlpr3 import LicensePlateCatcher

    from algo.recognize.plate import crop_plate_roi, judge_vtype_by_color, ocr_plate
    from algo.train.detect import detect_boxes

    yolo = None if gt_box else weights
    catcher = LicensePlateCatcher()

    n = len(samples)
    rows = []
    for img_path, info in samples:
        img = cv2.imread(img_path)
        if img is None:
            continue

        gt_box_xyxy = [float(v) for v in info["bbox_plate"]]
        if gt_box:
            roi_box = gt_box_xyxy
            best_iou = 1.0
            detected = True
        else:
            boxes = detect_boxes(img_path, conf=conf, weights=yolo)
            if not boxes:
                rows.append(
                    {
                        "name": os.path.basename(img_path),
                        "gt_plate": info["plate"],
                        "gt_vtype": info["vtype"],
                        "detected": False,
                        "iou": 0.0,
                        "ocr": "",
                        "vtype": "",
                    }
                )
                continue
            # 真实集是单类（plate），直接取置信度最高的框
            top = max(boxes, key=lambda b: b["conf"])
            roi_box = top["bbox_xyxy"]
            best_iou = iou(roi_box, gt_box_xyxy)
            detected = True

        roi = crop_plate_roi(img, roi_box)
        if roi.size == 0:
            rows.append(
                {
                    "name": os.path.basename(img_path),
                    "gt_plate": info["plate"],
                    "gt_vtype": info["vtype"],
                    "detected": detected,
                    "iou": best_iou,
                    "ocr": "",
                    "vtype": "",
                }
            )
            continue

        text, _score = ocr_plate(roi, catcher)
        rows.append(
            {
                "name": os.path.basename(img_path),
                "gt_plate": info["plate"],
                "gt_vtype": info["vtype"],
                "detected": detected,
                "iou": best_iou,
                "ocr": text,
                "vtype": judge_vtype_by_color(roi),
            }
        )

    def has_roi(row: dict) -> bool:
        """牌色非空即说明拿到了 ROI（空串=检测失败或未裁出图）。"""
        return bool(row["vtype"])

    def rate(pool_filter, predicate) -> float:
        pool = [r for r in rows if pool_filter(r)]
        if not pool:
            return 0.0
        return sum(1 for r in pool if predicate(r)) / len(pool)

    all_rows = lambda r: True
    summary = {
        "n": n,
        "mode": "gt-box" if gt_box else "detect",
        "weights": None if gt_box else weights,
        "conf": conf,
        "detect_any": rate(all_rows, lambda r: r["detected"]),
        "detect_iou_hit": rate(all_rows, lambda r: r["iou"] >= IOU_HIT),
        "mean_iou": float(np.mean([r["iou"] for r in rows])) if rows else 0.0,
        "roi_count": sum(1 for r in rows if has_roi(r)),
        "ocr_exact": rate(has_roi, lambda r: r["ocr"] == r["gt_plate"]),
        "ocr_char_acc": (
            float(np.mean([char_accuracy(r["ocr"], r["gt_plate"]) for r in rows if has_roi(r)]))
            if any(has_roi(r) for r in rows)
            else 0.0
        ),
        "vtype_acc": rate(has_roi, lambda r: r["vtype"] == r["gt_vtype"]),
        "e2e_ocr": rate(all_rows, lambda r: bool(r["ocr"]) and r["ocr"] == r["gt_plate"]),
        "e2e_all": rate(
            all_rows,
            lambda r: bool(r["ocr"]) and r["ocr"] == r["gt_plate"] and r["vtype"] == r["gt_vtype"],
        ),
    }

    # 分牌色拆解：绿/蓝两类的难度差异很大（蓝牌字符少一位、反光更强）
    for label in ("新能源", "燃油"):
        pool = [r for r in rows if r["gt_vtype"] == label and has_roi(r)]
        summary[f"by_vtype_{label}"] = {
            "n": len(pool),
            "ocr_exact": (
                sum(1 for r in pool if r["ocr"] == r["gt_plate"]) / len(pool) if pool else 0.0
            ),
            "vtype_acc": (
                sum(1 for r in pool if r["vtype"] == r["gt_vtype"]) / len(pool) if pool else 0.0
            ),
        }

    bad = [r for r in rows if has_roi(r) and r["ocr"] != r["gt_plate"]][:20]
    return {"summary": summary, "rows": rows, "ocr_failures": bad}


def _pct(value: float) -> str:
    return f"{value * 100:6.2f}%"


def print_report(result: dict) -> None:
    s = result["summary"]
    pct = _pct
    print("=" * 62)
    print(f"真实集评估（模式：{s['mode']}，样本 {s['n']} 张）")
    print("=" * 62)
    if s["mode"] == "detect":
        print(f"  检测 检出率          {pct(s['detect_any'])}")
        print(f"  检测 IoU≥{IOU_HIT} 命中率   {pct(s['detect_iou_hit'])}")
        print(f"  检测 平均 IoU        {s['mean_iou']:.4f}")
    print(f"  OCR  整串完全匹配     {pct(s['ocr_exact'])}  (ROI 样本 {s['roi_count']} 张)")
    print(f"  OCR  字符级准确率     {pct(s['ocr_char_acc'])}")
    print(f"  牌色 判定正确率       {pct(s['vtype_acc'])}")
    print(f"  端到端 号码正确       {pct(s['e2e_ocr'])}")
    print(f"  端到端 号码+牌色全对  {pct(s['e2e_all'])}")
    for label in ("新能源", "燃油"):
        b = s[f"by_vtype_{label}"]
        print(
            f"    └ {label}（{b['n']} 张）：OCR {pct(b['ocr_exact'])}  牌色 {pct(b['vtype_acc'])}"
        )
    if result["ocr_failures"]:
        print("\n  OCR 失败样例（前 20）：")
        for r in result["ocr_failures"]:
            print(f"    {r['name']:<16} 真值={r['gt_plate']:<9} 识别={r['ocr'] or '(空)'}")
    print("=" * 62)


def main() -> int:
    ap = argparse.ArgumentParser(description="真实集端到端评估（任务 5.5）")
    ap.add_argument("--data", default=DATA_DIR, help="数据集目录（含 meta.json）")
    ap.add_argument("--split", default="val", choices=["train", "val", "all"])
    ap.add_argument("--weights", default=REAL_BEST_PT, help="检测器权重；--gt-box 时忽略")
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--gt-box", action="store_true", help="跳过检测器，直接用真值框裁 ROI")
    ap.add_argument("--limit", type=int, default=0, help="最多评估多少张（0=全部）")
    ap.add_argument("--out", default=OUT_JSON, help="结果 JSON 输出路径")
    args = ap.parse_args()

    if not args.gt_box and not os.path.isfile(args.weights):
        print(f"缺少权重 {args.weights}；先跑 train --name train_real，或加 --gt-box 跳过检测")
        return 1

    samples = load_samples(args.data, args.split, args.limit)
    if not samples:
        print(f"没有可评估样本：{args.data}（split={args.split}）")
        return 1

    result = evaluate(samples, weights=args.weights, conf=args.conf, gt_box=args.gt_box)
    print_report(result)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result["summary"], fh, ensure_ascii=False, indent=2)
    print(f"结果已写入：{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
