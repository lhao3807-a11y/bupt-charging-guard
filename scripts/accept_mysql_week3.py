"""A11：独立 MySQL 库四场景十轮闭环、真实 HTTP 状态读取与重启恢复。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app import models as m
from app.db import SessionLocal, engine
from app.main import app
from app.pipeline import Pipeline, write_status
from fastapi.testclient import TestClient
from seed_week3_demo import seed
from sqlalchemy import text


def main() -> None:
    # 只允许专用验收库；不得把演示夹具写入开发/生产库。
    assert engine.dialect.name == "mysql"
    assert engine.url.database and engine.url.database.startswith("tang_week3_accept_")
    moment = datetime(2026, 10, 13, 20, 0)
    m.init_db(engine)
    results = []
    with SessionLocal() as db, tempfile.TemporaryDirectory() as temp:
        m.seed_db(db)
        seed(db, "all", moment, None)
        version = db.execute(text("SELECT VERSION()")).scalar_one()
        assert version.startswith("8.")
        frames = Path(temp) / "frames"
        frames.mkdir()
        for name in ("001.jpg", "002.jpg", "003.jpg", "004.jpg"):
            (frames / name).write_bytes(b"stub frame; recognition uses labels")
        status = str(Path(temp) / "status.json")
        os.environ["PIPELINE_STATUS_FILE"] = status
        os.environ["RECOGNITION_MODE"] = "stub"
        worker = Pipeline(db, frame_dir=str(frames))
        with TestClient(app) as client:
            for index in range(10):
                run = worker.run_once(now=moment)
                assert run.error is None
                assert not any(frame.error for frame in run.frames)
                assert sorted(f.rule_hit for f in run.frames if f.rule_hit) == [1, 2, 3]
                assert sum(f.rule_hit is None for f in run.frames) == 1
                if index:
                    assert run.newly_notified == 0
                write_status(run, status)
                response = client.get("/api/pipeline/status")
                assert response.status_code == 200
                assert response.json()["violations"] == 3
                results.append(
                    {"round": index + 1, "http_status": response.status_code, **run.to_dict()}
                )
        record_ids = [row.id for row in db.query(m.OccupationRecord).all()]
        assert len(record_ids) == 3
    # 新会话与新编排实例不继承识别缓存，判重和发送状态必须由 MySQL 恢复。
    with SessionLocal() as db, tempfile.TemporaryDirectory() as temp:
        for name in ("001.jpg", "002.jpg", "003.jpg", "004.jpg"):
            (Path(temp) / name).write_bytes(b"stub frame; recognition uses labels")
        restarted = Pipeline(db, frame_dir=temp).run_once(now=moment)
        assert restarted.error is None
        assert not any(f.error for f in restarted.frames)
        assert restarted.newly_notified == 0
        assert sorted(row.id for row in db.query(m.OccupationRecord).all()) == sorted(record_ids)
    payload = {
        "mysql_version": version,
        "database": engine.url.database,
        "recognition_mode": "stub",
        "rounds": results,
        "restart": restarted.to_dict(),
        "assertions": "10 rounds, four scenes, HTTP 200, three records, no repeated sends, restart recovery: PASS",
    }
    target = REPO / "docs/acceptance/week3/09-mysql-ten-rounds.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MySQL {version}: 10 rounds + restart PASS; evidence: {target}")


if __name__ == "__main__":
    main()
