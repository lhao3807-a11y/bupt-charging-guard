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

import os

import pytest

MODE_ENV = "RECOGNITION_MODE"
FRAME_DIR_ENV = "FRAME_SOURCE_DIR"


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


# ---------------------------------------------------------------------------
# real 识别目录与编排取帧目录同源（契约 v1.9 §6.11 口径 6 / 验收 A10）
#
# 旧实现把 real 的读图目录**写死**成 `algo/samples/frames`，而编排按
# `FRAME_SOURCE_DIR` 取帧：两处不等时，编排按 A 目录算帧摘要，real 却去 B 目录
# 读**同名**的另一张图 —— 验收 A10 明确要求「按帧关联无串帧」，这里钉死它。
# ---------------------------------------------------------------------------
def test_real_frame_dir_follows_frame_source_dir(monkeypatch, tmp_path):
    from app import pipeline as pl
    from app.routers import recognize

    monkeypatch.setenv(FRAME_DIR_ENV, str(tmp_path))
    assert recognize.frame_source_dir() == str(tmp_path)
    assert recognize.frame_path_for("001.jpg") == os.path.join(str(tmp_path), "001.jpg")
    assert recognize.frame_source_dir() == pl.default_frame_dir(), "两个解析器必须同源"


def test_real_frame_dir_default_is_samples_frames(monkeypatch):
    """未设置 FRAME_SOURCE_DIR → 仍是 algo/samples/frames（既有 demo 行为不变）。"""
    from app import pipeline as pl
    from app.routers import recognize

    monkeypatch.delenv(FRAME_DIR_ENV, raising=False)
    expected = os.path.join(pl.repo_root(), "algo", "samples", "frames")
    assert recognize.frame_source_dir() == expected
    assert recognize.frame_path_for("001.jpg") == os.path.join(expected, "001.jpg")


def test_real_frame_dir_relative_env_resolves_like_pipeline(monkeypatch):
    """相对路径按**仓库根**解析 —— 不能一处按仓库根、一处按 cwd（那样又会分叉）。"""
    from app import pipeline as pl
    from app.routers import recognize

    monkeypatch.setenv(FRAME_DIR_ENV, os.path.join("algo", "samples", "frames"))
    assert recognize.frame_source_dir() == pl.default_frame_dir()
    assert recognize.frame_source_dir() == os.path.join(pl.repo_root(), "algo", "samples", "frames")


def test_real_mode_looks_up_image_in_frame_source_dir(client, monkeypatch, tmp_path):
    """行为级：real 模式找图确实去 FRAME_SOURCE_DIR 指的地方（旧实现只会说 algo/samples/frames）。"""
    monkeypatch.setenv(MODE_ENV, "real")
    monkeypatch.setenv(FRAME_DIR_ENV, str(tmp_path))  # 空目录 → 必然找不到

    resp = client.post("/api/recognize", json={"frame_ref": "001.jpg"})
    assert resp.status_code == 404
    assert str(tmp_path) in resp.json()["detail"], "报错里应给出实际查找目录，便于排障"


# ---------------------------------------------------------------------------
# real 模式的失败必须可见（验收 A09）
#
# CV 依赖只在 .venv-algo 里，这里通过替换 `_cv_recognize` 注入「检出 / 无牌 /
# 空号码」三种结果 —— 被测的是**失败口径**，不是模型本身。
# ---------------------------------------------------------------------------
def _inject_cv(monkeypatch, result):
    """把 real 模式的 CV 调用替换成固定返回（不加载模型）。"""
    from app.routers import recognize

    monkeypatch.setattr(recognize, "_cv_recognize", lambda path: result)


def _real_request(client, monkeypatch, tmp_path, name="001.jpg"):
    """在 real 模式下请求一帧（图片文件存在，内容无所谓 —— CV 已被注入替换）。"""
    monkeypatch.setenv(MODE_ENV, "real")
    monkeypatch.setenv(FRAME_DIR_ENV, str(tmp_path))
    (tmp_path / name).write_bytes(b"not-a-real-jpeg")
    return client.post("/api/recognize", json={"frame_ref": name})


def test_real_no_plate_detected_is_422(client, monkeypatch, tmp_path):
    """画面里没检出车牌 → 422，且说明「未检出」而不是假装成功。"""
    _inject_cv(monkeypatch, None)
    resp = _real_request(client, monkeypatch, tmp_path)
    assert resp.status_code == 422
    assert "未在画面中检出租车牌" in resp.json()["detail"]


def test_real_empty_ocr_plate_is_422(client, monkeypatch, tmp_path):
    """检出框但 OCR 空号码 → 422（旧实现会拿空串往下走，静默判成「无违规」）。"""
    _inject_cv(
        monkeypatch,
        {
            "plate": "   ",
            "vtype": "新能源",
            "confidence": 0.9,
            "bbox": [10, 20, 30, 40],
            "frame_time": "2026-10-13T10:00:00",
        },
    )
    resp = _real_request(client, monkeypatch, tmp_path)
    assert resp.status_code == 422
    assert "OCR 空结果" in resp.json()["detail"]


def test_real_success_structure_matches_contract(client, monkeypatch, tmp_path):
    """成功路径：结构仍与 stub 完全一致（契约 §4），号码原样透出。"""
    _inject_cv(
        monkeypatch,
        {
            "plate": "沪AG61020",
            "vtype": "新能源",
            "confidence": 0.89,
            "bbox": [1273, 1060, 309, 111],
            "frame_time": "2026-10-13T10:00:00",
        },
    )
    resp = _real_request(client, monkeypatch, tmp_path)
    assert resp.status_code == 200
    body = resp.json()
    assert body["plate"] == "沪AG61020"
    assert set(body) == {"plate", "vtype", "confidence", "bbox", "frame_time"}
