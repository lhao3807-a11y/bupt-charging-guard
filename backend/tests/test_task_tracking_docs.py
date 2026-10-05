"""Keep week-two tracking and acceptance documents complete and navigable."""

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


def test_acceptance_document_lists_all_fourteen_plan_checks_once():
    path = DOCS / "WEEK2_ACCEPTANCE.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    check_rows = re.findall(r"^\| (\d{1,2}) \|", text, re.MULTILINE)

    assert len(check_rows) == 14
    assert set(check_rows) == {str(number) for number in range(1, 15)}


def test_acceptance_document_local_links_resolve():
    path = DOCS / "WEEK2_ACCEPTANCE.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")

    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" in target:
            continue
        assert (path.parent / target.split("#", 1)[0]).is_file(), target
