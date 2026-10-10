from pathlib import Path

import pytest

from algo.train.detect import VEHICLE_WEIGHTS, detect_vehicles


@pytest.mark.skipif(
    not Path(VEHICLE_WEIGHTS).is_file(), reason="Local real vehicle weights not trained"
)
def test_real_charging_photo_outputs_vehicle_bbox():
    pytest.importorskip("ultralytics")
    root = Path(__file__).resolve().parents[2]
    boxes = detect_vehicles(str(root / "algo/dataset_charging_photos/images/charging_0017.jpg"))
    assert boxes
    for box in boxes:
        assert box["name"] == "vehicle"
        assert 0.4 <= box["conf"] <= 1
        assert box["bbox_xywh"][2] > 0 and box["bbox_xywh"][3] > 0
