"""识别桩样例与契约/种子数据的一致性校验（CONTRACT §10）。

这组测试是「联调不返工」的保险丝：
- 每个标注 JSON 必须能直接解析成 ``RecognitionResult``（字段与契约 §4 完全一致）；
- 必须存在同名测试帧（stub 按 ``frame_ref`` 拼路径）；
- 标注里的车牌必须能在种子 ``charging_pile.bound_plate`` 中查到，
  否则 judge 查不到桩、整条闭环会静默断掉；
- 四份样例合起来要能命中契约 §3.3 的全部四条规则（含规则④正常）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app import models as m
from app.db import Base
from app.rule_engine import judge
from app.schemas import RecognitionResult
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMES_DIR = REPO_ROOT / "algo" / "samples" / "frames"
LABELS_DIR = REPO_ROOT / "algo" / "samples" / "labels"

LABEL_FILES = sorted(LABELS_DIR.glob("*.json"))


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    m.seed_db(session)
    try:
        yield session
    finally:
        session.close()


def test_samples_exist():
    """至少要有 1 份样例（契约 §10：1–2 张即可；本项目提供 4 份覆盖四规则）。"""
    assert LABEL_FILES, "algo/samples/labels 下没有任何标注 JSON"


@pytest.mark.parametrize("label_path", LABEL_FILES, ids=lambda p: p.name)
def test_label_parses_as_recognition_result(label_path: Path):
    """标注字段必须与契约 §4 的 RecognitionResult 完全一致。"""
    data = json.loads(label_path.read_text(encoding="utf-8"))
    result = RecognitionResult.model_validate(data)

    assert result.plate
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.bbox) == 4
    assert result.frame_time is not None


@pytest.mark.parametrize("label_path", LABEL_FILES, ids=lambda p: p.name)
def test_matching_frame_file_exists(label_path: Path):
    """stub 按 frame_ref 拼 algo/samples/frames/<name>.jpg，帧文件必须存在。"""
    assert (FRAMES_DIR / f"{label_path.stem}.jpg").is_file()


@pytest.mark.parametrize("label_path", LABEL_FILES, ids=lambda p: p.name)
def test_label_plate_is_bound_to_a_pile(db, label_path: Path):
    """样列车牌必须已绑定到某个桩，否则 judge 无法关联（闭环会断）。"""
    result = RecognitionResult.model_validate(json.loads(label_path.read_text(encoding="utf-8")))
    pile = db.query(m.ChargingPile).filter(m.ChargingPile.bound_plate == result.plate).one_or_none()
    assert pile is not None, f"{label_path.name} 的车牌 {result.plate} 未绑定任何桩"


def test_samples_cover_all_four_rules(db):
    """四份样例合起来必须覆盖规则①②③④，Demo 才能把四条规则都演示到。"""
    hits = set()
    for label_path in LABEL_FILES:
        result = RecognitionResult.model_validate(
            json.loads(label_path.read_text(encoding="utf-8"))
        )
        record = judge(result, db)
        hits.add(None if record is None else record.rule_hit)

    assert hits == {
        None,
        m.RULE_FUEL_OCCUPY,
        m.RULE_ABNORMAL,
        m.RULE_FULL_NOT_MOVED,
    }, f"样例未覆盖全部规则，实际命中：{hits}"
