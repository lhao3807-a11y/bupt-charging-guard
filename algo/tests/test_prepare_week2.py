from algo.tools.prepare_week2 import complete_sources, group_split, reviewed_plate_meta, yolo_box


def test_manual_review_corrects_gt_and_excludes_out_of_scope_plates():
    result = reviewed_plate_meta(
        {"a": {"plate": "old"}, "b": {"plate": "police"}},
        {"corrections": {"a": {"plate": "new"}}, "exclude": {"b": "special plate"}},
    )
    assert result == {"a": {"plate": "new"}}


def test_excludes_unknown_license_and_missing_credit():
    rows = [
        {"file": "a.jpg", "source_page": "https://a", "license": "CC0", "artist": "A"},
        {"file": "b.jpg", "source_page": "", "license": "CC0", "artist": "A"},
        {"file": "c.jpg", "source_page": "https://c", "license": "unknown", "artist": "A"},
        {"file": "d.jpg", "source_page": "https://d", "license": "CC0", "artist": ""},
    ]
    assert [r["file"] for r in complete_sources(rows)] == ["a.jpg"]


def test_artist_groups_never_cross_train_val():
    rows = [
        {"file": "a", "artist": "A"},
        {"file": "b", "artist": "A"},
        {"file": "c", "artist": "B"},
    ]
    result = group_split(rows, {"A"})
    assert result == {"a": "val", "b": "val", "c": "train"}


def test_box_is_normalized_and_invalid_boxes_are_rejected():
    import pytest

    assert yolo_box([10, 20, 50, 60], 100, 100) == [0.3, 0.4, 0.4, 0.4]
    with pytest.raises(ValueError):
        yolo_box([50, 20, 10, 60], 100, 100)
    with pytest.raises(ValueError):
        yolo_box([-1, 20, 50, 60], 100, 100)


def test_rebuild_removes_stale_excluded_images(tmp_path, monkeypatch):
    import json

    import pytest

    Image = pytest.importorskip("PIL.Image")
    from algo.tools import prepare_week2 as prep

    monkeypatch.setattr(prep, "ROOT", tmp_path)
    monkeypatch.setattr(prep, "BUILD", tmp_path / "build")
    base = tmp_path / "algo/dataset_web"
    (base / "images/train").mkdir(parents=True)
    Image.new("RGB", (100, 100)).save(base / "images/train/a.jpg")
    (base / "licenses.csv").write_text(
        "file,source_page,license,artist\na.jpg,https://a,CC0,A\n", encoding="utf-8"
    )
    (base / "meta.json").write_text(
        json.dumps(
            {
                "a.jpg": {
                    "split": "train",
                    "bbox_plate": [10, 20, 50, 60],
                    "plate": "京A12345",
                    "vtype": "燃油",
                }
            }
        ),
        encoding="utf-8",
    )
    review = tmp_path / "algo/dataset_plate_web/review.json"
    review.parent.mkdir(parents=True)
    review.write_text('{"corrections":{},"exclude":{}}', encoding="utf-8")
    prep.build("plate")
    review.write_text('{"corrections":{},"exclude":{"a.jpg":"removed"}}', encoding="utf-8")
    prep.build("plate")
    assert not (prep.BUILD / "plate/images/train/a.jpg").exists()
