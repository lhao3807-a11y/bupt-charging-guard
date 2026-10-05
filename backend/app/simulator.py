"""充电桩状态模拟器（PLAN §3.2 任务 5.8 初版）。

**为什么需要它**：第 3 页「充电状态展示」要能看到桩的状态**随时间变化**，
否则页面永远显示种子数据那四个静止的桩，演示时看不出系统是活的。
本模块给出一个确定性状态机，让桩按时间自然流转：

```text
空闲（有车） ──等待 SIM_IDLE_TO_CHARGING_MIN──▶ 充电中 ──充 SIM_CHARGING_TO_FULL_MIN──▶ 已充满 ──超过 full_timeout_min──▶ 空闲（车已移走）
```

**与规则引擎的关系（重要）**：

- 已充满 → 移走用的是业务阈值 `full_timeout_min`（**从 `system_config` 读**，契约 §7），
  所以模拟出来的数据会**自然触发规则③「充满未移车」** —— 第 2 页/第 4 页因此有真数据可看，
  不是自造的假流水。
- 前两段时长（等多久开始充、充多久充满）是**模拟器节奏参数**，不是业务判定阈值，
  故用模块常量而**不写进 `system_config`** —— 那张表是规则引擎的唯一配置源，
  写进去就是给契约 §7 白名单开了口子。

**确定性**：状态推进只看 `now` 与桩自身的时间字段，不掷随机数 ——
同样的输入必然得到同样的输出，测试才能钉住行为，演示也能复现。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app import models as m
from app.rule_engine import get_config_int

#: 空闲桩「车已停下 → 开始充电」的等待时长（分钟）
SIM_IDLE_TO_CHARGING_MIN = 3

#: 充电中「开始充电 → 充满」的时长（分钟）
SIM_CHARGING_TO_FULL_MIN = 20


@dataclass
class PileChange:
    """单个桩的一次状态变化，供调用方展示/记录。"""

    pile_id: str
    from_status: str
    to_status: str
    reason: str


@dataclass
class SimResult:
    """一次推进的结果。"""

    advanced_at: datetime
    changes: list[PileChange] = field(default_factory=list)

    @property
    def changed_count(self) -> int:
        return len(self.changes)


def _elapsed_minutes(since: datetime | None, now: datetime) -> float:
    """自 since 起到 now 的分钟数；since 为空（没有时间基准）返回 0 —— 不推进。"""
    if since is None:
        return 0.0
    return max((now - since).total_seconds() / 60.0, 0.0)


def _release(pile: m.ChargingPile) -> None:
    """车已移走：解绑并清空两个时间字段（回到「空闲且无车」的初始态）。"""
    pile.status = m.PILE_IDLE
    pile.bound_plate = None
    pile.start_time = None
    pile.end_time = None


def advance_pile(
    pile: m.ChargingPile,
    db: Session,
    now: datetime,
) -> PileChange | None:
    """按需推进**单个**桩的状态；返回变化，无变化则 `None`。

    一次调用只推进**一步**：真实时间是连续流逝的，一步到位会跳过中间状态，
    演示时看不到「充电中」这档（第 3 页三种状态色就白设计了）。
    """
    if pile.status == m.PILE_IDLE:
        if pile.bound_plate is None:
            return None  # 没有车，等识别系统来绑定
        # start_time 在此处是「车辆到达/绑定的时刻」（规则引擎同一口径）
        if _elapsed_minutes(pile.start_time, now) <= SIM_IDLE_TO_CHARGING_MIN:
            return None
        before = pile.status
        pile.status = m.PILE_CHARGING
        pile.start_time = now  # 重置为「开始充电时刻」，规则②③各取所需
        return PileChange(
            pile.pile_id,
            before,
            m.PILE_CHARGING,
            f"车辆已停放超过 {SIM_IDLE_TO_CHARGING_MIN} 分钟，开始充电",
        )

    if pile.status == m.PILE_CHARGING:
        if _elapsed_minutes(pile.start_time, now) <= SIM_CHARGING_TO_FULL_MIN:
            return None
        before = pile.status
        pile.status = m.PILE_FULL
        pile.end_time = now
        return PileChange(
            pile.pile_id,
            before,
            m.PILE_FULL,
            f"已充电 {SIM_CHARGING_TO_FULL_MIN} 分钟，电池充满",
        )

    if pile.status == m.PILE_FULL:
        # 业务阈值：充满后多久必须移车（契约 §7，严禁硬编码）
        timeout = get_config_int(db, "full_timeout_min")
        if _elapsed_minutes(pile.end_time, now) <= timeout:
            return None
        before = pile.status
        _release(pile)
        return PileChange(
            pile.pile_id,
            before,
            m.PILE_IDLE,
            f"充满后超过 {timeout} 分钟未移车，判定超时并释放车位",
        )

    return None


def advance(db: Session, now: datetime | None = None) -> SimResult:
    """推进全部充电桩一步，并**提交**事务。

    :param now: 推进到的时刻，默认系统时钟；传固定值便于测试与复现。
    """
    moment = now or datetime.now()
    result = SimResult(advanced_at=moment)

    for pile in db.query(m.ChargingPile).order_by(m.ChargingPile.pile_id.asc()).all():
        change = advance_pile(pile, db, moment)
        if change is not None:
            result.changes.append(change)

    if result.changes:
        db.commit()
    return result
