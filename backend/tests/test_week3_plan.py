"""Check that week-three assignments and acceptance references stay actionable."""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"


def test_week3_acceptance_references_assigned_tasks_without_orphans():
    text = (DOCS / "WEEK3_PLAN.md").read_text(encoding="utf-8")
    tasks = re.findall(r"^#### ([LTW]\d+)\s", text, re.MULTILINE)
    assert tasks, "The plan must contain individually assigned tasks"
    assert len(tasks) == len(set(tasks)), "Task IDs must be unique"

    rows = re.findall(r"^\| (A\d+) \| (.+) \| (.+) \| (.+) \|$", text, re.MULTILINE)
    assert rows, "The plan must have an acceptance matrix"
    ids = [row[0] for row in rows]
    assert ids == [f"A{index:02d}" for index in range(1, len(rows) + 1)]
    covered = set()
    for acceptance_id, criterion, owner, references in rows:
        assert criterion.strip(), acceptance_id
        assert owner in {"吕浩", "汤瑾睿", "吴和庆"}, acceptance_id
        linked = set(re.findall(r"\b[LTW]\d+\b", references))
        assert linked, f"{acceptance_id} needs an implementation owner task"
        assert linked <= set(tasks), f"{acceptance_id} references unknown tasks"
        covered.update(linked)
    assert covered == set(tasks), f"Tasks without acceptance coverage: {set(tasks) - covered}"


def test_four_week_plan_links_to_week3_details():
    text = (DOCS / "PLAN_4WEEKS.md").read_text(encoding="utf-8")
    targets = re.findall(r"\[[^]]+\]\(([^)]+)\)", text)
    assert "WEEK3_PLAN.md" in targets
    assert (DOCS / "WEEK3_PLAN.md").is_file()
