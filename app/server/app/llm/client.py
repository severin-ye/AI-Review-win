"""OpenAI 兼容 LLM 客户端（设计文档 §3：一套代码通吃 OpenAI/DeepSeek/通义/本地 vLLM）。

- base_url / api_key / model 从 settings 表读取（键 llm.base_url、llm.api_key、llm.model）。
- chat_json()：优先 response_format={"type": "json_object"} 结构化输出；
  服务端不支持时降级为普通模式 + 从文本中提取首个 JSON 对象/数组；tenacity 重试 3 次。
- 未配置 api_key 时抛 LLMNotConfiguredError（API 层转 400 友好提示；检索流程降级处理）。
"""
from __future__ import annotations

import json
import re
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.user_settings import llm_config


class LLMNotConfiguredError(RuntimeError):
    """未配置 llm.api_key（或 base_url/model 缺失）。"""


def _client():
    """按当前 settings 构造 OpenAI 客户端；未配置则抛 LLMNotConfiguredError。"""
    cfg = llm_config()
    if not cfg["api_key"]:
        raise LLMNotConfiguredError("未配置 LLM API Key，请到设置页填写 llm.api_key")
    if not cfg["base_url"]:
        raise LLMNotConfiguredError("未配置 LLM Base URL，请到设置页填写 llm.base_url")
    if not cfg["model"]:
        raise LLMNotConfiguredError("未配置 LLM 模型，请到设置页填写 llm.model")
    from openai import OpenAI

    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=60.0), cfg["model"]


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


def _extract_json(text: str) -> Any:
    """从模型输出中提取首个合法 JSON 值：先整串解析，再试 ```json 代码块，最后按括号配对扫描。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for match in _JSON_BLOCK_RE.finditer(text):
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
    # 括号配对扫描：找第一个 { 或 [，配对到对应闭合符
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise ValueError(f"模型输出中未找到 JSON：{text[:200]!r}")
    pairs = {"{": "}", "[": "]"}
    open_ch = text[start]
    close_ch = pairs[open_ch]
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"模型输出 JSON 括号不配对：{text[:200]!r}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception)
    & retry_if_not_exception_type(LLMNotConfiguredError),  # 未配置属用户错误，重试无意义
    reraise=True,
)
def _chat_once(system: str, user: str, use_json_mode: bool) -> str:
    client, model = _client()
    kwargs: dict[str, Any] = {}
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def chat_json(system: str, user: str, schema_hint: dict | None = None) -> Any:
    """调用 LLM 并返回解析后的 JSON 值（dict 或 list）。

    schema_hint：可选的 JSON 结构示例，附加到 user prompt 末尾引导模型输出。
    未配置 api_key → LLMNotConfiguredError；其余异常经 tenacity 重试 3 次后抛出。
    """
    if schema_hint is not None:
        user = (
            f"{user}\n\n请严格按以下 JSON 结构返回（不要输出多余文字）：\n"
            f"{json.dumps(schema_hint, ensure_ascii=False)}"
        )
    try:
        raw = _chat_once(system, user, use_json_mode=True)
    except LLMNotConfiguredError:
        raise
    except Exception:
        # 服务端不支持 response_format 等场景：降级普通模式 + JSON 提取
        raw = _chat_once(system, user, use_json_mode=False)
    return _extract_json(raw)
