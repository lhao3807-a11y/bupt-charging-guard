"""充电桩列表的测试（契约 v1.6 §6.7，第 3 页 / PLAN 任务 5.7 的 C1）。

覆盖点：
- 字段 = `charging_pile` 全字段，列名口径按 §3.5 的 P3
- 排序按 `pile_id` 升序（刷新不跳动）
- **`summary` 是筛选后的计数**（本接口最容易写错的一处）
- `status` 精确匹配：空串视为不筛选，拼错 → 422
- `pile_id` 模糊匹配且忽略大小写
- 分页 / `total` 随筛选变化 / 空结果
"""

from __future__ import annotations

from datetime import datetime

from app import models as m

# 种子桩（models.SEED_PILES）共 4 个：空闲 2 / 充电中 1 / 已充满 1
SEED_PILE_COUNT = 4
PILE_FIELDS = {"pile_id", "status", "bound_plate", "start_time", "end_time"}


def _get(client, **params):
    resp = client.get("/api/piles", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_list_returns_seed_piles(client):
    body = _get(client)
    assert body["total"] == SEED_PILE_COUNT
    assert len(body["items"]) == SEED_PILE_COUNT
    assert body["page"] == 1 and body["size"] == 20
    assert set(body["items"][0]) == PILE_FIELDS


def test_items_are_ordered_by_pile_id_asc(client):
    ids = [item["pile_id"] for item in _get(client)["items"]]
    assert ids == sorted(ids)


def test_summary_counts_all_statuses(client):
    """口径 2：summary 给出三个状态计数 + total。"""
    summary = _get(client)["summary"]
    assert summary == {"空闲": 2, "充电中": 1, "已充满": 1, "total": SEED_PILE_COUNT}


def test_summary_reflects_filter_not_whole_table(client):
    """**最易写错的一处**：筛了「空闲」，总览卡就该只剩空闲，否则前端会显示错觉数字。"""
    body = _get(client, status="空闲")
    assert body["total"] == 2
    assert body["summary"] == {"空闲": 2, "充电中": 0, "已充满": 0, "total": 2}


def test_filter_status_is_exact(client):
    body = _get(client, status="已充满")
    assert body["total"] == 1
    assert body["items"][0]["pile_id"] == "PILE-002"
    assert body["items"][0]["status"] == "已充满"


def test_filter_status_empty_string_means_no_filter(client):
    """前端「全部」发空串：不能当成非法值（与 §6.4 / §6.6 同款口径）。"""
    assert _get(client, status="")["total"] == SEED_PILE_COUNT
    assert _get(client, status="   ")["total"] == SEED_PILE_COUNT


def test_filter_status_invalid_is_422(client):
    assert client.get("/api/piles", params={"status": "损坏"}).status_code == 422


def test_filter_pile_id_is_fuzzy_and_case_insensitive(client):
    assert _get(client, pile_id="PILE")["total"] == SEED_PILE_COUNT
    assert _get(client, pile_id="pile-001")["total"] == 1  # 小写也命中
    assert _get(client, pile_id="001")["total"] == 1


def test_filters_combine_with_and(client):
    # PILE-003 / PILE-004 都是空闲 → 再加 pile_id 模糊筛出一个
    assert _get(client, status="空闲", pile_id="003")["total"] == 1
    # 空闲 + 不存在的桩 → 0
    assert _get(client, status="空闲", pile_id="999")["total"] == 0


def test_pagination_and_total(client):
    body = _get(client, page=2, size=2)
    assert body["total"] == SEED_PILE_COUNT  # total 仍是筛选后总数，不受分页影响
    assert body["page"] == 2 and body["size"] == 2
    assert [item["pile_id"] for item in body["items"]] == ["PILE-003", "PILE-004"]


def test_empty_result_has_zeroed_summary(client):
    body = _get(client, pile_id="不存在的桩")
    assert body["total"] == 0
    assert body["items"] == []
    assert body["summary"] == {"空闲": 0, "充电中": 0, "已充满": 0, "total": 0}


def test_idle_pile_has_null_end_time(db_session, client):
    """空闲桩：未充满 → `end_time` 为 null（不能写成空串或 1970）。"""
    db_session.add(m.ChargingPile(pile_id="PILE-900", status=m.PILE_IDLE, bound_plate=None))
    db_session.commit()
    body = _get(client, pile_id="PILE-900")
    assert body["total"] == 1
    item = body["items"][0]
    assert item["bound_plate"] is None
    assert item["start_time"] is None
    assert item["end_time"] is None


def test_charging_pile_times_are_returned(client):
    """充电中桩：有到达时间，无充满时间。"""
    item = _get(client, pile_id="PILE-001")["items"][0]
    assert item["status"] == "充电中"
    assert item["bound_plate"] == "京AD12345"
    # ISO 8601 字符串能被解析回来（前端 new Date(...) 直接可用）
    assert datetime.fromisoformat(item["start_time"]).year == 2026
    assert item["end_time"] is None
