"""`GET /api/records` 筛选参数的测试（契约 v1.3 §6.4）。

覆盖任务书点名的全部口径：
- 7 个参数各自生效（`plate`/`pile_id` 模糊且忽略大小写，其余精确）
- **`total` 随筛选变化**（不是全表总数）—— 前端分页条依赖它
- **`end_time` 只给日期时含当日 23:59:59.999999**（「选同一天查不到数据」的经典坑）
- 多参数 **AND**；不传/传空串不参与过滤（与 v1.2 向后兼容）
- `start_time > end_time` 返回空列表且不报错
- 非法枚举值 / 越界 `rule_hit` / 非法时间格式 → 422（不静默忽略，免得筛了却没生效）
"""

from __future__ import annotations

from datetime import datetime

import pytest
from app import models as m

# 固定的一份记录集（occur_time 特意跨 09-18 / 09-19 / 09-20，用于验证日期边界）
RECORDS = (
    # plate,         vtype,               pile_id,     rule_hit, occur_time,                    notify_status
    (
        "京AD12345",
        m.VTYPE_NEW_ENERGY,
        "PILE-001",
        0,
        datetime(2026, 9, 18, 10, 0, 0),
        m.NOTIFY_PENDING,
    ),
    ("京A88888", m.VTYPE_FUEL, "PILE-004", 1, datetime(2026, 9, 19, 8, 30, 0), m.NOTIFY_SENT),
    (
        "京AD24680",
        m.VTYPE_NEW_ENERGY,
        "PILE-003",
        2,
        datetime(2026, 9, 19, 23, 59, 59),
        m.NOTIFY_PENDING,
    ),
    (
        "京AD67890",
        m.VTYPE_NEW_ENERGY,
        "PILE-002",
        3,
        datetime(2026, 9, 19, 0, 0, 0),
        m.NOTIFY_FAILED,
    ),
    ("京N12345", m.VTYPE_FUEL, "PILE-009", 1, datetime(2026, 9, 20, 9, 0, 0), m.NOTIFY_PENDING),
)


@pytest.fixture()
def records(db_session):
    """清空种子残留后灌入固定记录集，返回该 session（种子本无违规记录，清空是防御性的）。"""
    db_session.query(m.OccupationRecord).delete()
    db_session.add_all(
        m.OccupationRecord(
            plate=plate,
            vtype=vtype,
            pile_id=pile_id,
            rule_hit=rule_hit,
            occur_time=occur_time,
            notify_status=notify_status,
        )
        for plate, vtype, pile_id, rule_hit, occur_time, notify_status in RECORDS
    )
    db_session.commit()
    return db_session


def _get(client, **params):
    resp = client.get("/api/records", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# 基线：不传参数与 v1.2 行为一致
# ---------------------------------------------------------------------------
def test_no_params_returns_all_desc(client, records):
    body = _get(client, page=1, size=20)
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["size"] == 20
    times = [item["occur_time"] for item in body["items"]]
    assert times == sorted(times, reverse=True)  # occur_time 倒序
    assert body["items"][0]["plate"] == "京N12345"  # 最新一条在最前


def test_pagination_slices_the_filtered_set(client, records):
    body = _get(client, page=2, size=2)
    assert body["total"] == 5  # total 是筛选后总数，与分页无关
    assert len(body["items"]) == 2
    assert body["page"] == 2


# ---------------------------------------------------------------------------
# 单参数
# ---------------------------------------------------------------------------
def test_filter_rule_hit_and_total_shrinks(client, records):
    body = _get(client, rule_hit=1)
    assert body["total"] == 2  # 关键：total 必须随筛选变化
    assert {i["plate"] for i in body["items"]} == {"京A88888", "京N12345"}


def test_filter_rule_hit_zero(client, records):
    body = _get(client, rule_hit=0)
    assert body["total"] == 1
    assert body["items"][0]["plate"] == "京AD12345"


def test_filter_plate_is_fuzzy(client, records):
    body = _get(client, plate="京AD")
    assert body["total"] == 3
    assert {i["plate"] for i in body["items"]} == {"京AD12345", "京AD67890", "京AD24680"}


def test_filter_plate_ignores_case(client, records):
    """车牌里的拉丁字母忽略大小写：查 `京n12345` 应命中 `京N12345`。"""
    body = _get(client, plate="京n12345")
    assert body["total"] == 1
    assert body["items"][0]["plate"] == "京N12345"


def test_filter_pile_id_is_fuzzy_and_case_insensitive(client, records):
    body = _get(client, pile_id="003")
    assert body["total"] == 1
    assert body["items"][0]["pile_id"] == "PILE-003"

    body = _get(client, pile_id="pile-00")  # 小写 + 模糊
    assert body["total"] == 5


def test_filter_vtype_exact(client, records):
    body = _get(client, vtype="燃油")
    assert body["total"] == 2
    assert {i["vtype"] for i in body["items"]} == {"燃油"}

    body = _get(client, vtype="新能源")
    assert body["total"] == 3


def test_filter_notify_status_exact(client, records):
    body = _get(client, notify_status="已提醒")
    assert body["total"] == 1
    assert body["items"][0]["plate"] == "京A88888"

    body = _get(client, notify_status="失败")
    assert body["total"] == 1

    body = _get(client, notify_status="未提醒")
    assert body["total"] == 3


# ---------------------------------------------------------------------------
# 时间范围（含边界）
# ---------------------------------------------------------------------------
def test_same_day_range_includes_end_of_day(client, records):
    """只给日期时上界按 23:59:59.999999 —— 09-19 23:59:59 的记录必须查得到。"""
    body = _get(client, start_time="2026-09-19", end_time="2026-09-19")
    assert body["total"] == 3
    assert {i["plate"] for i in body["items"]} == {"京A88888", "京AD24680", "京AD67890"}


def test_same_day_range_excludes_next_day(client, records):
    """09-20 09:00 的记录不能被 09-19 的范围带出来。"""
    body = _get(client, start_time="2026-09-19", end_time="2026-09-19")
    assert all(i["occur_time"].startswith("2026-09-19") for i in body["items"])


def test_start_time_only_is_inclusive(client, records):
    body = _get(client, start_time="2026-09-19T08:30:00")  # 与某条记录同刻，应含
    assert body["total"] == 3
    assert "京A88888" in {i["plate"] for i in body["items"]}


def test_end_time_only_date_is_inclusive(client, records):
    body = _get(client, end_time="2026-09-18")
    assert body["total"] == 1
    assert body["items"][0]["plate"] == "京AD12345"


def test_full_iso_range(client, records):
    body = _get(client, start_time="2026-09-19T00:00:00", end_time="2026-09-19T23:59:59.999999")
    assert body["total"] == 3


def test_start_after_end_returns_empty_without_error(client, records):
    body = _get(client, start_time="2026-09-20", end_time="2026-09-19")
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# 多参数 AND / 空参数 / 异常入参
# ---------------------------------------------------------------------------
def test_multiple_params_are_combined_with_and(client, records):
    # 「京A」模糊命中 京A88888 / 京AD12345 / 京AD24680 / 京AD67890，共 4 条
    assert _get(client, plate="京A")["total"] == 4
    assert _get(client, plate="京A", vtype="燃油")["total"] == 1  # 只剩 京A88888
    assert _get(client, plate="京A", vtype="燃油", rule_hit=1)["total"] == 1
    # 燃油 + 规则 2 无交集 → 空
    body = _get(client, vtype="燃油", rule_hit=2)
    assert body["total"] == 0 and body["items"] == []


def test_and_with_time_and_pagination(client, records):
    body = _get(
        client,
        rule_hit=1,
        start_time="2026-09-19",
        end_time="2026-09-19",
        page=1,
        size=1,
    )
    assert body["total"] == 1  # 筛选后只剩 09-19 的京A88888
    assert len(body["items"]) == 1
    assert body["items"][0]["plate"] == "京A88888"


def test_blank_params_are_ignored(client, records):
    """前端清空筛选框会发空串 —— 视为不传，不能把结果清空。"""
    body = _get(client, plate="", pile_id="  ", start_time="", end_time="")
    assert body["total"] == 5


def test_invalid_vtype_is_422(client, records):
    resp = client.get("/api/records", params={"vtype": "混动"})
    assert resp.status_code == 422


def test_invalid_rule_hit_is_422(client, records):
    assert client.get("/api/records", params={"rule_hit": 9}).status_code == 422
    assert client.get("/api/records", params={"rule_hit": -1}).status_code == 422


def test_invalid_notify_status_is_422(client, records):
    assert client.get("/api/records", params={"notify_status": "待提醒"}).status_code == 422


def test_invalid_time_format_is_422(client, records):
    """格式非法必须报错，不能静默当成没传（否则前端筛了却没生效，排查成本极高）。"""
    assert client.get("/api/records", params={"start_time": "2026/09/19"}).status_code == 422
    assert client.get("/api/records", params={"end_time": "昨天"}).status_code == 422


def test_empty_filtered_result(client, records):
    body = _get(client, plate="沪Z99999")
    assert body["total"] == 0
    assert body["items"] == []
