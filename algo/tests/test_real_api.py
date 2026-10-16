"""Real photo through the production recognition router, with no database writes."""

import json
from pathlib import Path

import pytest

pytest.importorskip("ultralytics")
pytest.importorskip("hyperlpr3")
from algo.recognize.plate import DEFAULT_WEIGHTS

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not Path(DEFAULT_WEIGHTS).is_file(), reason="Real plate model unavailable")
def test_real_photo_through_recognition_http_router(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    monkeypatch.syspath_prepend(str(ROOT / "backend"))
    from app.routers import recognize
    from app.schemas import RecognitionResult

    rows = json.loads((ROOT / "algo/dataset_plate_web/manifest.json").read_text(encoding="utf-8"))
    item = next(r for r in rows if r["split"] == "val")
    path = ROOT / item["image"]
    monkeypatch.setenv("FRAME_SOURCE_DIR", str(path.parent))
    monkeypatch.setenv("RECOGNITION_MODE", "real")
    app = FastAPI()
    app.include_router(recognize.router)
    with TestClient(app) as client:
        response = client.post("/api/recognize", json={"frame_ref": path.name})
    assert response.status_code == 200
    parsed = RecognitionResult.model_validate(response.json())
    assert parsed.plate == item["plate"]
    assert parsed.vtype.value == item["vtype"]
