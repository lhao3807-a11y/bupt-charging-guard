"""SQLAlchemy 连接层（开发期 SQLite / 目标 MySQL 8）。

- 开发期用 SQLite 文件库，第 2 周换 MySQL 8 只改 DATABASE_URL。
- schema.sql（MySQL 8 语法）由汤瑾睿维护，是交付物；
  开发期建表由 Alembic 或 schema.sql 自行管理，本文件只负责连接。
- ENUM 一律在 Pydantic 层校验，禁止依赖 DB 原生 ENUM 行为。
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 开发期 SQLite（*.db 已被 .gitignore 忽略）
DB_PATH = os.path.join(BASE_DIR, "app.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

# SQLite 需关闭同线程检查以兼容 FastAPI 依赖注入
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每次请求一个会话，结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
