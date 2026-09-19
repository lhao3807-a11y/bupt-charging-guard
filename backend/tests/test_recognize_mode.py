"""识别桩 stub/real 模式开关的测试（任务 2.5）。

覆盖：
- 默认 = stub（无环境变量、system_config 无该键/值非法时）
- 环境变量 RECOGNITION_MODE 优先于表，非法值 → 500
- real 模式在缺 CV 依赖（后端 venv 不装 torch）→ 503，提示可操作
- 两种模式下 /api/recognize 的响应结构都符合契约 §4

real 的完整 CV 链路在 algo/tests 里已覆盖（有 GPU 依赖，不在这里跑）。
"""

from __future__ import annotations

import pytest
from app.models import SystemConfig

MODE_ENV = "RECOGNITION_MODE"


@pytest.fixture(autouse=True)
def _clean_mode_env(monkeypatch):
    """保证用例之间环境变量互不影响。"""
    monkeypatch.delenv(MODE_ENV, raising=False)
    yield


def _set_mode(db_session, value: str) -> None:
    row = db_session.query(SystemConfig).filter(SystemConfig.key == "recognition_mode").one()
    row.value = value
    db_session.commit()


def test_default_mode_is_stub(client):
    """PLAN 2.5 硬要求：默认 stub（种子未含该键时也回退 stub）。"""
    client.app.dependency_overrides  # noqa: B018 触发 app 初始化
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 200
    body = resp.json()
    # 001 标注（契约 §10）：京AD12345 充电中 → 正常
    assert body["plate"] == "京AD12345"
    assert set(body) == {"plate", "vtype", "confidence", "bbox", "frame_time"}


def test_stub_reads_labels(client, db_session):
    _set_mode(db_session, "stub")
    resp = client.post("/api/recognize", json={"frame_ref": "002.jpg"})
    assert resp.status_code == 200
    assert resp.json()["plate"] == "京A88888"


def test_missing_label_is_404_in_stub(client):
    resp = client.post("/api/recognize", json={"frame_ref": "nope.jpg"})
    assert resp.status_code == 404


def test_env_var_overrides_table(client, db_session, monkeypatch):
    """环境变量 real 覆盖表里的 stub → 走 real 分支（缺 CV 依赖 → 503）。"""
    _set_mode(db_session, "stub")
    monkeypatch.setenv(MODE_ENV, "real")
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 503
    assert "算法环境" in resp.json()["detail"]


def test_table_real_without_env(client, db_session):
    """表配置 real + 无环境变量 → 同样进 real 分支 → 503（缺依赖）。"""
    _set_mode(db_session, "real")
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 503


def test_illegal_env_var_is_500(client, monkeypatch):
    monkeypatch.setenv(MODE_ENV, "yolo")
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 500


def test_illegal_table_value_falls_back_to_stub(client, db_session):
    _set_mode(db_session, "nonsense")
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 200  # 非法表值 → 默认 stub，正常返回
    assert resp.json()["plate"] == "京AD12345"
