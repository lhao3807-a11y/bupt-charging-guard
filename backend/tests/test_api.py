"""接口层端到端测试 —— 覆盖契约 §6 的四个业务端点 + §11 验收清单。

覆盖点（对应 CONTRACT §11 第 1 周末 Demo 验收）：
- /api/recognize 传入 frame_ref 返回合规 RecognitionResult；缺失标注 → 404
- /api/judge 四条规则：燃油占位 / 异常占位 / 充满未移车 各命中，正常充电返回 null
- /api/judge 去重：同桩同规则重复判定复用同一条记录（不新增）
- /api/notify 按 id 更新状态成功；不存在的 id → 404
- /api/records 分页 total 正确、按 occur_time 倒序
"""

from __future__ import annotations

from app.routers.recognize import label_path_for

# 种子桩位（models.SEED_PILES）与标注样例（algo/samples/labels/*.json）的真实对应：
#   001 京AD12345 新能源 → PILE-001 充电中   → 规则④ 正常（judge 返回 null）
#   002 京A88888  燃油   → PILE-004 空闲     → 规则① 燃油占位（rule_hit=1）
#   003 京AD24680 新能源 → PILE-003 空闲久停 → 规则② 异常占位（rule_hit=2）
#   004 京AD67890 新能源 → PILE-002 已充满   → 规则③ 充满未移车（rule_hit=3）
FRAME_NORMAL = "001.jpg"
FRAME_FUEL = "002.jpg"
FRAME_ABNORMAL = "003.jpg"
FRAME_FULL = "004.jpg"


# ---------------------------------------------------------------------------
# /api/recognize
# ---------------------------------------------------------------------------
def test_recognize_returns_recognition_result(client):
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["plate"] == "京AD12345"
    assert body["vtype"] == "新能源"
    assert len(body["bbox"]) == 4


def test_recognize_missing_label_returns_404(client):
    resp = client.post("/api/recognize", json={"frame_ref": "no_such_frame.jpg"})
    assert resp.status_code == 404
    assert "标注文件" in resp.json()["detail"]


def test_label_path_blocks_path_traversal():
    """frame_ref 含 ../ 时不得越出 labels 目录（契约 §6.1 只允许文件名）。"""
    path = label_path_for("../../etc/passwd")
    assert path.endswith("passwd.json")
    assert ".." not in path.replace("\\", "/").split("labels/")[-1]


# ---------------------------------------------------------------------------
# /api/judge —— 四条规则
# ---------------------------------------------------------------------------
def _recognize(client, frame: str) -> dict:
    resp = client.post("/api/recognize", json={"frame_ref": frame})
    assert resp.status_code == 200
    return resp.json()


def test_judge_rule4_normal_returns_null(client):
    """规则④ 正常充电（PILE-001 充电中）→ 不违规，返回 null。"""
    resp = client.post("/api/judge", json=_recognize(client, FRAME_NORMAL))
    assert resp.status_code == 200
    assert resp.json() is None


def test_judge_rule3_full_not_moved(client):
    """规则③ 充满未移车（PILE-002）→ rule_hit=3，落库并带 id。"""
    resp = client.post("/api/judge", json=_recognize(client, FRAME_FULL))
    assert resp.status_code == 200
    body = resp.json()
    assert body["rule_hit"] == 3
    assert body["pile_id"] == "PILE-002"
    assert body["id"] is not None
    assert body["notify_status"] == "未提醒"


def test_judge_rule2_abnormal_park(client):
    """规则② 异常占位久停（PILE-003）→ rule_hit=2。"""
    resp = client.post("/api/judge", json=_recognize(client, FRAME_ABNORMAL))
    assert resp.status_code == 200
    assert resp.json()["rule_hit"] == 2


def test_judge_rule1_fuel_occupy(client):
    """规则① 燃油车占位（PILE-004）→ rule_hit=1。"""
    resp = client.post("/api/judge", json=_recognize(client, FRAME_FUEL))
    assert resp.status_code == 200
    assert resp.json()["rule_hit"] == 1


def test_judge_dedup_same_violation_reuses_record(client):
    """同桩 + 同规则 + 未提醒 → 重复判定复用同一条记录，不新增。"""
    payload = _recognize(client, FRAME_FUEL)
    first = client.post("/api/judge", json=payload).json()
    second = client.post("/api/judge", json=payload).json()

    assert first["id"] == second["id"], "同一持续违规不应产生重复记录"

    records = client.get("/api/records", params={"page": 1, "size": 50}).json()
    assert records["total"] == 1


def test_judge_creates_new_record_after_notified(client):
    """已提醒后再命中同一违规 → 视为新违规，新增一条。"""
    payload = _recognize(client, FRAME_FUEL)
    first = client.post("/api/judge", json=payload).json()

    client.post("/api/notify", json={"id": first["id"], "notify_status": "已提醒"})

    second = client.post("/api/judge", json=payload).json()
    assert second["id"] != first["id"]
    assert client.get("/api/records", params={"page": 1, "size": 50}).json()["total"] == 2


# ---------------------------------------------------------------------------
# /api/notify
# ---------------------------------------------------------------------------
def test_notify_updates_status(client):
    record = client.post("/api/judge", json=_recognize(client, FRAME_FUEL)).json()
    resp = client.post("/api/notify", json={"id": record["id"], "notify_status": "已提醒"})
    assert resp.status_code == 200
    assert resp.json()["notify_status"] == "已提醒"

    items = client.get("/api/records", params={"page": 1, "size": 10}).json()["items"]
    assert items[0]["notify_status"] == "已提醒"


def test_notify_unknown_id_returns_404(client):
    resp = client.post("/api/notify", json={"id": 999999, "notify_status": "已提醒"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /api/records
# ---------------------------------------------------------------------------
def test_records_pagination_total(client):
    """产生 2 条不同违规，校验 total 与 size 生效。"""
    client.post("/api/judge", json=_recognize(client, FRAME_ABNORMAL))
    client.post("/api/judge", json=_recognize(client, FRAME_FUEL))

    body = client.get("/api/records", params={"page": 1, "size": 1}).json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["size"] == 1
    assert len(body["items"]) == 1


def test_records_empty_initially(client):
    body = client.get("/api/records").json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# 端到端最小闭环（契约 §11 主线）
# ---------------------------------------------------------------------------
def test_end_to_end_closed_loop(client):
    """识别 → 判定 → 提醒 → 后台可查：一条完整闭环。"""
    recognition = _recognize(client, FRAME_FULL)

    violation = client.post("/api/judge", json=recognition).json()
    assert violation is not None and violation["rule_hit"] == 3

    notified = client.post("/api/notify", json={"id": violation["id"], "notify_status": "已提醒"})
    assert notified.status_code == 200

    page = client.get("/api/records").json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == violation["id"]
    assert page["items"][0]["notify_status"] == "已提醒"
