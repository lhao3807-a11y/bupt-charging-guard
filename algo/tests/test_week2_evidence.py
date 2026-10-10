import hashlib
import json
from pathlib import Path

from algo.tools.verify_week2 import manifest_digest, recognition_metrics

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs/acceptance/algo/week2-web"


def test_saved_reports_reference_current_manifests_and_local_weights():
    for kind in ("vehicle", "plate"):
        report = json.loads((REPORT / f"{kind}-detection.json").read_text(encoding="utf-8"))
        manifest = ROOT / f"algo/dataset_{kind}_web/manifest.json"
        assert report["manifest_sha256"] == manifest_digest(manifest)
        rows = json.loads(manifest.read_text(encoding="utf-8"))
        assert report["val_images"] == sum(r["split"] == "val" for r in rows)
        weights = ROOT / report["weights"]
        if weights.is_file():
            assert report["weights_sha256"] == hashlib.sha256(weights.read_bytes()).hexdigest()
    report = json.loads((REPORT / "recognition.json").read_text(encoding="utf-8"))
    assert report["summary"] == recognition_metrics(report["rows"])
    assert report["manifest_sha256"] == manifest_digest(
        ROOT / "algo/dataset_plate_web/manifest.json"
    )
    assert (
        report["weights_sha256"]
        == json.loads((REPORT / "plate-detection.json").read_text(encoding="utf-8"))[
            "weights_sha256"
        ]
    )
