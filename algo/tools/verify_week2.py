"""Evaluate saved M2/M3 models against fixed, sourced validation manifests."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs/acceptance/algo/week2-web"


def manifest_digest(path: Path) -> str:
    """Canonical JSON hash, stable across Git CRLF/LF checkout differences."""
    value = json.loads(path.read_text(encoding="utf-8"))
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def recognition_metrics(rows: list[dict]) -> dict:
    n = len(rows)
    detected = [r for r in rows if r["result"] is not None]

    def same_plate(r):
        return (
            bool(r["result"])
            and bool(r["result"]["plate"])
            and r["result"]["plate"] == r["gt_plate"]
        )

    def same_vtype(r):
        return bool(r["result"]) and r["result"]["vtype"] == r["gt_vtype"]

    def rate(pool, test):
        return sum(bool(test(r)) for r in pool) / len(pool) if pool else 0.0

    return {
        "images": n,
        "detected": len(detected),
        "detection_iou50_all": rate(rows, lambda r: r["iou"] >= 0.5),
        "ocr_exact_detected": rate(detected, same_plate),
        "ocr_exact_all": rate(rows, same_plate),
        "vtype_correct_detected": rate(detected, same_vtype),
        "vtype_correct_all": rate(rows, same_vtype),
        "plate_and_vtype_correct_all": rate(rows, lambda r: same_plate(r) and same_vtype(r)),
    }


def save_json(path: Path, item):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")


def detection_counts(
    predicted: list[list[float]], truth: list[list[float]], ignored: list[list[float]] | None = None
) -> dict:
    from algo.recognize.box import iou

    unmatched = set(range(len(truth)))
    tp = 0
    ignore_count = 0
    for box in predicted:
        if unmatched:
            best = max(unmatched, key=lambda i: iou(box, truth[i]))
            if iou(box, truth[best]) >= 0.5:
                unmatched.remove(best)
                tp += 1
                continue
        if any(iou(box, b) >= 0.5 for b in (ignored or [])):
            ignore_count += 1
    return {
        "tp": tp,
        "fp": len(predicted) - tp - ignore_count,
        "fn": len(truth) - tp,
        "ignored": ignore_count,
    }


def evaluate_detection(kind: str) -> dict:
    from ultralytics import YOLO

    from algo.train.detect import select_device

    weights = ROOT / f"algo/runs/detect/train_{kind}_web/weights/best.pt"
    data = ROOT / f".tmp-m2/data/{kind}/data.yaml"
    model = YOLO(str(weights))
    metrics = model.val(
        data=str(data),
        device=select_device(),
        imgsz=640,
        batch=8,
        workers=0,
        plots=True,
        project=str(ROOT / "algo/runs/detect"),
        name=f"val_{kind}_web",
        exist_ok=True,
    )
    manifest = ROOT / f"algo/dataset_{kind}_web/manifest.json"
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    val = [r for r in rows if r["split"] == "val"]
    report = {
        "kind": kind,
        "weights": weights.relative_to(ROOT).as_posix(),
        "weights_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
        "manifest_sha256": manifest_digest(manifest),
        "manifest_hash_format": "canonical-json-utf8-sortkeys-compact",
        "train_images": len(rows) - len(val),
        "val_images": len(val),
        "val_boxes": sum(len(r["boxes_xyxy"]) for r in val),
        "map50": float(metrics.box.map50),
        "map50_95": float(metrics.box.map),
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
    }
    operating_rows = []
    for item in val:
        prediction = model.predict(
            str(ROOT / item["image"]), conf=0.4, imgsz=640, device=select_device(), verbose=False
        )[0]
        boxes = prediction.boxes.xyxy.tolist()
        counts = detection_counts(boxes, item["boxes_xyxy"], item.get("ignored_boxes_xyxy"))
        operating_rows.append(
            {
                "file": item["file"],
                "boxes_xyxy": boxes,
                "confidence": prediction.boxes.conf.tolist(),
                **counts,
            }
        )
    counts = {key: sum(r[key] for r in operating_rows) for key in ("tp", "fp", "fn", "ignored")}
    if kind == "vehicle":
        report["map_scope"] = (
            "Raw Ultralytics mAP on large-vehicle labels, without ignored-region support; correct small-vehicle detections outside the labeling scope can conservatively lower this mAP. Operating metrics below handle manually recorded ignored regions."
        )
    report["operating_confidence_threshold"] = 0.4
    report["operating_counts_iou50"] = counts
    report["operating_precision"] = (
        counts["tp"] / (counts["tp"] + counts["fp"]) if counts["tp"] + counts["fp"] else 0.0
    )
    report["operating_recall"] = (
        counts["tp"] / (counts["tp"] + counts["fn"]) if counts["tp"] + counts["fn"] else 0.0
    )
    report["predictions"] = operating_rows
    save_json(OUT / f"{kind}-detection.json", report)
    return report


def evaluate_recognition() -> dict:
    from algo.recognize.box import iou
    from algo.recognize.plate import DEFAULT_WEIGHTS, recognize_frame
    from backend.app.schemas import RecognitionResult

    manifest = ROOT / "algo/dataset_plate_web/manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    rows = []
    for item in data:
        if item["split"] != "val":
            continue
        result = recognize_frame(
            str(ROOT / item["image"]), frame_time=datetime(2026, 10, 10, 0, 0, 0)
        )
        overlap = 0.0
        if result is not None:
            RecognitionResult.model_validate(result)
            x, y, w, h = result["bbox"]
            overlap = iou([x, y, x + w, y + h], item["boxes_xyxy"][0])
        row = {
            "file": item["file"],
            "source_page": item["source_page"],
            "gt_plate": item["plate"],
            "gt_vtype": item["vtype"],
            "result": result,
            "iou": overlap,
        }
        rows.append(row)
        print(f"{item['file']}: {result}", flush=True)
    summary = recognition_metrics(rows)
    report = {
        "weights": Path(DEFAULT_WEIGHTS).relative_to(ROOT).as_posix(),
        "weights_sha256": hashlib.sha256(Path(DEFAULT_WEIGHTS).read_bytes()).hexdigest(),
        "manifest_sha256": manifest_digest(manifest),
        "manifest_hash_format": "canonical-json-utf8-sortkeys-compact",
        "confidence_threshold": 0.4,
        "summary": summary,
        "rows": rows,
        "failures": [
            r
            for r in rows
            if r["result"] is None
            or r["result"]["plate"] != r["gt_plate"]
            or r["result"]["vtype"] != r["gt_vtype"]
        ],
        "contract_valid_outputs": sum(r["result"] is not None for r in rows),
    }
    save_json(OUT / "recognition.json", report)
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["vehicle", "plate", "recognition"])
    task = parser.parse_args().task
    result = evaluate_recognition() if task == "recognition" else evaluate_detection(task)
    print(json.dumps(result.get("summary", result), ensure_ascii=False, indent=2))
