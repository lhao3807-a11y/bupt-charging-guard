import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(".")
PACK = ROOT / "algo" / "dataset_scene_mvp"
EXPECTED_SCENES = {
    "fuel_occupy",
    "ev_charging",
    "ev_idle_long",
    "ev_full_not_moved",
}
ALLOWED_LICENSES = {"by", "by-sa", "cc0", "pdm"}


def test_mvp_scenarios_are_traceable_and_not_training_labels():
    manifest = json.loads((PACK / "scene_cases.json").read_text(encoding="utf-8"))
    with (PACK / "licenses.csv").open(encoding="utf-8-sig", newline="") as file:
        assets = {row["path"]: row for row in csv.DictReader(file)}

    cases = manifest["cases"]
    assert manifest["scenario_case_count"] == len(cases) == 120
    assert manifest["asset_count"] == manifest["unique_image_count"] == len(assets) == 109
    counts = Counter(case["scene_category"] for case in cases)
    assert set(counts) == EXPECTED_SCENES
    assert counts == {scene: 30 for scene in EXPECTED_SCENES}

    for scene in EXPECTED_SCENES:
        paths = [case["image_path"] for case in cases if case["scene_category"] == scene]
        assert len(set(paths)) == 30

    for case in cases:
        assert case["status_origin"] == "synthetic_demo"
        assert case["training_eligible"] is False
        assert case["campus_verified"] is False
        asset = assets[case["image_path"]]
        assert asset["license"] in ALLOWED_LICENSES
        assert asset["creator"]
        assert asset["source_page"].startswith("https://")
        assert asset["license_url"].startswith("https://")
        image = ROOT / case["image_path"]
        assert image.is_file()
        assert hashlib.sha256(image.read_bytes()).hexdigest() == asset["sha256"]

    for asset in assets.values():
        image = ROOT / asset["path"]
        assert image.is_file()
        assert hashlib.sha256(image.read_bytes()).hexdigest() == asset["sha256"]
