"""车辆信息 CRUD 的测试（契约 v1.3 §6.6）。

覆盖任务书点名的三条坑与全部状态码：
- 4 端点：`GET/POST /api/vehicles`、`PUT/DELETE /api/vehicles/{plate}`
- 状态码：`201` / `409` / `404` / `204` / `422`
- **`plate` 是主键不可改**：`VehicleUpdate` 类型上不含 `plate`，请求体里塞 `plate` 也被忽略
- **`occupation_record.plate` 无外键约束**，删车后历史违规记录**仍在**（专门一条测试）
- 列表筛选：`plate`/`owner` 模糊，`vtype` 精确，`total` 为筛选后总数
- 删除时释放关联桩的 `bound_plate`（FK 声明 SET NULL，SQLite 需显式处理）
"""

from __future__ import annotations

from datetime import datetime

import pytest
from app import models as m
from app.schemas import VehicleCreate, VehicleUpdate

# 种子车辆（models.SEED_VEHICLES）共 4 辆：3 新能源 + 1 燃油
SEED_COUNT = 4
SEED_PLATE = "京AD12345"
SEED_FUEL_PLATE = "京A88888"


def _get(client, **params):
    resp = client.get("/api/vehicles", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Schema 层：主键从类型上就改不了
# ---------------------------------------------------------------------------
def test_update_schema_has_no_plate_or_created_at():
    """口径 1：`VehicleUpdate` 不含 `plate` / `created_at` —— 类型层面杜绝改主键。"""
    assert "plate" not in VehicleUpdate.model_fields
    assert "created_at" not in VehicleUpdate.model_fields
    assert set(VehicleUpdate.model_fields) == {"vtype", "owner", "phone"}


def test_create_schema_has_no_created_at():
    """口径 4：`created_at` 由服务端生成，请求体不传。"""
    assert "created_at" not in VehicleCreate.model_fields


def test_occupation_record_plate_has_no_foreign_key():
    """口径 3 的核心：`occupation_record.plate` **不得**有 FK，否则历史记录会被连带删除。"""
    assert not m.OccupationRecord.__table__.c.plate.foreign_keys


# ---------------------------------------------------------------------------
# GET /api/vehicles
# ---------------------------------------------------------------------------
def test_list_returns_seed_vehicles(client):
    body = _get(client)
    assert body["total"] == SEED_COUNT
    assert len(body["items"]) == SEED_COUNT
    assert body["page"] == 1 and body["size"] == 20
    item = body["items"][0]
    assert set(item) == {"plate", "vtype", "owner", "phone", "created_at"}


def test_list_filter_plate_is_fuzzy_and_case_insensitive(client):
    assert _get(client, plate="京AD")["total"] == 3
    assert _get(client, plate="京ad12345")["total"] == 1  # 小写也命中


def test_list_filter_vtype_exact(client):
    assert _get(client, vtype="燃油")["total"] == 1
    assert _get(client, vtype="新能源")["total"] == 3
    assert client.get("/api/vehicles", params={"vtype": "混动"}).status_code == 422


def test_list_filter_owner_fuzzy(client):
    assert _get(client, owner="汤")["total"] == 1
    assert _get(client, owner="汤瑾睿")["items"][0]["plate"] == SEED_PLATE


def test_list_total_shrinks_with_filter_and_pagination(client):
    body = _get(client, vtype="新能源", page=1, size=1)
    assert body["total"] == 3  # total 是筛选后总数，与分页无关
    assert len(body["items"]) == 1


def test_list_and_filter_combined(client):
    body = _get(client, plate="京A", vtype="燃油", owner="张")
    assert body["total"] == 1
    assert body["items"][0]["plate"] == SEED_FUEL_PLATE


def test_list_blank_params_are_ignored(client):
    assert _get(client, plate="", vtype="", owner="  ")["total"] == SEED_COUNT


def test_list_no_match_returns_empty(client):
    body = _get(client, plate="沪Z99999")
    assert body["total"] == 0 and body["items"] == []


# ---------------------------------------------------------------------------
# POST /api/vehicles
# ---------------------------------------------------------------------------
def test_create_returns_201_and_persists(client):
    resp = client.post(
        "/api/vehicles",
        json={
            "plate": "京AD55555",
            "vtype": "新能源",
            "owner": "新同学",
            "phone": "13800136621",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["plate"] == "京AD55555"
    assert body["owner"] == "新同学"
    assert body["phone"] == "13800136621"
    # created_at 由服务端生成（≈ 当前时刻，而不是请求体里传的）
    created_at = datetime.fromisoformat(body["created_at"])
    assert abs((datetime.now() - created_at).total_seconds()) < 60

    assert _get(client, plate="京AD55555")["total"] == 1
    assert _get(client)["total"] == SEED_COUNT + 1


def test_create_normalizes_plate_to_upper(client):
    resp = client.post(
        "/api/vehicles",
        json={"plate": " 京ad77777 ", "vtype": "新能源", "owner": "小写", "phone": "13800136622"},
    )
    assert resp.status_code == 201
    assert resp.json()["plate"] == "京AD77777"  # 去空白 + 转大写


def test_create_duplicate_plate_returns_409(client):
    """口径 2：重复车牌必须是 409（不是 400），前端靠它提示「车牌号已存在」。"""
    resp = client.post(
        "/api/vehicles",
        json={"plate": SEED_PLATE, "vtype": "新能源", "owner": "重复", "phone": "13800136623"},
    )
    assert resp.status_code == 409
    assert "已存在" in resp.json()["detail"]
    assert _get(client)["total"] == SEED_COUNT  # 没有被写进去


def test_create_duplicate_ignores_case(client):
    resp = client.post(
        "/api/vehicles",
        json={"plate": "京ad12345", "vtype": "新能源", "owner": "x", "phone": "13800136624"},
    )
    assert resp.status_code == 409  # 统一化后与种子车牌相同


def test_create_allows_missing_optional_fields(client):
    """owner / phone 在契约里可空 —— 只给必填字段也应能建。"""
    resp = client.post("/api/vehicles", json={"plate": "京B10001", "vtype": "燃油"})
    assert resp.status_code == 201
    assert resp.json()["owner"] is None
    assert resp.json()["phone"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"plate": "TEST01", "vtype": "燃油"},  # 不符合车牌格式
        {"plate": "", "vtype": "燃油"},  # 空车牌
        {"plate": "京A1234", "vtype": "燃油"},  # 尾段只有 4 位
        {"plate": "京AD12345", "vtype": "混动"},  # 枚举非法
        {"plate": "京AD12345", "vtype": "燃油", "phone": "12345"},  # 手机号非法
        {"plate": "京AD12345", "vtype": "燃油", "owner": "x" * 51},  # 车主超长
    ],
)
def test_create_invalid_payload_returns_422(client, payload):
    assert client.post("/api/vehicles", json=payload).status_code == 422
    assert _get(client)["total"] == SEED_COUNT  # 没有脏数据落库


# ---------------------------------------------------------------------------
# PUT /api/vehicles/{plate}
# ---------------------------------------------------------------------------
def test_update_changes_fields_and_keeps_plate(client):
    resp = client.put(
        f"/api/vehicles/{SEED_PLATE}",
        json={"vtype": "燃油", "owner": "汤瑾睿2", "phone": "13900139000"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["plate"] == SEED_PLATE  # 主键没变
    assert body["owner"] == "汤瑾睿2"
    assert body["phone"] == "13900139000"
    assert body["vtype"] == "燃油"


def test_update_cannot_change_plate_even_if_body_contains_it(client):
    """口径 1：请求体里塞 `plate` 也只是无效字段被忽略，主键纹丝不动。"""
    resp = client.put(
        f"/api/vehicles/{SEED_PLATE}",
        json={"plate": "京X00000", "vtype": "新能源", "owner": "改不动的", "phone": "13800136630"},
    )
    assert resp.status_code == 200
    assert resp.json()["plate"] == SEED_PLATE
    assert _get(client, plate="京X00000")["total"] == 0  # 没有生成新车
    assert _get(client, plate=SEED_PLATE)["total"] == 1


def test_update_partial_payload_keeps_other_fields(client):
    """只发 `vtype` 时，owner / phone 不应被清空（exclude_unset 语义）。"""
    before = _get(client, plate=SEED_PLATE)["items"][0]
    resp = client.put(f"/api/vehicles/{SEED_PLATE}", json={"vtype": "燃油"})
    assert resp.status_code == 200
    after = resp.json()
    assert after["owner"] == before["owner"]
    assert after["phone"] == before["phone"]


def test_update_explicit_null_clears_field(client):
    resp = client.put(f"/api/vehicles/{SEED_PLATE}", json={"vtype": "新能源", "phone": None})
    assert resp.status_code == 200
    assert resp.json()["phone"] is None


def test_update_unknown_plate_returns_404(client):
    resp = client.put(
        "/api/vehicles/京X00000", json={"vtype": "燃油", "owner": "x", "phone": "13800138000"}
    )
    assert resp.status_code == 404


def test_update_invalid_phone_returns_422(client):
    resp = client.put(f"/api/vehicles/{SEED_PLATE}", json={"vtype": "新能源", "phone": "abc"})
    assert resp.status_code == 422


def test_update_plate_lookup_is_case_insensitive(client):
    resp = client.put("/api/vehicles/京ad12345", json={"vtype": "新能源", "owner": "小写定位"})
    assert resp.status_code == 200
    assert resp.json()["owner"] == "小写定位"


# ---------------------------------------------------------------------------
# DELETE /api/vehicles/{plate}
# ---------------------------------------------------------------------------
def test_delete_returns_204_without_body(client):
    resp = client.delete(f"/api/vehicles/{SEED_PLATE}")
    assert resp.status_code == 204
    assert resp.content == b""
    assert _get(client, plate=SEED_PLATE)["total"] == 0
    assert _get(client)["total"] == SEED_COUNT - 1


def test_delete_unknown_plate_returns_404(client):
    assert client.delete("/api/vehicles/京X00000").status_code == 404


def test_delete_does_not_cascade_violation_records(client, db_session):
    """口径 3（最重要）：删车后历史违规记录**仍在** —— 历史是事实记录。

    同时验证：记录不会因为删车而消失（`occupation_record.plate` 无 FK）。
    """
    db_session.add(
        m.OccupationRecord(
            plate=SEED_FUEL_PLATE,
            vtype=m.VTYPE_FUEL,
            pile_id="PILE-004",
            rule_hit=m.RULE_FUEL_OCCUPY,
            occur_time=datetime(2026, 9, 19, 10, 0, 0),
            notify_status=m.NOTIFY_SENT,
        )
    )
    db_session.commit()

    assert client.delete(f"/api/vehicles/{SEED_FUEL_PLATE}").status_code == 204

    # 车辆没了
    assert _get(client, plate=SEED_FUEL_PLATE)["total"] == 0
    # 违规记录还在，且内容完好
    records = client.get("/api/records", params={"plate": SEED_FUEL_PLATE}).json()
    assert records["total"] == 1
    assert records["items"][0]["rule_hit"] == m.RULE_FUEL_OCCUPY
    assert db_session.query(m.OccupationRecord).count() == 1


def test_delete_frees_bound_pile(client, db_session):
    """删车要释放关联桩：FK 声明 SET NULL，SQLite 不强制 → 显式置空，保证与 MySQL 一致。"""
    pile = db_session.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-004").one()
    assert pile.bound_plate == SEED_FUEL_PLATE  # 种子里 PILE-004 绑的就是它

    assert client.delete(f"/api/vehicles/{SEED_FUEL_PLATE}").status_code == 204

    db_session.expire_all()
    pile = db_session.query(m.ChargingPile).filter(m.ChargingPile.pile_id == "PILE-004").one()
    assert pile.bound_plate is None


def test_delete_then_recreate_same_plate_is_201(client):
    """删掉后可以重新录入同一车牌（主键已释放）。"""
    assert client.delete(f"/api/vehicles/{SEED_PLATE}").status_code == 204
    resp = client.post(
        "/api/vehicles",
        json={"plate": SEED_PLATE, "vtype": "新能源", "owner": "重新录入", "phone": "13800136640"},
    )
    assert resp.status_code == 201
    assert resp.json()["owner"] == "重新录入"


# ---------------------------------------------------------------------------
# 与识别闭环的衔接：删车后不再有手机号，但仍能查到历史
# ---------------------------------------------------------------------------
def test_crud_flow_keeps_records_queryable(client):
    """走一遍增 → 查 → 改 → 删，确认 /api/records 全程不受影响且可查。"""
    plate = "京AD99999"
    assert (
        client.post(
            "/api/vehicles",
            json={"plate": plate, "vtype": "新能源", "owner": "流程", "phone": "13800136650"},
        ).status_code
        == 201
    )
    assert _get(client, plate=plate)["total"] == 1
    assert (
        client.put(f"/api/vehicles/{plate}", json={"vtype": "新能源", "owner": "流程2"}).status_code
        == 200
    )
    assert _get(client, plate=plate)["items"][0]["owner"] == "流程2"
    assert client.delete(f"/api/vehicles/{plate}").status_code == 204
    assert client.get("/api/records", params={"plate": plate}).json()["total"] == 0
