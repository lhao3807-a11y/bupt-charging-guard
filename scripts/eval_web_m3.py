"""M3：real 模式在**网络实拍集**（dataset_web）上的端到端评估。

- 每张 val 图跑 ``recognize_frame``（新权重），对照 ``meta.json`` 里人工核验的
  ``plate`` / ``vtype`` 统计：整串匹配率、字符级准确率、牌色判定准确率。
- ``plate`` 为空的条目（检测/OCR 失败）只计失败，不跳过。
- 输出 JSON + 可读日志到 ``docs/acceptance/algo/07-eval-web.{json,log}``。

用法（仓库根目录，用 .venv-algo）::

    .venv-algo\\Scripts\\python.exe scripts/eval_web_m3.py [--weights algo/runs/detect/train_real_web/weights/best.pt]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

OUT_JSON = os.path.join(REPO, "docs", "acceptance", "algo", "07-eval-web.json")
OUT_LOG = os.path.join(REPO, "docs", "acceptance", "algo", "07-eval-web.log")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--weights",
        default=os.path.join(
            REPO, "algo", "runs", "detect", "train_real_web", "weights", "best.pt"
        ),
    )
    args = ap.parse_args()
    if not os.path.isfile(args.weights):
        print(f"权重不存在：{args.weights}（先跑 M2 训练）")
        return 1

    with open(os.path.join(REPO, "algo", "dataset_web", "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    val = {k: v for k, v in meta.items() if v["split"] == "val"}
    print(
        f"val 集 {len(val)} 张，权重 {os.path.basename(os.path.dirname(os.path.dirname(args.weights)))}"
    )

    from algo.recognize import plate as P

    rows = []
    for name in sorted(val):
        gt = val[name]
        img = os.path.join(REPO, "algo", "dataset_web", "images", "val", name)
        try:
            r = P.recognize_frame(img, weights=args.weights)
        except Exception as exc:  # noqa: BLE001 单张失败不拖垮整批
            rows.append(
                {
                    "file": name,
                    "error": str(exc)[:120],
                    "gt_plate": gt["plate"],
                    "gt_vtype": gt["vtype"],
                    "pred": None,
                }
            )
            continue
        if r is None:
            rows.append(
                {
                    "file": name,
                    "gt_plate": gt["plate"],
                    "gt_vtype": gt["vtype"],
                    "pred": None,
                    "reason": "未检出车牌",
                }
            )
            continue
        # 结构必须与契约 RecognitionResult 完全一致（§4）
        assert set(r) == {"plate", "vtype", "confidence", "bbox", "frame_time"}, f"字段不符 {name}"
        rows.append(
            {
                "file": name,
                "gt_plate": gt["plate"],
                "gt_vtype": gt["vtype"],
                "pred_plate": r["plate"],
                "pred_vtype": r["vtype"],
                "conf": round(r["confidence"], 4),
                "bbox": r["bbox"],
            }
        )

    n = len(rows)
    sum(1 for r in rows if r.get("pred") is not False and r.get("pred_plate") is not None)
    has_pred = [r for r in rows if r.get("pred_plate")]
    exact = sum(1 for r in has_pred if r["pred_plate"] == r["gt_plate"])
    vtype_ok = sum(1 for r in has_pred if r["pred_vtype"] == r["gt_vtype"])
    gt_chars = sum(len(r["gt_plate"]) for r in has_pred)
    ok_chars = sum(
        sum(a == b for a, b in zip(r["pred_plate"], r["gt_plate"]))
        for r in has_pred
        if len(r["pred_plate"]) == len(r["gt_plate"])
    )
    summary = {
        "weights": args.weights,
        "val_images": n,
        "detected_with_plate": len(has_pred),
        "ocr_exact_match": exact,
        "ocr_exact_pct": round(100 * exact / max(1, len(has_pred)), 2),
        "ocr_char_pct": round(100 * ok_chars / max(1, gt_chars), 2),
        "vtype_pct": round(100 * vtype_ok / max(1, len(has_pred)), 2),
        "rows": rows,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    with open(OUT_LOG, "w", encoding="utf-8") as fh:
        fh.write(f"M3 网络实拍集评估（{n} 张 val）\n")
        fh.write(f"权重: {args.weights}\n")
        fh.write(
            f"检出 {len(has_pred)}/{n}；OCR 整串 {exact}/{len(has_pred)}"
            f" = {summary['ocr_exact_pct']}%；字符级 {summary['ocr_char_pct']}%；"
            f"牌色 {vtype_ok}/{len(has_pred)} = {summary['vtype_pct']}%\n\n"
        )
        for r in rows:
            if not r.get("pred_plate"):
                fh.write(f"[MISS] {r['file']}  gt={r['gt_plate']}  ({r.get('reason', '')})\n")
            elif r["pred_plate"] != r["gt_plate"] or r["pred_vtype"] != r["gt_vtype"]:
                fh.write(
                    f"[WRONG] {r['file']}  gt={r['gt_plate']}/{r['gt_vtype']}"
                    f"  pred={r['pred_plate']}/{r['pred_vtype']}\n"
                )
    print(
        f"完成：检出 {len(has_pred)}/{n}，OCR 整串 {summary['ocr_exact_pct']}%，"
        f"字符级 {summary['ocr_char_pct']}%，牌色 {summary['vtype_pct']}%"
    )
    print("凭据 ->", OUT_JSON)
    return 0


if __name__ == "__main__":
    sys.exit(main())
