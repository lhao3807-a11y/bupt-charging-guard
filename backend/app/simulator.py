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
- 判定**不自己实现**：超时释放前把「这一刻的车 + 桩状态」交给 `rule_engine.judge()`
  判定并 `save_violation()` 落库，保证与 `/api/judge` 走的是同一套规则、同一套去重口径。
  ⚠️ 早期版本只改桩状态、不落库，于是文档宣称的「自然触发规则③」实际是一条记录都没有
  —— 第 2 周验收审查发现，本模块因此补上落库并钉了回归测试。

**确定性**：状态推进只看 `now` 与桩自身的时间字段，不掷随机数 ——
同样的输入必然得到同样的输出，测试才能钉住行为，演示也能复现。

**时间基准**：库里 `DATETIME` 一律是**朴素本地时**（见 `models.py`）。
调用方若传入带时区的时刻（ISO 8601 允许 `+08:00`），先经 `normalize_moment()`
归一化再参与相减 —— 否则「aware − naive」会抛 `TypeError` 变成 500
（第 2 周验收审查阻断项之一）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app import models as m
from app.rule_engine import get_config_int, judge, save_violation
from app.schemas import RecognitionResult

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


def normalize_moment(value: datetime | None) -> datetime | None:
    """把带时区的时刻归一化为**本地朴素时间**；朴素时刻原样返回。

    **为什么是「转本地再去掉 tzinfo」而不是拒绝**：ISO 8601 允许带偏移量
    （``2026-09-08T10:30:00+08:00``），它是合法输入，拒掉会让前端日期控件动辄 422；
    而库里 `DATETIME` 全是朴素本地时（`models.py`），拿 aware 值去减 naive 值会
    直接 `TypeError` → 500。归一到同一基准后两种写法都能用，且结果可预期。
    """
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone().replace(tzinfo=None)


def _lookup_vtype(db: Session, plate: str | None) -> str | None:
    """按车牌查车型；车没录入 `vehicle` 表 → `None`。

    **为什么不能兜底成「新能源」**：车型决定命中哪条规则（① vs ③），
    猜一个就等于往库里写假数据。没录入就是没法判定，宁可这次不落库。
    """
    if not plate:
        return None
    row = db.get(m.Vehicle, plate)
    return None if row is None else row.vtype


#: rule_hit → 规则序号，仅用于把落库结果写进人类可读的 `reason`
_RULE_LABELS = ("", "①", "②", "③")


def _record_timeout_violation(
    pile: m.ChargingPile,
    db: Session,
    now: datetime,
) -> int | None:
    """释放**之前**把「充满超时未移车」判定并落库，返回命中的 rule_hit（未命中 → `None`）。

    判定交回 `rule_engine.judge()` 而不是本模块自己写 `rule_hit=3`：
    桩上停的也可能是燃油车（模拟器不挑车），那种情况引擎会判规则①，
    本模块照抄一个 3 就会和 `/api/judge` 的口径打架。
    """
    if pile.bound_plate is None:
        return None
    vtype = _lookup_vtype(db, pile.bound_plate)
    if vtype is None:
        return None

    # bbox / confidence 在「模拟器造的时间点」上没有意义，但要凑齐契约 §4 的结构
    hit = judge(
        RecognitionResult(
            plate=pile.bound_plate,
            vtype=vtype,
            confidence=1.0,
            bbox=[0, 0, 0, 0],
            frame_time=now,
        ),
        db,
        now=now,
    )
    if hit is None:
        return None
    save_violation(db, hit)
    return hit.rule_hit


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
        # 先判定落库、再释放：释放后 bound_plate 清空，引擎就反查不到桩了
        hit_rule = _record_timeout_violation(pile, db, now)
        _release(pile)
        reason = f"充满后超过 {timeout} 分钟未移车，判定超时并释放车位"
        if hit_rule is not None:
            reason += f"；已记入违规记录（规则{_RULE_LABELS[hit_rule]}）"
        return PileChange(pile.pile_id, before, m.PILE_IDLE, reason)

    return None


def advance(db: Session, now: datetime | None = None) -> SimResult:
    """推进全部充电桩一步，并**提交**事务。

    :param now: 推进到的时刻，默认系统时钟；传固定值便于测试与复现。
        带时区的值会先经 `normalize_moment()` 归一到本地朴素时间。
    """
    moment = normalize_moment(now) or datetime.now()
    result = SimResult(advanced_at=moment)

    for pile in db.query(m.ChargingPile).order_by(m.ChargingPile.pile_id.asc()).all():
        change = advance_pile(pile, db, moment)
        if change is not None:
            result.changes.append(change)

    if result.changes:
        db.commit()
    return result
