"""Verify the screenshot seed script's API calls without changing a database."""

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "docs" / "design" / "tools" / "demo_seed.py"


def load_script():
    spec = importlib.util.spec_from_file_location("demo_seed", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_with_transport(monkeypatch, module, handler):
    original_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        module.httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs)
    )
    monkeypatch.setattr(sys, "argv", ["demo_seed.py"])
    return module.main()


def test_demo_seed_creates_nine_records_with_all_three_notification_states(monkeypatch, capsys):
    module = load_script()
    records = []
    paths = []

    def handle(request):
        paths.append(request.url.path)
        if request.url.path == "/api/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/api/judge":
            payload = json.loads(request.content)
            rule = {"京A88888": 1, "京AD24680": 2, "京AD67890": 3}[payload["plate"]]
            record = {
                "id": len(records) + 1,
                "plate": payload["plate"],
                "pile_id": f"PILE-00{rule}",
                "occur_time": payload["frame_time"],
                "rule_hit": rule,
                "notify_status": "未提醒",
            }
            records.append(record)
            return httpx.Response(200, json=record)
        if request.url.path == "/api/notify":
            payload = json.loads(request.content)
            records[payload["id"] - 1]["notify_status"] = payload["notify_status"]
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/api/records":
            return httpx.Response(200, json={"total": len(records), "items": records})
        return httpx.Response(404)

    assert run_with_transport(monkeypatch, module, handle) == 0
    assert paths.count("/api/judge") == 9
    assert paths.count("/api/notify") == 7
    assert {item["rule_hit"] for item in records} == {1, 2, 3}
    assert Counter(item["notify_status"] for item in records) == {
        "未提醒": 2,
        "已提醒": 6,
        "失败": 1,
    }
    assert "records 总数：9" in capsys.readouterr().out


def test_demo_seed_stops_when_judge_fails(monkeypatch):
    module = load_script()
    paths = []

    def handle(request):
        paths.append(request.url.path)
        if request.url.path == "/api/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(503, text="unavailable")

    with pytest.raises(SystemExit, match="judge 失败 503"):
        run_with_transport(monkeypatch, module, handle)
    assert paths == ["/api/health", "/api/judge"]
