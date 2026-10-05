"""Keep the three week-two task trackers complete and locally navigable."""

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[2] / "docs"
TRACKERS = {
    "LUHAO": {f"4.{number}" for number in range(1, 9)},
    "TANG": {f"5.{number}" for number in range(1, 10)},
    "WU": {f"6.{number}" for number in range(1, 15)},
}


@pytest.mark.parametrize("person,expected", TRACKERS.items())
def test_tracker_covers_each_assigned_week_two_task_once(person: str, expected: set[str]):
    text = (DOCS / f"TASK_TRACKING_{person}.md").read_text(encoding="utf-8")
    task_rows = re.findall(r"^\| ((?:4|5|6)\.\d+) (?:[^|]+)\|", text, re.MULTILINE)

    assert len(task_rows) == len(expected)
    assert set(task_rows) == expected


@pytest.mark.parametrize("person", TRACKERS)
def test_tracker_local_links_resolve(person: str):
    path = DOCS / f"TASK_TRACKING_{person}.md"
    text = path.read_text(encoding="utf-8")

    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" in target:
            continue
        assert (path.parent / target.split("#", 1)[0]).is_file(), target
