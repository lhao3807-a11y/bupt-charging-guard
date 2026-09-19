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

from pydantic import BaseModel, Field, field_validator


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
