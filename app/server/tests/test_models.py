"""M5 模型管理与 api_key 安全测试。

- GET /api/models/status：结构断言（临时数据目录下模型不存在，exists/ready=False，
  loaded=False；不触发任何真实加载）。
- POST /api/models/download：未知模型 400（真实下载走网络，单测不覆盖，见 M5 文档手动验证）。
- llm.api_key 仅写不读：GET 掩码（****+后4位）；PUT 掩码值跳过写入；空串清除。
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="ai-review-test-models-")
os.environ.setdefault("AI_REVIEW_DATA_DIR", _tmp)
os.environ.setdefault("AI_REVIEW_SEGMENTER", "rule")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.core.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Setting  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _raw_setting(key: str):
    with Session(engine) as session:
        row = session.get(Setting, key)
        return row.value if row is not None else None


def test_models_status_structure(client: TestClient) -> None:
    resp = client.get("/api/models/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["models_dir"].endswith("models")
    for key in ("sat", "sat_tokenizer", "bge_m3"):
        entry = body[key]
        for field in ("path", "exists", "size_bytes", "file_count", "missing_files", "ready", "loaded"):
            assert field in entry, f"{key} 缺少字段 {field}"
        # 临时数据目录下模型未下载（同跑的其他模块也不会写入 models/）
        assert entry["exists"] is False
        assert entry["ready"] is False
        assert entry["loaded"] is False
        assert entry["missing_files"], f"{key} 应列出缺失文件"


def test_models_download_guards(client: TestClient) -> None:
    resp = client.post("/api/models/download", json={"models": ["unknown-model"]})
    assert resp.status_code == 400
    assert "未知模型" in resp.json()["detail"]


def test_api_key_write_only_masking(client: TestClient) -> None:
    # 写入真实密钥 → GET 只回掩码（****+后4位）
    assert client.put("/api/settings", json={"llm.api_key": "sk-live-abcdef123456"}).status_code == 200
    body = client.get("/api/settings").json()
    assert body["llm.api_key"] == "****3456"
    assert "abcdef" not in body["llm.api_key"]

    # 掩码原样回传（设置页未修改）→ 库中原值不变
    assert client.put("/api/settings", json={"llm.api_key": "****3456"}).status_code == 200
    import json as _json

    assert _json.loads(_raw_setting("llm.api_key")) == "sk-live-abcdef123456"

    # 新值覆盖；空串清除
    assert client.put("/api/settings", json={"llm.api_key": "sk-new-key-9999"}).status_code == 200
    assert _json.loads(_raw_setting("llm.api_key")) == "sk-new-key-9999"
    assert client.get("/api/settings").json()["llm.api_key"] == "****9999"
    assert client.put("/api/settings", json={"llm.api_key": ""}).status_code == 200
    assert _json.loads(_raw_setting("llm.api_key")) == ""
    assert client.get("/api/settings").json()["llm.api_key"] == ""

    # 收尾：恢复测试用 dummy key，避免影响同跑的其他模块（review/export 各自显式覆盖，此处保险）
    assert client.put("/api/settings", json={"llm.api_key": "sk-test"}).status_code == 200


def test_settings_new_defaults(client: TestClient) -> None:
    body = client.get("/api/settings").json()
    assert "output.dir" in body
    assert body["docx.first_line_indent"] == 0.5
