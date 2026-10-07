import ast
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest


def declared_pages() -> list[tuple[str, str, str, str]]:
    script = Path(__file__).with_name("demo_screenshots.py")
    tree = ast.parse(script.read_text(encoding="utf-8"))
    pages = next(
        node for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "PAGES"
    )
    return ast.literal_eval(pages.value)


def test_all_week_two_captures_use_current_routes_and_honest_labels() -> None:
    pages = {name: (route, caption, title) for name, route, caption, title in declared_pages()}
    assert [pages[f"p{i}-{name}"][0] for i, name in enumerate(
        ("vehicle", "records", "piles", "statistics", "config", "preview"), start=1
    )] == ["/vehicle", "/records", "/piles", "/statistics", "/config", "/preview"]
    for key in ("p3-piles", "p4-statistics", "p5-config"):
        assert "演示数据" in pages[key][1]
        assert "开发夹具" not in " ".join(pages[key])
    assert "样例静态帧" in pages["p6-preview"][1]


def test_failed_capture_preserves_previous_png(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The screenshot utility uses Pillow only for framing; this test exercises
    # capture without requiring that optional package in the backend venv.
    pil = types.ModuleType("PIL")
    for name in ("Image", "ImageDraw", "ImageFilter", "ImageFont"):
        setattr(pil, name, types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "PIL", pil)
    spec = importlib.util.spec_from_file_location(
        "capture_under_test", Path(__file__).with_name("demo_screenshots.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "RAW_DIR", tmp_path)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stderr="failed"),
    )
    previous = tmp_path / "login.png"
    previous.write_bytes(b"previous capture")
    with pytest.raises(SystemExit, match="拍摄失败"):
        module.shoot("browser", "login", "/login", tmp_path / "profile")
    assert previous.read_bytes() == b"previous capture"
    assert not list(tmp_path.glob("*.fresh.png"))
