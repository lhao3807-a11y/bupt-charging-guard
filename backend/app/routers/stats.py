"""违规统计聚合 —— 对应 GET /api/stats（CONTRACT §6.8，v1.6 新增，供第 4 页）。

背景（契约 §6.8）：第 4 页「报警统计」要 ECharts 柱/折线/饼，数据来自 `occupation_record`
的聚合。此前没有聚合接口，前端若自己拉全量记录再统计，数据量大时既拖垮页面，
又与 §6.4 的分页口径不一致。

```text
GET /api/stats?days=7   → StatsResp
```

**三条口径（改动前先改契约）**：

1. **`by_rule` 固定 4 项**（rule_hit 0/1/2/3 升序），无记录也返回 `count: 0`。
   序列顺序由后端钉死，前端不重排 —— 否则「同一份数据两个页面顺序不同」这种
   图表对不齐的问题会重现（契约 §3.5 处理列名分叉时的同款教训）。
2. **`by_date` 连续补洞**：窗口内没有记录的日期补 `count: 0`，折线图不必前端补点。
3. **聚合在 Python 侧做**，不用 `DATE()` / `DATE_FORMAT()` 这类数据库函数 ——
   SQLite 与 MySQL 的日期函数写法不同（契约 §2「换库只改连接串」要求行为一致），
   演示原型数据量也远没到需要在库内聚合的程度。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import RULE_LABELS, DateCount, RuleCount, StatsResp

router = APIRouter(tags=["stats"])

_DAYS_DEFAULT = 7
_DAYS_MIN = 1
_DAYS_MAX = 90


def build_stats(
    db: Session,
    *,
    days: int = _DAYS_DEFAULT,
    now: datetime | None = None,
) -> StatsResp:
    """按窗口聚合违规记录（纯函数，便于测试固定 `now`）。

    :param days: 窗口天数，含今天（``days=1`` 即「今天」）。
    :param now: 判定「今天」的时刻，默认取系统时钟；**仅内部与测试使用**。
    """
    today = (now or datetime.now()).date()
    window_start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time())
    window_end = datetime.combine(today, datetime.max.time())

    rows = (
        db.query(m.OccupationRecord.occur_time, m.OccupationRecord.rule_hit)
        .filter(
            m.OccupationRecord.occur_time >= window_start,
            m.OccupationRecord.occur_time <= window_end,
        )
        .all()
    )

    by_rule_counts: dict[int, int] = {rule: 0 for rule in sorted(RULE_LABELS)}
    by_date_counts: dict[date, int] = {}
    for occur_time, rule_hit in rows:
        by_rule_counts[rule_hit] = by_rule_counts.get(rule_hit, 0) + 1
        day = occur_time.date()
        by_date_counts[day] = by_date_counts.get(day, 0) + 1

    by_rule = [
        RuleCount(rule_hit=rule, label=RULE_LABELS[rule], count=by_rule_counts[rule])
        for rule in sorted(by_rule_counts)
    ]
    # 连续日期序列：窗口内每天一个点，缺失补 0（口径 2）
    by_date = [
        DateCount(
            date=(window_start.date() + timedelta(days=offset)).isoformat(),
            count=by_date_counts.get(window_start.date() + timedelta(days=offset), 0),
        )
        for offset in range(days)
    ]

    return StatsResp(
        total=sum(by_date_counts.values()),
        by_rule=by_rule,
        by_date=by_date,
        window_start=window_start,
        window_end=window_end,
        days=days,
    )


@router.get("/api/stats", response_model=StatsResp, summary="违规统计聚合（按规则 / 按日期）")
def get_stats(
    days: int = Query(
        _DAYS_DEFAULT, ge=_DAYS_MIN, le=_DAYS_MAX, description="统计窗口天数，含今天"
    ),
    db: Session = Depends(get_db),
) -> StatsResp:
    """返回最近 `days` 天（含今天）的违规统计，供第 4 页图表直接取用。"""
    return build_stats(db, days=days)
