"""Validate the remote branch snapshot integrated on 2026-10-13."""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
INCLUDED = {
    "api-week2": "dae5995d9cadbdb6b073d60895423d1d940f5370",
    "db-schema": "6f75af67d5673d346d22b447a8ae2f352795a3b6",
    "rule-engine": "24ee309d6ac2692975637066d2de191c0f63e12c",
    "ui-design": "6841440b6beac743428e9383be8480b3813558f2",
    "ui-week1": "22f3da5bb9a01a8d6f6dd46677c56c9b177f4311",
    "ui-week2": "4e36f3b004ec920121d16ce8b2a5bb8a7ddf627c",
    "ui-week2-review": "07fa9d9d9809e279328b7cd9361610b53ee73251",
}


@pytest.mark.parametrize("branch,commit", INCLUDED.items())
def test_selected_branch_snapshot_is_in_main_history(branch, commit):
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, f"Missing branch {branch}: {result.stderr}"
