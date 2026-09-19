"""查询条件小工具（路由复用）。

契约 §6.4（记录筛选）与 §6.6（车辆列表筛选）都要求「文本字段模糊匹配、忽略大小写」，
口径必须只定义一处 —— 否则后台两个页面的筛选手感会不一致，而且换库时容易翻车。
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func


def like_ci(column, value: str):
    """大小写不敏感的模糊匹配：``lower(column) LIKE %value.lower()%``。

    显式套 ``lower()``，不依赖各库 ``LIKE`` 的默认排序规则（SQLite 对 ASCII 不敏感、
    MySQL 取决于 collation）—— 保证换库行为一致。中文不受 ``lower()`` 影响，
    故 ``京A`` 仍能匹配 ``京AD12345``。

    注意：``column`` 为 NULL 时（如未关联桩的 ``occupation_record.pile_id``）结果为 NULL，
    不会命中筛选条件 —— 这符合直觉（按桩筛选就不该带出没有桩的记录）。
    """
    return func.lower(column).like(f"%{value.strip().lower()}%")


def enum_exact(value: str | None, allowed: tuple[str, ...], field: str) -> str | None:
    """规整「精确匹配」的枚举查询参数，返回可用值或 ``None``（不参与过滤）。

    - ``None`` / 空串 / 纯空白 → ``None``。前端筛选项选「全部」时发的就是空串
      （见 `VehicleView.vue` 的 `vtype: '' as VType | ''`），**不能当成非法值**，
      否则前端一切到「全部」接口就 422。
    - 合法值 → 原样返回。
    - 其余 → 422。**不静默忽略**：拼错枚举值却返回全量结果，排查成本极高。
    """
    if value is None or not value.strip():
        return None
    key = value.strip()
    if key not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field} 取值非法：{value!r}（可选：{' / '.join(allowed)}）",
        )
    return key
