"""LLM 接入：OpenAI 兼容客户端（查询重写 / M4 审校共用）。"""
from app.llm.client import LLMNotConfiguredError, chat_json

__all__ = ["LLMNotConfiguredError", "chat_json"]
