"""占用生命周期 —— 「本次占用」标识的唯一入口（契约 v1.9 §3.6 / T1 设计）。

**为什么单开一个模块**：`occupancy_id` 的正确性决定判重、提醒与统计是否可信，
但「到车 / 离车 / 换车」这三个动作散落在模拟器、编排与演示夹具里。
把它们收敛到一处，才能保证「同样的事情只在一个地方发生」——
否则很容易出现「某处直接改了 `bound_plate` 却忘了换 `occupancy_id`」，
那正是第 3 周自动轮询下「换车被误合并 / 离车重入算成同一次」的根因。

三条口径（改动前先改契约）：

1. **到车**（``begin_occupancy``）：桩上原本没车，或换成了另一块牌 → 生成新标识。
   同车仍在原桩 → **保持原标识**（桩状态怎么流转都不影响）。
2. **离车**（``end_occupancy``）：解绑并把标识置 ``NULL``，回到「空闲且无车」。
3. **落库快照**：违规记录落库时把桩上的标识抄进 ``occupation_record.occupancy_id``，
   之后**永不改写**（历史记录不回溯，呼应验收 A08）。

维护人：汤瑾睿
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app import models as m


def begin_occupancy(
    pile: m.ChargingPile,
    plate: str,
    at: datetime,
    *,
    db: Session | None = None,
) -> str:
    """**到车**：把 ``plate`` 绑定到 ``pile``，返回本次占用的 ``occupancy_id``。

    - 同车仍在（``bound_plate`` 未变）→ 标识与所有时间字段**原样不动**，
      返回已有标识。规则②③的判定依赖不被打断的到达时间，随意重置会让久停判定失真。
    - 换车 / 空桩来车 → 生成**新**标识，``start_time`` 重置为 ``at``，``end_time`` 清空，
      ``status`` 置 ``空闲`` —— 「停上去了」不等于「在充电」，能否充电由充电桩决定。

    :param db: 传入则顺带 ``commit``（调用方通常已在事务里，可省略）。
    """
    if not plate:
        raise ValueError("begin_occupancy 需要非空车牌：离车请调用 end_occupancy()")

    if pile.bound_plate == plate and pile.occupancy_id:
        return pile.occupancy_id

    occupancy_id = m.make_occupancy_id(pile.pile_id, at)
    pile.bound_plate = plate
    pile.occupancy_id = occupancy_id
    pile.start_time = at
    pile.end_time = None
    pile.status = m.PILE_IDLE

    if db is not None:
        db.commit()
    return occupancy_id


def end_occupancy(pile: m.ChargingPile, *, db: Session | None = None) -> None:
    """**离车**：解绑并清空占用标识与两个时间字段，回到「空闲且无车」。

    与模拟器里的 ``_release()`` 是同一语义，区别只在调用点：模拟器是「超时释放」，
    这里是「车走了」。两者都**必须**清 ``occupancy_id``，否则下次到车会与上次的判重键撞上。
    """
    pile.status = m.PILE_IDLE
    pile.bound_plate = None
    pile.occupancy_id = None
    pile.start_time = None
    pile.end_time = None
    pile.scenario = None

    if db is not None:
        db.commit()


def current_occupancy_id(pile: m.ChargingPile) -> str | None:
    """读取当前占用标识；桩上无车时返回 ``None``（不现场编造一个）。"""
    if pile.bound_plate is None or pile.occupancy_id is None:
        return None
    return pile.occupancy_id
