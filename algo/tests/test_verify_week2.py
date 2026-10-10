from algo.tools.verify_week2 import detection_counts, manifest_digest, recognition_metrics


def test_manifest_digest_ignores_line_endings_and_key_order(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_bytes(b'{"a":1,"b":2}\n')
    b.write_bytes(b'{\r\n "b": 2, "a": 1\r\n}\r\n')
    assert manifest_digest(a) == manifest_digest(b)
    b.write_bytes(b'{"a":3,"b":2}')
    assert manifest_digest(a) != manifest_digest(b)


def test_duplicate_detections_do_not_match_the_same_ground_truth_twice():
    boxes = [[10, 10, 30, 30], [10, 10, 30, 30], [80, 80, 90, 90]]
    assert detection_counts(boxes, [[10, 10, 30, 30], [40, 40, 60, 60]]) == {
        "tp": 1,
        "fp": 2,
        "fn": 1,
        "ignored": 0,
    }


def test_out_of_scope_small_vehicle_is_ignored_in_operating_metrics():
    assert detection_counts([[80, 80, 90, 90]], [], [[80, 80, 90, 90]]) == {
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "ignored": 1,
    }


def test_metrics_count_detection_and_ocr_failures_in_full_denominator():
    rows = [
        {
            "gt_plate": "京A12345",
            "gt_vtype": "燃油",
            "result": {"plate": "京A12345", "vtype": "燃油"},
            "iou": 0.9,
        },
        {
            "gt_plate": "京AD12345",
            "gt_vtype": "新能源",
            "result": {"plate": "", "vtype": "新能源"},
            "iou": 0.8,
        },
        {"gt_plate": "粤A12345", "gt_vtype": "燃油", "result": None, "iou": 0},
    ]
    metrics = recognition_metrics(rows)
    assert metrics["images"] == 3
    assert metrics["detected"] == 2
    assert metrics["ocr_exact_detected"] == 0.5
    assert metrics["ocr_exact_all"] == 1 / 3
    assert metrics["vtype_correct_all"] == 2 / 3
    assert metrics["plate_and_vtype_correct_all"] == 1 / 3


def test_no_detections_or_empty_dataset_are_reported_as_zero():
    assert recognition_metrics([])["ocr_exact_all"] == 0
