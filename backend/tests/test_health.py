"""冒烟测试：GET /api/health 必须返回 200 且 status=ok。"""

from app.main import app
from fastapi.testclient import TestClient


def test_health_ok():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
