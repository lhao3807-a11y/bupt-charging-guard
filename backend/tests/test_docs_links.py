"""Keep links between retained project documents usable after cleanup."""

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[2] / "docs"


@pytest.mark.parametrize("path", sorted(DOCS.glob("*.md")), ids=lambda path: path.name)
def test_top_level_document_local_links_resolve(path: Path):
    text = path.read_text(encoding="utf-8")

    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" in target or target.startswith(("#", "mailto:")):
            continue
        local_path = target.split("#", 1)[0]
        if local_path:
            assert (path.parent / local_path).is_file(), f"{path.name}: {target}"


@pytest.mark.parametrize(
    "name",
    [
        "CONTRACT.md",
        "PLAN_4WEEKS.md",
        "WEEK3_PLAN.md",
        "WEEK2_ACCEPTANCE.md",
        "WEEK2_WU_REMAINING.md",
    ],
)
def test_current_project_documents_are_retained(name: str):
    assert (DOCS / name).is_file()
