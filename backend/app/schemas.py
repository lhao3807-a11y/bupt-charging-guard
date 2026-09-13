"""Pydantic 数据模型 —— 唯一事实源见 docs/CONTRACT.md。

所有模型严格对应契约第 3~6 节：
- vehicle / charging_pile / occupation_record / system_config 四表
- RecognitionResult / ViolationRecord / FrameRef / NotifyResp / RecordPage

ENUM 在模型层用 str-Enum 校验（开发期 SQLite 不依赖 DB 原生 ENUM）。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


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
