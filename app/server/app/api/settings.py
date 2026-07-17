"""设置接口：整包 get / put，存 SQLite settings 表（值为 JSON 字符串）。

GET 合并内置默认值（DB 未写入的键也能读到默认），支持设计文档第 8 节全部键：
llm.base_url / llm.api_key / llm.model、retrieve.query_count / vector_topk / bm25_topk /
rrf_k / enabled、embedding.provider / embedding.model、docx.* / segment.* / output.dir 等。
PUT 为通用键值写入（任意点分键均可），值为任意 JSON。

M5 api_key 安全（务实方案）：llm.api_key 仅写不读——GET 返回掩码（****+后4位），
PUT 收到掩码值（**** 开头）时跳过写入（保留原值），空串表示清除。
OS 钥匙串（keytar / keyring）留作后续工作（见设计文档 §8）。
"""
import json
from typing import Any

from fastapi import APIRouter
from sqlmodel import Session, select

from app.core.db import engine
from app.core.user_settings import DEFAULT_REVIEW_PROMPT
from app.models import Setting

router = APIRouter(prefix="/settings", tags=["settings"])

# 内置默认值（设计文档 §8）；DB 中有值时以 DB 为准
DEFAULT_SETTINGS: dict[str, Any] = {
    "llm.base_url": "",
    "llm.api_key": "",
    "llm.model": "",
    "review.prompt": DEFAULT_REVIEW_PROMPT,
    "retrieve.query_count": 8,
    "retrieve.vector_topk": 3,
    "retrieve.bm25_topk": 3,
    "retrieve.rrf_k": 60,
    "retrieve.enabled": True,
    "embedding.provider": "local",
    "embedding.model": "BAAI/bge-m3",
    "docx.has_review_table": "Y",
    "docx.first_line_indent": 0.5,
    "output.dir": "",
    "segment.min_sentence_length": 10,
    "segment.review_references": False,
}

_API_KEY_FIELD = "llm.api_key"


def _mask_api_key(value: Any) -> str:
    """非空密钥 → ****+后4位；空值原样返回。"""
    text = str(value or "")
    if not text:
        return ""
    tail = text[-4:] if len(text) > 4 else text
    return f"****{tail}"


@router.get("")
def get_all_settings() -> dict:
    with Session(engine) as session:
        rows = session.exec(select(Setting)).all()
    result: dict = dict(DEFAULT_SETTINGS)
    for row in rows:
        try:
            result[row.key] = json.loads(row.value)
        except (json.JSONDecodeError, TypeError):
            result[row.key] = row.value
    # api_key 仅写不读：对外只暴露掩码
    result[_API_KEY_FIELD] = _mask_api_key(result.get(_API_KEY_FIELD))
    return result


@router.put("")
def put_settings(payload: dict) -> dict:
    with Session(engine) as session:
        for key, value in payload.items():
            # 掩码原样回传（设置页未修改密钥）→ 跳过，保留库中原值
            if key == _API_KEY_FIELD and isinstance(value, str) and value.startswith("****"):
                continue
            row = session.get(Setting, key)
            if row is None:
                row = Setting(key=key, value=json.dumps(value, ensure_ascii=False))
            else:
                row.value = json.dumps(value, ensure_ascii=False)
            session.add(row)
        session.commit()
    return {"ok": True}


@router.post("/test-llm")
def test_llm_connection() -> dict:
    """LLM 连通性测试：读取库中已保存配置，发起一次最小 chat 调用（单发不重试）。

    始终返回 200：成功 {"ok": true, model, latency_ms}；
    失败 {"ok": false, message}（配置缺失 / 网络 / 鉴权 / 模型名错误均不外抛，由前端打红叉）。
    """
    import time

    from app.core.user_settings import llm_config

    cfg = llm_config()
    missing = [k for k in ("base_url", "api_key", "model") if not cfg[k]]
    if missing:
        return {
            "ok": False,
            "stage": "config",
            "message": f"配置不完整（缺少 {', '.join(missing)}），请填写后保存再测试",
        }
    try:
        from openai import OpenAI

        client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=30.0)
        started = time.monotonic()
        resp = client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
            temperature=0,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        reply = (resp.choices[0].message.content or "").strip()
        return {"ok": True, "model": cfg["model"], "latency_ms": latency_ms, "reply": reply[:50]}
    except Exception as exc:  # 连接失败 / 401 / 404 / 400 等统一转为 ok=false
        status = getattr(exc, "status_code", None)
        detail = str(exc).replace("\n", " ")[:300]
        message = f"HTTP {status}：{detail}" if status else detail
        return {"ok": False, "stage": "connect", "message": message}
