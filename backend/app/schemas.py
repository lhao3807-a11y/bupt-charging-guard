"""Pydantic 数据模型 —— 唯一事实源见 docs/CONTRACT.md。

所有模型严格对应契约第 3~6 节：
- vehicle / charging_pile / occupation_record / system_config 四表
- RecognitionResult / ViolationRecord / FrameRef / NotifyResp / RecordPage

ENUM 在模型层用 str-Enum 校验（开发期 SQLite 不依赖 DB 原生 ENUM）。
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class VType(str, Enum):
    """车型：由绿牌/蓝牌判定。"""

    新能源 = "新能源"
    燃油 = "燃油"


class PileStatus(str, Enum):
    """充电桩运行状态（模拟）。"""

    空闲 = "空闲"
    充电中 = "充电中"
    已充满 = "已充满"


class NotifyStatus(str, Enum):
    """提醒状态。"""

    未提醒 = "未提醒"
    已提醒 = "已提醒"
    失败 = "失败"


# ---------------------------------------------------------------------------
# 健康
# ---------------------------------------------------------------------------
class HealthResp(BaseModel):
    status: str = "ok"


# ---------------------------------------------------------------------------
# 识别桩 -> /api/recognize
# ---------------------------------------------------------------------------
class FrameRef(BaseModel):
    """识别请求入参：frame_ref 为相对 algo/samples/frames/ 的文件名。"""

    frame_ref: str = Field(
        ..., description="测试帧文件名，如 001.jpg；stub 读 algo/samples/labels/001.json"
    )


class RecognitionResult(BaseModel):
    """识别结果，真实 CV 与识别桩 stub 返回同一结构。"""

    plate: str = Field(..., description="车牌号")
    vtype: VType = Field(..., description="车型")
    confidence: float = Field(..., ge=0, le=1, description="识别置信度")
    bbox: list[int] = Field(..., min_length=4, max_length=4, description="[x, y, w, h]")
    frame_time: datetime = Field(..., description="帧时间，ISO 8601")


# ---------------------------------------------------------------------------
# 违规记录 -> /api/judge, /api/records
# ---------------------------------------------------------------------------
class ViolationRecord(BaseModel):
    """违规记录，对应 occupation_record。rule_hit: 1 燃油占位 / 2 异常占位 / 3 充满未移车 / 0 正常。"""

    id: int | None = Field(None, description="记录 ID（来自 occupation_record），新建时为 None")
    plate: str
    vtype: VType
    pile_id: str | None = Field(None, description="关联桩 ID（v0.1 新增）")
    rule_hit: int = Field(..., ge=0, le=3)
    occur_time: datetime
    notify_status: NotifyStatus = NotifyStatus.未提醒


# ---------------------------------------------------------------------------
# 短信沙箱 -> /api/notify
# ---------------------------------------------------------------------------
class NotifyReq(BaseModel):
    """短信沙箱请求：按记录 id 更新提醒状态（契约 v1.2 起入参含 id）。"""

    id: int = Field(..., description="违规记录 ID，取自 /api/judge 的返回")
    notify_status: NotifyStatus


class NotifyResp(BaseModel):
    notify_status: NotifyStatus


# ---------------------------------------------------------------------------
# 后台分页 -> /api/records
# ---------------------------------------------------------------------------
class RecordPage(BaseModel):
    """违规记录分页响应，total 供前端分页条使用（v0.1 明确）。"""

    items: list[ViolationRecord] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20


# ---------------------------------------------------------------------------
# 车辆信息 -> /api/vehicles（CONTRACT §6.6，v1.3 新增）
# ---------------------------------------------------------------------------
#: 车牌 / 手机号格式校验。口径与前端表单一致（`VehicleView.vue` 的 `PLATE_RE` / `PHONE_RE`），
#: 契约 §6.6 要求「格式非法 → 422（Pydantic 校验）」，故在模型层拦住而不是靠 DB。
PLATE_RE = re.compile(r"^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$")
PHONE_RE = re.compile(r"^1[3-9]\d{9}$")

#: 约束常量，便于报错文案与测试引用（对应契约 §3.1 的 VARCHAR 长度）
PLATE_MAX_LEN = 15
OWNER_MAX_LEN = 50


def normalize_plate(raw: str) -> str:
    """车牌统一化：去首尾空白 + 拉丁字母转大写。

    车牌惯例全大写，且前端筛选也是按大写比较（`VehicleView.vue` 的 `toUpperCase()`）；
    URL 路径里的车牌也走同一函数，保证「列表拿到的车牌」能直接用于 PUT / DELETE。
    """
    return raw.strip().upper()


def _validate_plate(raw: str) -> str:
    plate = normalize_plate(raw)
    if not PLATE_RE.match(plate) or len(plate) > PLATE_MAX_LEN:
        raise ValueError(f"车牌号格式不正确：{raw!r}（示例：京A12345 / 京AD12345）")
    return plate


def _validate_phone(raw: str | None) -> str | None:
    """手机号：允许留空（→ None），填了就必须是 11 位大陆手机号。"""
    if raw is None:
        return None
    phone = raw.strip()
    if not phone:
        return None
    if not PHONE_RE.match(phone):
        raise ValueError(f"手机号格式不正确：{raw!r}（11 位，1 开头）")
    return phone


def _strip_optional(raw: str | None) -> str | None:
    """可选文本字段：去空白，空串归一为 None（DB 列可空，前端清空会发空串）。"""
    if raw is None:
        return None
    text = raw.strip()
    return text or None


class Vehicle(BaseModel):
    """车辆信息（读模型），对应 `vehicle` 全字段（契约 §3.1）。

    读模型**刻意不做格式校验**：库里若存在历史遗留数据，也不该让接口 500。
    """

    plate: str = Field(..., description="车牌号（主键）")
    vtype: VType
    owner: str | None = Field(None, description="车主")
    phone: str | None = Field(None, description="手机号")
    created_at: datetime = Field(..., description="录入时间（服务端生成）")


class VehicleCreate(BaseModel):
    """`POST /api/vehicles` 请求体：**不含 `created_at`**（服务端生成，契约 §6.6）。"""

    plate: str = Field(..., max_length=PLATE_MAX_LEN, description="车牌号（主键，新增后不可改）")
    vtype: VType
    owner: str | None = Field(None, max_length=OWNER_MAX_LEN, description="车主")
    phone: str | None = Field(None, max_length=20, description="手机号")

    @field_validator("plate")
    @classmethod
    def _v_plate(cls, value: str) -> str:
        return _validate_plate(value)

    @field_validator("phone")
    @classmethod
    def _v_phone(cls, value: str | None) -> str | None:
        return _validate_phone(value)

    @field_validator("owner")
    @classmethod
    def _v_owner(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class VehicleUpdate(BaseModel):
    """`PUT /api/vehicles/{plate}` 请求体。

    **刻意不含 `plate` / `created_at`** —— 车牌是主键不可改，从类型上杜绝改主键
    （契约 §6.6 口径 1）；车牌只出现在路径参数里，仅用于定位。
    """

    vtype: VType
    owner: str | None = Field(None, max_length=OWNER_MAX_LEN, description="车主")
    phone: str | None = Field(None, max_length=20, description="手机号")

    @field_validator("phone")
    @classmethod
    def _v_phone(cls, value: str | None) -> str | None:
        return _validate_phone(value)

    @field_validator("owner")
    @classmethod
    def _v_owner(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class VehiclePage(BaseModel):
    """车辆分页响应，`total` 为**筛选后**总数（契约 §6.6 口径 5）。"""

    items: list[Vehicle] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20


# ---------------------------------------------------------------------------
# 充电桩 -> /api/piles（CONTRACT §6.7，v1.6 新增，供第 3 页）
# ---------------------------------------------------------------------------
class PileItem(BaseModel):
    """充电桩（读模型），对应 `charging_pile` 全字段（契约 §3.2）。

    列名按契约 §3.5 的 P3 行：`pile_id`→桩 ID / `status`→状态 / `bound_plate`→绑定车牌 /
    `start_time`→开始充电时间 / `end_time`→充满时间。
    """

    pile_id: str = Field(..., description="桩 ID（主键）")
    status: PileStatus = Field(..., description="运行状态：空闲 / 充电中 / 已充满")
    bound_plate: str | None = Field(None, description="当前绑定的车牌，未占用为 None")
    start_time: datetime | None = Field(None, description="开始充电（到达）时间")
    end_time: datetime | None = Field(None, description="充满时间，未充满为 None")


class PilePage(BaseModel):
    """充电桩分页响应。

    `summary` 是**筛选后**的三状态计数 + `total`，供第 3 页「状态总览卡」直接取值，
    前端不必再算一遍（契约 §6.7 口径 2）。
    """

    items: list[PileItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20
    summary: dict[str, int] = Field(
        default_factory=dict,
        description="筛选后各状态计数，含 '空闲' / '充电中' / '已充满' / 'total'",
    )


# ---------------------------------------------------------------------------
# 违规统计 -> /api/stats（CONTRACT §6.8，v1.6 新增，供第 4 页）
# ---------------------------------------------------------------------------
#: rule_hit → 中文标签（第 4 页图表图例直接取用）
RULE_LABELS: dict[int, str] = {
    0: "正常",
    1: "燃油占位",
    2: "异常占位",
    3: "充满未移车",
}


class RuleCount(BaseModel):
    """按命中规则聚合的计数。序列顺序由后端固定（0/1/2/3），前端不重排。"""

    rule_hit: int = Field(..., ge=0, le=3, description="命中规则 0~3")
    label: str = Field(..., description="规则中文名，如 燃油占位")
    count: int = Field(0, description="窗口内该规则的记录数")


class DateCount(BaseModel):
    """按日期聚合的计数（趋势序列），缺失日期补 0。"""

    date: str = Field(..., description="日期，YYYY-MM-DD")
    count: int = Field(0, description="当日记录数")


class StatsResp(BaseModel):
    """违规统计聚合响应（契约 §6.8）。"""

    total: int = Field(0, description="窗口内记录总数 = sum(by_rule.count)")
    by_rule: list[RuleCount] = Field(default_factory=list, description="固定 4 项，rule_hit 升序")
    by_date: list[DateCount] = Field(default_factory=list, description="连续日期序列，升序")
    window_start: datetime = Field(..., description="统计窗口下界（含）")
    window_end: datetime = Field(..., description="统计窗口上界（含）")
    days: int = Field(..., description="窗口天数，回显请求值")


# ---------------------------------------------------------------------------
# 系统参数 -> /api/config（CONTRACT §6.9，v1.6 新增，供第 5 页）
# ---------------------------------------------------------------------------
class ConfigItem(BaseModel):
    """系统参数项，对应 `system_config` 全字段（契约 §3.4）。

    `value` 是**字符串**（`system_config.value` 为 VARCHAR(50)），与数据库保持一致，
    由调用方按需转 int —— 避免「库里是 '30'、接口返回 30」的类型漂移。
    """

    key: str = Field(..., description="参数键")
    value: str = Field(..., description="参数值（字符串）")
    note: str | None = Field(None, description="说明")


class ConfigPage(BaseModel):
    """系统参数列表响应（GET 与 PUT 共用：PUT 返回更新后的全量）。"""

    items: list[ConfigItem] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# 充电状态模拟器 -> /api/piles/simulate（CONTRACT §6.10，v1.7 新增）
# ---------------------------------------------------------------------------
class PileChange(BaseModel):
    """单个桩的一次状态变化。"""

    pile_id: str = Field(..., description="桩 ID")
    from_status: str = Field(..., description="变化前的状态")
    to_status: str = Field(..., description="变化后的状态")
    reason: str = Field(..., description="变化原因（人话，便于演示时讲解）")


class SimulateReq(BaseModel):
    """`POST /api/piles/simulate` 请求体：`at` 用于**演示快进**，不传则取服务端时钟。"""

    at: datetime | None = Field(None, description="把『现在』设为该时刻（ISO 8601）")


class SimulateResp(BaseModel):
    """模拟器推进结果。

    `statuses` 是推进后的**全量状态快照**，前端可直接刷新总览卡，
    不必再发一次 `GET /api/piles`（契约 §6.10 口径 3）。
    """

    advanced_at: datetime = Field(..., description="推进到的时刻")
    changed_count: int = Field(0, description="本次发生变化的桩数")
    changes: list[PileChange] = Field(default_factory=list, description="变化明细")
    statuses: dict[str, str] = Field(default_factory=dict, description="推进后各桩状态")


#: 阈值取值范围（分钟）：下界 1（0 会让规则②③对任何车立刻命中），上界 1440（24 小时）
CONFIG_MIN_VALUE = 1
CONFIG_MAX_VALUE = 1440


class ConfigUpdate(BaseModel):
    """`PUT /api/config` 请求体 —— **白名单仅两个阈值键**（契约 §7 红线）。

    - `extra="forbid"`：请求体出现未知 key → Pydantic 直接 422，
      防止把野键写进 `system_config`（它是规则引擎的唯一配置源）。
    - 两个键都可选，但**至少给一个**（`_v_at_least_one`），全空 → 422。
    """

    model_config = {"extra": "forbid"}

    full_timeout_min: int | None = Field(
        None, ge=CONFIG_MIN_VALUE, le=CONFIG_MAX_VALUE, description="充满超时阈值（分钟）"
    )
    abnormal_park_min: int | None = Field(
        None, ge=CONFIG_MIN_VALUE, le=CONFIG_MAX_VALUE, description="异常占位久停阈值（分钟）"
    )

    @model_validator(mode="after")
    def _v_at_least_one(self) -> ConfigUpdate:
        if self.full_timeout_min is None and self.abnormal_park_min is None:
            raise ValueError("请求体为空：至少需要给出 full_timeout_min / abnormal_park_min 之一")
        return self
