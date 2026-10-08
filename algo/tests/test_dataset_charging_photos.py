import csv
import hashlib
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "dataset_charging_photos"


def test_curated_open_images_have_traceable_sources_and_unique_content():
    with (DATA / "manifest.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) >= 120
    assert len({row["source_page"] for row in rows}) == len(rows)
    assert len({row["sha256"] for row in rows}) == len(rows)
    for row in rows:
        assert row["license"] in {"by", "by-sa", "cc0", "pdm"}
        assert row["creator"] and row["source_page"].startswith("https://")
        assert row["visual_review"] == "manual_contact_sheet"
        assert row["status_evidence"] == "none"
        image = DATA / "images" / row["file"]
        assert image.is_file()
        assert hashlib.sha256(image.read_bytes()).hexdigest() == row["sha256"]
