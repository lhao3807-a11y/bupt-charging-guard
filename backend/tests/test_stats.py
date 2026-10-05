"""违规统计聚合的测试（契约 v1.6 §6.8，第 4 页 / PLAN 任务 5.7 的 C2）。

覆盖点：
- `by_rule` **固定 4 项**（0/1/2/3 升序），无记录也返回 `count: 0`
- `by_date` **连续日期序列**，缺失日期补 0（折线图不必前端补点）
- 三个总数恒等：`total == sum(by_rule) == sum(by_date)`
- 窗口由 `days` 控制，窗口外记录不计入；`days` 越界 → 422
- `build_stats` 是纯函数，可传固定 `now`（测试不依赖真实时钟）
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app import models as m
from app.routers.stats import build_stats
from app.schemas import RULE_LABELS

# 固定基准时刻，避免测试受「今天」影响
NOW = datetime(2026, 9, 8, 12, 0, 0)


def _add_record(db, occur_time: datetime, rule_hit: int, plate="京AD12345", pile_id="PILE-001"):
    db.add(
        m.OccupationRecord(
            plate=plate,
            vtype=m.VTYPE_NEW_ENERGY,
            pile_id=pile_id,
            rule_hit=rule_hit,
            occur_time=occur_time,
        )
    )
    db.commit()


def _get(client, **params):
    resp = client.get("/api/stats", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_empty_database_returns_zeroed_series(client):
    """种子只灌车辆/桩/配置，没有违规记录 → 全 0，但序列形状必须完整。"""
    body = _get(client)
    assert body["total"] == 0
    assert [(item["rule_hit"], item["count"]) for item in body["by_rule"]] == [
        (0, 0),
        (1, 0),
        (2, 0),
        (3, 0),
    ]
    assert len(body["by_date"]) == 7  # days 默认 7


def test_by_rule_is_fixed_four_items_in_order(db_session):
    _add_record(db_session, NOW, m.RULE_FULL_NOT_MOVED)
    stats = build_stats(db_session, days=7, now=NOW)
    hits = [item.rule_hit for item in stats.by_rule]
    assert hits == [0, 1, 2, 3]  # 顺序由后端钉死，前端不重排
    assert [item.count for item in stats.by_rule] == [0, 0, 0, 1]


def test_by_rule_labels(db_session):
    _add_record(db_session, NOW, m.RULE_FUEL_OCCUPY)
    stats = build_stats(db_session, days=7, now=NOW)
    labels = {item.rule_hit: item.label for item in stats.by_rule}
    assert labels == RULE_LABELS
    assert labels[1] == "燃油占位"


def test_totals_are_consistent(db_session):
    _add_record(db_session, NOW, m.RULE_FUEL_OCCUPY)
    _add_record(db_session, NOW - timedelta(days=1), m.RULE_ABNORMAL)
    _add_record(db_session, NOW - timedelta(days=1), m.RULE_ABNORMAL)
    stats = build_stats(db_session, days=7, now=NOW)
    assert stats.total == 3
    assert sum(item.count for item in stats.by_rule) == stats.total
    assert sum(item.count for item in stats.by_date) == stats.total


def test_by_date_is_continuous_with_zero_fill(db_session):
    _add_record(db_session, NOW, m.RULE_FUEL_OCCUPY)  # 9-08
    _add_record(db_session, NOW - timedelta(days=3), m.RULE_ABNORMAL)  # 9-05
    stats = build_stats(db_session, days=5, now=NOW)
    counts = [(item.date, item.count) for item in stats.by_date]
    # 窗口 = 09-04 … 09-08（升序）；09-04/06/07 无记录 → 补 0，不能跳过
    assert [date for date, _ in counts] == [
        "2026-09-04",
        "2026-09-05",
        "2026-09-06",
        "2026-09-07",
        "2026-09-08",
    ]
    assert [count for _, count in counts] == [0, 1, 0, 0, 1]


def test_by_date_format_is_iso_date(db_session):
    _add_record(db_session, NOW, m.RULE_FUEL_OCCUPY)
    stats = build_stats(db_session, days=1, now=NOW)
    assert stats.by_date[0].date == "2026-09-08"


def test_records_outside_window_are_excluded(db_session):
    _add_record(db_session, NOW, m.RULE_FUEL_OCCUPY)  # 窗口内
    _add_record(db_session, NOW - timedelta(days=30), m.RULE_ABNORMAL)  # 窗口外
    stats = build_stats(db_session, days=7, now=NOW)
    assert stats.total == 1
    assert stats.by_rule[1].count == 1
    assert stats.by_rule[2].count == 0


def test_window_bounds_are_inclusive(db_session):
    """窗口上下界**含边界**（与 §6.4 时间口径一致）：当天 00:00:00 与 23:59:59 都要算进来。"""
    _add_record(db_session, datetime(2026, 9, 8, 0, 0, 0), m.RULE_FUEL_OCCUPY)
    _add_record(db_session, datetime(2026, 9, 8, 23, 59, 59), m.RULE_FUEL_OCCUPY)
    stats = build_stats(db_session, days=1, now=NOW)
    assert stats.total == 2
    assert stats.window_start == datetime(2026, 9, 8, 0, 0, 0)
    assert stats.window_end == datetime(2026, 9, 8, 23, 59, 59, 999999)


def test_days_one_means_today_only(db_session):
    _add_record(db_session, NOW, m.RULE_FUEL_OCCUPY)
    _add_record(db_session, NOW - timedelta(days=1), m.RULE_ABNORMAL)
    stats = build_stats(db_session, days=1, now=NOW)
    assert stats.total == 1
    assert len(stats.by_date) == 1


def test_days_is_echoed_and_window_spans_days(db_session):
    stats = build_stats(db_session, days=14, now=NOW)
    assert stats.days == 14
    assert len(stats.by_date) == 14
    assert (stats.window_end.date() - stats.window_start.date()).days == 13


def test_endpoint_days_query(client):
    assert len(_get(client, days=3)["by_date"]) == 3
    assert _get(client, days=3)["days"] == 3


def test_days_out_of_range_is_422(client):
    assert client.get("/api/stats", params={"days": 0}).status_code == 422
    assert client.get("/api/stats", params={"days": 91}).status_code == 422


def test_rule_zero_is_counted_too(db_session):
    """`rule_hit=0`（正常）也是窗口内的记录，不能因为它不违规就漏掉。"""
    _add_record(db_session, NOW, m.RULE_NORMAL)
    stats = build_stats(db_session, days=7, now=NOW)
    assert stats.total == 1
    assert stats.by_rule[0].count == 1
