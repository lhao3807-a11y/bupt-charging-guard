"""系统参数读写 —— 对应 GET / PUT /api/config（CONTRACT §6.9，v1.6 新增，供第 5 页）。

背景（契约 §6.9）：§1.1 第 5 页「系统参数配置」要求阈值可编辑并落 `system_config`。

```text
GET /api/config                  → ConfigPage
PUT /api/config  {full_timeout_min: 45}   → ConfigPage（更新后的全量）
```

**守 §7 红线（本模块存在的全部理由）**：

- **白名单只有两个键**。规则引擎的阈值全部来自 `system_config`（`rule_engine.get_config_int`），
  这张表一旦被写进野键，影响的是「有没有违规」的业务判定，不是显示问题。
  故 `ConfigUpdate` 用 `extra="forbid"`，未知 key 直接 422。
- **取值范围 1–1440 分钟**。0 会让规则②③对任何车立刻命中，负数无意义。
- **键缺失抛 `ConfigMissingError` 而不是给默认值**。阈值缺失是数据故障，必须暴露 ——
  与 `rule_engine.get_config_int` 完全一致（契约 §7「严禁硬编码兜底」）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.rule_engine import ConfigMissingError
from app.schemas import ConfigItem, ConfigPage, ConfigUpdate

router = APIRouter(tags=["config"])

#: 契约 §7 白名单 —— 只允许读写的键。**新增阈值必须先改契约 §7**
CONFIG_KEYS: tuple[str, ...] = ("full_timeout_min", "abnormal_park_min")


def _read_config(db: Session, key: str) -> m.SystemConfig:
    """读取白名单内的配置项；缺失 → `ConfigMissingError`（不静默兜底）。"""
    row = db.get(m.SystemConfig, key)
    if row is None:
        raise ConfigMissingError(
            f"system_config 缺少参数 {key!r}：请确认已执行 backend/sql/schema.sql 的种子数据"
        )
    return row


def _to_page(db: Session) -> ConfigPage:
    """读取白名单全部键，组装 `ConfigPage`（GET 与 PUT 共用）。"""
    items = [
        ConfigItem(key=row.key, value=row.value, note=row.note)
        for row in (_read_config(db, key) for key in CONFIG_KEYS)
    ]
    return ConfigPage(items=items, total=len(items))


@router.get("/api/config", response_model=ConfigPage, summary="读取系统参数（§7 白名单）")
def get_config(db: Session = Depends(get_db)) -> ConfigPage:
    """返回 `full_timeout_min` / `abnormal_park_min` 两项配置。"""
    return _to_page(db)


@router.put("/api/config", response_model=ConfigPage, summary="修改系统参数（仅两个阈值）")
def update_config(payload: ConfigUpdate, db: Session = Depends(get_db)) -> ConfigPage:
    """更新阈值，返回更新后的**全量**配置（前端据此刷新表格，不必再发一次 GET）。

    - 未知 key / 越界值 / 空请求体 → 422（由 `ConfigUpdate` 拦下，到不了这里）。
    - `value` 以字符串落库（`system_config.value` 是 VARCHAR(50)）。
    """
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if value is None:
            continue
        row = _read_config(db, key)
        row.value = str(value)

    db.commit()
    return _to_page(db)
