"""模拟器端点的测试（契约 v1.7 §6.10，第 3 页演示用）。

钉住四条口径：

1. **一次只推进一步**（连调两次第二次应无变化）—— 否则演示会跳过「充电中」
2. `at` 是**演示快进**：传了就用它当「现在」
3. 响应带 `statuses` 全量快照，前端不必二次请求
4. 已充满 → 释放沿用业务阈值 `full_timeout_min`（§7），改配置行为就变
"""

from __future__ import annotations

from datetime import datetime

from app import models as m

AT = datetime(2026, 9, 8, 10, 30, 0)


def _post(client, payload=None):
    if payload is None:
        return client.post("/api/piles/simulate")
    return client.post("/api/piles/simulate", json=payload)


def test_simulate_returns_200_and_full_shape(client):
    resp = _post(client, {"at": AT.isoformat()})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"advanced_at", "changed_count", "changes", "statuses"}
    assert body["changed_count"] == len(body["changes"])
    for change in body["changes"]:
        assert set(change) == {"pile_id", "from_status", "to_status", "reason"}


def test_simulate_fast_forward_with_at(client):
    body = _post(client, {"at": AT.isoformat()}).json()
    assert datetime.fromisoformat(body["advanced_at"]) == AT
    # 种子 4 桩在 10:30 全部满足推进条件：
    # 001 充电中(09:50)→已充满、002 已充满(09:20)→释放、003/004 空闲→充电中
    assert body["changed_count"] == 4
    assert {c["pile_id"] for c in body["changes"]} == {
        "PILE-001",
        "PILE-002",
        "PILE-003",
        "PILE-004",
    }


def test_simulate_advances_only_one_step(client):
    """口径 1：一次一档。连调两次，第二次应当没有变化。"""
    first = _post(client, {"at": AT.isoformat()}).json()
    assert first["changed_count"] == 4
    second = _post(client, {"at": AT.isoformat()}).json()
    assert second["changed_count"] == 0


def test_simulate_statuses_snapshot_matches_db(client, db_session):
    body = _post(client, {"at": AT.isoformat()}).json()
    assert body["statuses"] == {
        row.pile_id: row.status for row in db_session.query(m.ChargingPile).all()
    }
    assert body["statuses"]["PILE-001"] == m.PILE_FULL
    assert body["statuses"]["PILE-002"] == m.PILE_IDLE


def test_simulate_without_at_uses_server_clock(client):
    before = datetime.now()
    body = _post(client).json()
    after = datetime.now()
    moment = datetime.fromisoformat(body["advanced_at"])
    assert before <= moment <= after


def test_simulate_invalid_at_is_422(client):
    assert _post(client, {"at": "不是时间"}).status_code == 422


def test_simulate_uses_config_threshold(client, db_session):
    """口径 2：释放阈值来自 system_config（契约 §7），不是写死的 30。"""
    row = db_session.get(m.SystemConfig, "full_timeout_min")
    row.value = "600"  # 放宽到 10 小时 → PILE-002 不该释放
    db_session.commit()

    body = _post(client, {"at": AT.isoformat()}).json()
    assert body["statuses"]["PILE-002"] == m.PILE_FULL
    assert not any(c["pile_id"] == "PILE-002" for c in body["changes"])


def test_simulate_change_reason_is_human_readable(client):
    body = _post(client, {"at": AT.isoformat()}).json()
    assert body["changes"], "本次应当有变化"
    assert all(change["reason"] for change in body["changes"])
    assert all(change["from_status"] != change["to_status"] for change in body["changes"])
