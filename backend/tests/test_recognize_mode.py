"""识别桩 stub/real 模式开关的测试（PLAN §2.2 任务 2.5）。

覆盖：
- 默认 = stub（无环境变量时）
- 环境变量 ``RECOGNITION_MODE`` 切 real → 缺 CV 依赖（后端 venv 不装 torch）返回 503，提示可操作
- 环境变量取值非法 → 500
- 两种模式下 /api/recognize 的响应结构都符合契约 §4
- 开关**只认环境变量**，不依赖 `system_config`（契约 §7 仅两项业务阈值，不擅自扩表）

real 的完整 CV 链路在 algo/tests 里已覆盖（有 GPU 依赖，不在这里跑）。
"""

from __future__ import annotations

import pytest

MODE_ENV = "RECOGNITION_MODE"


@pytest.fixture(autouse=True)
def _clean_mode_env(monkeypatch):
    """保证用例之间环境变量互不影响。"""
    monkeypatch.delenv(MODE_ENV, raising=False)
    yield


def test_default_mode_is_stub(client):
    """无环境变量 → 默认 stub，读标注 JSON 返回合规结构。"""
    client.app.dependency_overrides  # noqa: B018 触发 app 初始化
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 200
    body = resp.json()
    # 001 标注（契约 §10）：京AD12345 充电中 → 正常
    assert body["plate"] == "京AD12345"
    assert set(body) == {"plate", "vtype", "confidence", "bbox", "frame_time"}


def test_stub_reads_labels(client):
    resp = client.post("/api/recognize", json={"frame_ref": "002.jpg"})
    assert resp.status_code == 200
    assert resp.json()["plate"] == "京A88888"


def test_blank_env_var_falls_back_to_stub(client, monkeypatch):
    """空串/纯空白等同未设置 → 仍走 stub（部署时清空变量不该炸）。"""
    monkeypatch.setenv(MODE_ENV, "   ")
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 200
    assert resp.json()["plate"] == "京AD12345"


def test_missing_label_is_404_in_stub(client):
    resp = client.post("/api/recognize", json={"frame_ref": "nope.jpg"})
    assert resp.status_code == 404


def test_env_var_real_without_cv_deps_is_503(client, monkeypatch):
    """RECOGNITION_MODE=real → 走 real 分支；后端 venv 无 torch → 503 且提示可操作。"""
    monkeypatch.setenv(MODE_ENV, "real")
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 503
    assert "算法环境" in resp.json()["detail"]


def test_env_var_is_case_insensitive(client, monkeypatch):
    monkeypatch.setenv(MODE_ENV, "REAL")
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 503  # 大写 REAL 同样进 real 分支


def test_illegal_env_var_is_500(client, monkeypatch):
    monkeypatch.setenv(MODE_ENV, "yolo")
    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 500


def test_mode_switch_does_not_read_system_config(client, db_session, monkeypatch):
    """开关与 system_config 解耦：表里塞同名键也不该改变行为（契约 §7 只有两项阈值）。"""
    from app.models import SystemConfig

    db_session.add(SystemConfig(key="recognition_mode", value="real", note="越权扩表，应被忽略"))
    db_session.commit()

    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 200  # 仍是 stub，没有进 real 分支
    assert resp.json()["plate"] == "京AD12345"
