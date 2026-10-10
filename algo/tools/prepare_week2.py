"""Build reproducible, sourced M2/M3 datasets from tracked photos and annotations."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".tmp-m2" / "data"
PLATE_VAL_ARTISTS = {
    "Quzhouliulian",
    "Zotyefan",
    "User3204",
    "JamesYoung8167",
    "Evnerd",
    "H4 boxer",
    "Zoerides",
    "Anonymousfox36",
}
VEHICLE_VAL_ARTISTS = {
    "OregonDOT",
    "frankh",
    "JCT600",
    "Au Kirk",
    "Kevin Krejci",
    "Matt From London",
    "JohnSeb",
    "AskDaveTaylor",
}
LICENSES = {"CC0", "CC BY-SA 4.0", "by", "by-sa", "cc0", "pdm"}


def complete_sources(rows: list[dict]) -> list[dict]:
    return [
        r
        for r in rows
        if r.get("source_page", "").startswith("https://")
        and r.get("license") in LICENSES
        and r.get("artist")
    ]


def group_split(rows: list[dict], val_artists: set[str]) -> dict[str, str]:
    return {r["file"]: "val" if r["artist"] in val_artists else "train" for r in rows}


def yolo_box(box: list[float], width: float, height: float) -> list[float]:
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError(f"Invalid box: {box}, image {width}x{height}")
    return [
        (x1 + x2) / (2 * width),
        (y1 + y2) / (2 * height),
        (x2 - x1) / width,
        (y2 - y1) / height,
    ]


def reviewed_plate_meta(meta: dict, review: dict) -> dict:
    return {
        name: {**item, **review["corrections"].get(name, {})}
        for name, item in meta.items()
        if name not in review["exclude"]
    }


def build(kind: str) -> dict:
    from PIL import Image

    if kind == "plate":
        base = ROOT / "algo/dataset_web"
        with (base / "licenses.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = complete_sources(list(csv.DictReader(f)))
        meta = json.loads((base / "meta.json").read_text(encoding="utf-8"))
        review = json.loads(
            (ROOT / "algo/dataset_plate_web/review.json").read_text(encoding="utf-8")
        )
        meta = reviewed_plate_meta(meta, review)
        rows = [r for r in rows if r["file"] in meta]
        split = group_split(rows, PLATE_VAL_ARTISTS)
    else:
        base = ROOT / "algo/dataset_charging_photos"
        with (base / "manifest.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = [{**r, "artist": r["creator"]} for r in csv.DictReader(f)]
        annotation_record = json.loads(
            (ROOT / "algo/dataset_vehicle_web/annotations.json").read_text(encoding="utf-8")
        )
        annotations = annotation_record["boxes"]
        rows = [r for r in complete_sources(rows) if r["file"] in annotations]
        split = group_split(rows, VEHICLE_VAL_ARTISTS)
    target = BUILD / kind
    if target.exists():
        if target.resolve().parent != BUILD.resolve() or kind not in {"plate", "vehicle"}:
            raise ValueError("Refusing to remove an unexpected dataset path")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    output_meta = {}
    manifest = []
    seen = set()
    for r in rows:
        name = r["file"]
        src = (
            base / "images" / meta[name]["split"] / name
            if kind == "plate"
            else base / "images" / name
        )
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        if digest in seen:
            raise ValueError(f"Duplicate image: {name}")
        seen.add(digest)
        with Image.open(src) as image:
            width, height = image.size
        boxes = (
            [meta[name]["bbox_plate"]]
            if kind == "plate"
            else [
                [b[0] * width, b[1] * height, b[2] * width, b[3] * height]
                for b in annotations[name]
            ]
        )
        labels = [yolo_box(b, width, height) for b in boxes]
        for folder in ("images", "labels"):
            (target / folder / split[name]).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target / "images" / split[name] / name)
        (target / "labels" / split[name] / Path(name).with_suffix(".txt")).write_text(
            "".join("0 " + " ".join(f"{v:.8f}" for v in b) + "\n" for b in labels), encoding="utf-8"
        )
        item = {
            **r,
            "split": split[name],
            "sha256": digest,
            "image": src.relative_to(ROOT).as_posix(),
            "boxes_xyxy": boxes,
            "width": width,
            "height": height,
        }
        if kind == "plate":
            item.update(plate=meta[name]["plate"], vtype=meta[name]["vtype"])
            output_meta[name] = {**meta[name], "split": split[name]}
        else:
            item["ignored_boxes_xyxy"] = [
                [b[0] * width, b[1] * height, b[2] * width, b[3] * height]
                for b in annotation_record.get("ignored_small_vehicles", {}).get(name, [])
            ]
        manifest.append(item)
    (target / "data.yaml").write_text(
        f"path: {json.dumps(target.as_posix(), ensure_ascii=False)}\ntrain: images/train\nval: images/val\nnames:\n  0: {kind}\n",
        encoding="utf-8",
    )
    (target / "meta.json").write_text(
        json.dumps(output_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    record = ROOT / f"algo/dataset_{kind}_web/manifest.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "kind": kind,
        "n": len(rows),
        "train": sum(v == "train" for v in split.values()),
        "val": sum(v == "val" for v in split.values()),
        "boxes": sum(len(r["boxes_xyxy"]) for r in manifest),
    }


if __name__ == "__main__":
    for kind in ("vehicle", "plate"):
        print(build(kind))
