"""充电状态适配器 + 四场景模拟夹具（第 3 周 T5 / 验收 A02–A04、A12）。

**为什么要单独一层**：充电状态现在是模拟的，第四周若要接 OCPP / 真实运营商，
只有「外部状态词 → 内部桩状态」这一段会变。把映射收在一个适配器里，
规则引擎与模拟器就**不必知道数据是从哪儿来的** —— 换数据源时改这一个文件。

**本周只交付模拟实现与映射测试**（`WEEK3_PLAN.md` T5 明确：不接真实运营商）。

四个确定性场景（同样输入 + 同样时刻 → 同样结果，便于复现与验收）：

| 场景 | 车型 | 桩状态 | 期望命中 |
|---|---|---|---|
| `fuel_occupy` 燃油占位 | 燃油 | 空闲（**不充电**） | 规则① |
| `idle_park` 未充电久停 | 新能源 | 空闲（**保持不充电**） | 规则②（超过 `abnormal_park_min`） |
| `full_timeout` 充满超时 | 新能源 | 已充满 | 规则③（超过 `full_timeout_min`） |
| `normal` 正常充电 | 新能源 | 充电中 | 规则④ 不违规 |

维护人：汤瑾睿
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models as m
from app import occupancy
from app.rule_engine import get_config_int

#: 四个演示场景（写进 `charging_pile.scenario`，**不参与任何判定**，仅供演示与追溯）
SCENARIO_FUEL = "fuel_occupy"
SCENARIO_IDLE = "idle_park"
SCENARIO_FULL = "full_timeout"
SCENARIO_NORMAL = "normal"
SCENARIOS = (SCENARIO_FUEL, SCENARIO_IDLE, SCENARIO_FULL, SCENARIO_NORMAL)

#: 场景 → 中文标签（脚本输出与演示脚本直接用）
SCENARIO_LABELS: dict[str, str] = {
    SCENARIO_FUEL: "燃油占位",
    SCENARIO_IDLE: "未充电久停",
    SCENARIO_FULL: "已充满超时",
    SCENARIO_NORMAL: "正常充电",
}

#: 场景默认「已经过了多少分钟」（比阈值多 10 分钟，确保一判定就命中）
_DEFAULT_OVERSHOOT_MIN = 10

#: 车型要求：防止把燃油车演示成正常充电、或把新能源车摆进燃油占位场景
_SCENARIO_VTYPE: dict[str, str] = {
    SCENARIO_FUEL: m.VTYPE_FUEL,
    SCENARIO_IDLE: m.VTYPE_NEW_ENERGY,
    SCENARIO_FULL: m.VTYPE_NEW_ENERGY,
    SCENARIO_NORMAL: m.VTYPE_NEW_ENERGY,
}

#: 外部充电状态词表（运营商 / OCPP 侧常见写法）→ 内部桩状态。
#: 未知的写法**明确报错**，不静默当成「空闲」—— 静默兜底会让演示里的状态说不清来源。
EXTERNAL_STATUS_MAP: dict[str, str] = {
    "available": m.PILE_IDLE,
    "idle": m.PILE_IDLE,
    "free": m.PILE_IDLE,
    "charging": m.PILE_CHARGING,
    "occupied": m.PILE_CHARGING,
    "charging_completed": m.PILE_FULL,
    "completed": m.PILE_FULL,
    "full": m.PILE_FULL,
    "suspended": m.PILE_IDLE,
}


class UnknownChargingStatus(ValueError):
    """外部状态词不在映射表里 —— 宁可报错，也不猜。"""


def map_status(external: str) -> str:
    """外部充电状态 → 内部桩状态；未知词抛 `UnknownChargingStatus`。

    大小写与空白都不敏感：外部系统的字段往往带空格或全大写。
    """
    key = (external or "").strip().lower()
    if key not in EXTERNAL_STATUS_MAP:
        raise UnknownChargingStatus(
            f"未知的外部充电状态：{external!r}（已登记：{' / '.join(sorted(EXTERNAL_STATUS_MAP))}）"
        )
    return EXTERNAL_STATUS_MAP[key]


@dataclass(frozen=True)
class ScenarioSpec:
    """一个场景的**完整描述**：把它喂给规则引擎会得到什么，是可预期的。"""

    key: str
    label: str
    vtype: str
    status: str
    #: 该场景下「已经过去多久」的基准字段（规则②用 start_time、③用 end_time）
    elapsed_basis: str | None
    #: 是否允许模拟器把它推进到「充电中」
    hold_charging: bool


SPECS: dict[str, ScenarioSpec] = {
    SCENARIO_FUEL: ScenarioSpec(
        SCENARIO_FUEL, SCENARIO_LABELS[SCENARIO_FUEL], m.VTYPE_FUEL, m.PILE_IDLE, None, True
    ),
    SCENARIO_IDLE: ScenarioSpec(
        SCENARIO_IDLE,
        SCENARIO_LABELS[SCENARIO_IDLE],
        m.VTYPE_NEW_ENERGY,
        m.PILE_IDLE,
        "start_time",
        True,
    ),
    SCENARIO_FULL: ScenarioSpec(
        SCENARIO_FULL,
        SCENARIO_LABELS[SCENARIO_FULL],
        m.VTYPE_NEW_ENERGY,
        m.PILE_FULL,
        "end_time",
        False,
    ),
    SCENARIO_NORMAL: ScenarioSpec(
        SCENARIO_NORMAL,
        SCENARIO_LABELS[SCENARIO_NORMAL],
        m.VTYPE_NEW_ENERGY,
        m.PILE_CHARGING,
        None,
        False,
    ),
}


def _elapsed_for(scenario: str, db: Session, overshoot: int | None) -> timedelta:
    """算出该场景「已经过去多久」= 业务阈值 + 超出量。

    阈值一律查 `system_config`（契约 §7 严禁硬编码）：把阈值改成 120 分钟，
    场景里的 `start_time` / `end_time` 会自动跟着变，演示仍然命中 ——
    若在这里写死 30，改了阈值演示就散了。
    """
    if scenario == SCENARIO_IDLE:
        base = get_config_int(db, "abnormal_park_min")
    elif scenario == SCENARIO_FULL:
        base = get_config_int(db, "full_timeout_min")
    else:
        base = 0
    extra = _DEFAULT_OVERSHOOT_MIN if overshoot is None else overshoot
    return timedelta(minutes=base + extra)


def apply_scenario(
    pile: m.ChargingPile,
    plate: str,
    scenario: str,
    at: datetime,
    db: Session,
    *,
    vtype: str | None = None,
    overshoot_min: int | None = None,
) -> str:
    """把某个桩摆成指定场景，返回本次占用的 `occupancy_id`。

    - 车型由**场景**决定（`vtype` 可显式覆盖），但会与车辆表核对：
      把燃油车摆进「正常充电」是演示语义错误，直接报错（T5 要求）。
    - 时间基准一律以 `at` 为「现在」往前推，不依赖系统时钟 —— 同样输入同样结果。
    """
    if scenario not in SPECS:
        raise ValueError(f"未知场景：{scenario!r}（可选 {' / '.join(SCENARIOS)}）")
    spec = SPECS[scenario]

    vehicle = db.get(m.Vehicle, plate)
    if vehicle is not None:
        actual = vtype or vehicle.vtype
        if actual != spec.vtype:
            raise ValueError(
                f"场景 {scenario}（{spec.label}）需要{spec.vtype}车，"
                f"但 {plate} 是{actual}车 —— 换一辆车或换个场景，不要为了演示改车型"
            )

    occupancy.begin_occupancy(pile, plate, at, db=db)
    pile.status = spec.status
    pile.scenario = scenario

    if spec.elapsed_basis == "start_time":
        pile.start_time = at - _elapsed_for(scenario, db, overshoot_min)
        pile.end_time = None
    elif spec.elapsed_basis == "end_time":
        pile.end_time = at - _elapsed_for(scenario, db, overshoot_min)
    else:
        pile.end_time = None

    db.commit()
    return pile.occupancy_id


def holds_charging(pile: m.ChargingPile) -> bool:
    """该桩是否**不应该**被模拟器推进到「充电中」。

    两条理由都成立就不推进：① 场景要求保持未充电（A02 的久停场景不能被普通
    自动充电流程抢先推进）；② 桩上是燃油车 —— **燃油车不能被演示成正常充电**（T5）。
    """
    return pile.scenario in (SCENARIO_IDLE, SCENARIO_FUEL)
