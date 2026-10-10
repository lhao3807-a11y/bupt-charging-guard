import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("kind,expected", [("vehicle", 97), ("plate", 93)])
def test_sourced_manifests_are_disjoint_and_match_files(kind, expected):
    rows = json.loads((ROOT / f"algo/dataset_{kind}_web/manifest.json").read_text(encoding="utf-8"))
    assert len(rows) == expected
    assert len({r["sha256"] for r in rows}) == len(rows)
    train_artists = {r["artist"] for r in rows if r["split"] == "train"}
    val_artists = {r["artist"] for r in rows if r["split"] == "val"}
    assert train_artists and val_artists and not train_artists & val_artists
    if kind == "plate":
        assert not {r["plate"] for r in rows if r["split"] == "train"} & {
            r["plate"] for r in rows if r["split"] == "val"
        }
        assert next(r for r in rows if r["file"] == "web_0857.jpg")["plate"] == "闽CG210M"
    for row in rows:
        assert row["source_page"].startswith("https://") and row["artist"] and row["license"]
        assert hashlib.sha256((ROOT / row["image"]).read_bytes()).hexdigest() == row["sha256"]
        for x1, y1, x2, y2 in row["boxes_xyxy"]:
            assert 0 <= x1 < x2 <= row["width"]
            assert 0 <= y1 < y2 <= row["height"]
