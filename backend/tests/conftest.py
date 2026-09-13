"""pytest 配置：把 backend/ 加入 sys.path，使 `import app` 可用；并提供接口层夹具。"""

import os
import sys

import pytest

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.db import get_db
from app.models import Base, seed_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_session():
    """独立内存库（每用例一份），已建表 + 灌种子。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    test_session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = test_session_factory()
    seed_db(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """TestClient，用独立内存库替换 get_db 依赖（不触碰开发库 app.db）。"""
    from app.main import app as fastapi_app
    from fastapi.testclient import TestClient

    def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.clear()
