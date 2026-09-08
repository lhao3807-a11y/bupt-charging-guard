"""FastAPI 入口 —— 第 0 天脚手架。

当前仅落地 /api/health 冒烟端点与 Pydantic 模型（见 app/schemas.py）。
其余端点（/api/recognize、/api/judge、/api/notify、/api/records）将在
契约确认升 v1.0 后由吕浩 + 汤瑾睿实现。
"""

from __future__ import annotations

from fastapi import FastAPI

from app.schemas import HealthResp

app = FastAPI(
    title="桩点北邮 · 充电桩车位防占系统",
    version="0.1.0",
    description="识别—判断—提醒 智能闭环（演示原型）",
)


@app.get("/api/health", response_model=HealthResp, tags=["health"])
def health() -> HealthResp:
    """冒烟/健康检查，供 CI 与 TestClient 探活。"""
    return HealthResp(status="ok")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
