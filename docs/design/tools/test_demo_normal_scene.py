import json

import httpx

from docs.design.tools import demo_normal_scene as demo


def test_normal_evidence_only_claims_observed_results(monkeypatch, tmp_path):
    paths = []

    def handle(request):
        paths.append(request.url.path)
        responses = {
            "/api/piles": {
                "items": [{"pile_id": "PILE-001", "status": "充电中", "bound_plate": "京AD12345"}]
            },
            "/api/vehicles": {"items": [{"plate": "京AD12345", "vtype": "新能源"}]},
            "/api/records": {"total": 1},
            "/api/stats": {"total": 1, "by_rule": [{"rule_hit": 0, "count": 0}]},
            "/api/judge": None,
        }
        return httpx.Response(200, content=json.dumps(responses[request.url.path]))

    client = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(demo.httpx, "Client", lambda **kwargs: client)
    monkeypatch.setattr(demo, "OUT_DIR", tmp_path)
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo.sys, "argv", ["demo_normal_scene.py", "--json"])
    assert demo.main() == 0
    evidence = json.loads((tmp_path / "A04-normal-scene.json").read_text(encoding="utf-8"))
    assert evidence["all_passed"]
    assert "notify_called" not in evidence
    assert "未监测" in evidence["notify_observation"]
    assert "/api/notify" not in paths
