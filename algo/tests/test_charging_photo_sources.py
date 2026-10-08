from scripts.collect_charging_photos import eligible_candidate


def test_only_well_sourced_large_reusable_photos_are_candidates():
    valid = {
        "title": "EV at a charging station",
        "creator": "Photographer",
        "license": "by-sa",
        "license_version": "2.0",
        "foreign_landing_url": "https://www.flickr.com/photos/example/123",
        "url": "https://live.staticflickr.com/example.jpg",
        "width": 1200,
        "height": 800,
    }
    assert eligible_candidate(valid)
    for update in (
        {"license": "by-nc"},
        {"license": "by-nd"},
        {"foreign_landing_url": ""},
        {"creator": ""},
        {"width": 320},
    ):
        assert not eligible_candidate({**valid, **update})
