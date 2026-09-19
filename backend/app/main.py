"""FastAPI 入口 —— 桩点北邮 · 充电桩车位防占系统。

端点（唯一事实源见 docs/CONTRACT.md §6）：
    POST   /api/recognize           输入帧 → 识别结果（stub 读标注）
    POST   /api/judge               识别结果 → 违规判定（命中即落库）
    POST   /api/notify              违规 → 短信沙箱（写库+日志）
    GET    /api/records             后台查询违规记录（分页 + 筛选，契约 §6.4）
    GET    /api/vehicles            车辆列表（分页 + 筛选，契约 §6.6）
    POST   /api/vehicles            新增车辆（车牌已存在 → 409）
    PUT    /api/vehicles/{plate}    更新车辆（车牌主键不可改）
    DELETE /api/vehicles/{plate}    删除车辆（204，不级联删违规记录）
    GET    /api/health              冒烟/健康检查

启动时自动建表 + 灌种子（开发期 SQLite；正式交付物是 backend/sql/schema.sql）。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import SessionLocal, engine
from app.models import init_db, seed_db
from app.routers.judge import router as judge_router
from app.routers.notify import router as notify_router
from app.routers.recognize import router as recognize_router
from app.routers.records import router as records_router
from app.routers.vehicles import router as vehicles_router
from app.schemas import HealthResp


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化开发库：建表 + 种子（已存在则跳过）。"""
    init_db(engine)
    session = SessionLocal()
    try:
        seed_db(session)
    finally:
        session.close()
    yield


app = FastAPI(
    title="桩点北邮 · 充电桩车位防占系统",
    version="0.2.0",
    description="识别—判断—提醒 智能闭环（演示原型）",
    lifespan=lifespan,
)

app.include_router(recognize_router)
app.include_router(judge_router)
app.include_router(notify_router)
app.include_router(records_router)
app.include_router(vehicles_router)


@app.get("/api/health", response_model=HealthResp, tags=["health"])
def health() -> HealthResp:
    """冒烟/健康检查，供 CI 与 TestClient 探活。"""
    return HealthResp(status="ok")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
