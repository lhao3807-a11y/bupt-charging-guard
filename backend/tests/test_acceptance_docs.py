"""Keep the retained acceptance checklist complete and navigable."""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"


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
