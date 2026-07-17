import os
import tempfile

# 在导入 app 之前隔离数据目录，避免污染 dev 数据
_tmp = tempfile.mkdtemp(prefix="ai-review-test-")
os.environ["AI_REVIEW_DATA_DIR"] = _tmp

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_health() -> None:
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert body["backend"] == "fastapi"
