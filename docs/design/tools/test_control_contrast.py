from pathlib import Path
import re

from docs.design.tools import check_tokens


def test_control_boundaries_meet_non_text_contrast() -> None:
    tokens, duplicates = check_tokens.parse_tokens(check_tokens.TOKENS_CSS)
    assert not duplicates
    for name in ("--border-control", "--border-control-hover"):
        color = check_tokens.as_hex(tokens, name)
        assert color is not None
        assert check_tokens.contrast(color, "#FFFFFF") >= 3.0


def test_control_border_is_scoped_to_form_controls() -> None:
    css = (Path(check_tokens.REPO_ROOT) / "frontend/src/styles/global.css").read_text(
        encoding="utf-8"
    )
    controls = re.search(
        r"\.el-input__wrapper,\s*\.el-select__wrapper\s*\{([^}]*)\}", css
    )
    assert controls is not None
    assert "--el-input-border-color: var(--border-control)" in controls.group(1)
    assert "--el-border-color: var(--border-control)" in controls.group(1)
    assert "--el-input-hover-border-color: var(--border-control-hover)" in controls.group(1)
    assert "--el-border-color-hover: var(--border-control-hover)" in controls.group(1)

    library_css = (Path(check_tokens.REPO_ROOT) / "frontend/node_modules/element-plus/dist/index.css").read_text(
        encoding="utf-8"
    )
    assert ".el-input__wrapper:hover{box-shadow:0 0 0 1px var(--el-input-hover-border-color) inset}" in library_css
    assert ".el-select__wrapper.is-hovering:not(.is-focused){box-shadow:0 0 0 1px var(--el-border-color-hover) inset}" in library_css
    assert "--el-table-border-color: var(--border-light)" in css
