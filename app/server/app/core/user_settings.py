"""用户设置读取（settings 表，值为 JSON 字符串）。

设计文档第 8 节使用点分键（如 docx.has_review_table、segment.min_sentence_length），
此处同时兼容下划线旧写法，便于调试期手工写库。
"""
from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session

from app.core.db import engine
from app.models import Setting


def get_setting(keys: str | list[str], default: Any = None) -> Any:
    """按顺序尝试多个键，返回第一个存在的设置值（JSON 解码后）。"""
    if isinstance(keys, str):
        keys = [keys]
    with Session(engine) as session:
        for key in keys:
            row = session.get(Setting, key)
            if row is not None:
                try:
                    return json.loads(row.value)
                except (json.JSONDecodeError, TypeError):
                    return row.value
    return default


def has_review_table() -> bool:
    """docx.has_review_table：首个表格是否为审查意见表（默认 Y，即移除）。"""
    value = get_setting(["docx.has_review_table", "has_review_table"], "Y")
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() in ("Y", "YES", "TRUE", "1")


def min_sentence_length() -> int:
    """segment.min_sentence_length：短句碎片合并阈值（默认 10 字符）。"""
    value = get_setting(["segment.min_sentence_length", "segment_min_sentence_length"], 10)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 10


# ---------- M3：LLM / 检索 / embedding（设计文档第 8 节） ----------


def _int_setting(keys: str | list[str], default: int, lo: int, hi: int) -> int:
    value = get_setting(keys, default)
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _bool_setting(keys: str | list[str], default: bool) -> bool:
    value = get_setting(keys, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() in ("Y", "YES", "TRUE", "1")


def llm_config() -> dict:
    """llm.base_url / llm.api_key / llm.model（OpenAI 兼容协议）。"""
    return {
        "base_url": get_setting("llm.base_url", "") or "",
        "api_key": get_setting("llm.api_key", "") or "",
        "model": get_setting("llm.model", "") or "",
    }


def retrieve_query_count() -> int:
    """retrieve.query_count：查询重写问题数（默认 8，范围 5-10，超出自动截断）。"""
    return _int_setting("retrieve.query_count", 8, 5, 10)


def retrieve_vector_topk() -> int:
    """retrieve.vector_topk：向量路每句最终保留条数（默认 3）。"""
    return _int_setting("retrieve.vector_topk", 3, 1, 20)


def retrieve_bm25_topk() -> int:
    """retrieve.bm25_topk：关键词路每句最终保留条数（默认 3）。"""
    return _int_setting("retrieve.bm25_topk", 3, 1, 20)


def retrieve_rrf_k() -> int:
    """retrieve.rrf_k：RRF 融合常数（默认 60，业界常用值）。"""
    return _int_setting("retrieve.rrf_k", 60, 1, 1000)


def retrieve_enabled() -> bool:
    """retrieve.enabled：关闭则纯 LLM 审校（默认开启）。"""
    return _bool_setting("retrieve.enabled", True)


def review_references() -> bool:
    """segment.review_references：是否审校/检索参考文献块（默认否）。"""
    return _bool_setting("segment.review_references", False)


# ---------- M4：LLM 审校（设计文档 §5.2④、§8） ----------

DEFAULT_REVIEW_PROMPT = """你是资深医学文稿审校专家，负责逐句核查医学文稿的质量问题。

请逐句检查以下四类问题：
1. 事实错误：与循证医学证据不符的表述（诊断标准、正常值范围、药物剂量、指南推荐等）。
   凡事实性判断，若提供了检索证据，必须在 explanation 中引用所依据的证据编号（如 [E1]）；
2. 术语错误：医学术语使用不规范、疾病/药品名称不准确、中英文缩写误用；
3. 语法错误：病句、搭配不当、成分残缺或多余；
4. 格式错误：数字与单位格式、标点符号、缩写书写不规范。

输出要求：
- 仅报告确有问题之处，不得修改没有问题的句子，也不得做无依据的风格改写；
- 每条修改对应一个句子，sentence_id 为句子的编号（[S1] 对应 1，[S2] 对应 2，依此类推）；
- original 必须原样摘录该句中被修改的片段（逐字一致，便于程序定位替换），suggestion 为修改后的对应文本；
- error_type 只能是：事实错误 / 术语错误 / 语法错误 / 格式错误；
- severity：high = 医学事实性错误（可能误导诊疗）；medium = 术语错误或明显语法错误；low = 格式与措辞建议；
- evidence_ids 为所引用证据的编号列表（[E1] 对应 1），无证据支持时留空；
- 若整个块都没有问题，返回空的 corrections 数组。"""


def review_prompt() -> str:
    """review.prompt：审校 system prompt（默认内置医学审校模板，可在设置页编辑）。"""
    value = str(get_setting("review.prompt", "") or "").strip()
    return value or DEFAULT_REVIEW_PROMPT


def embedding_provider() -> str:
    """embedding.provider：local（本地 BGE-M3）| openai（走 llm.base_url 的 /embeddings）。
    stub 为测试专用隐藏档（确定性假向量，不加载模型）。"""
    value = str(get_setting("embedding.provider", "local") or "local").strip().lower()
    return value if value in ("local", "openai", "stub") else "local"


def embedding_model() -> str:
    """embedding.model：local=HF 模型名（默认 BAAI/bge-m3）；openai=远端 embedding 模型名。"""
    return str(get_setting("embedding.model", "BAAI/bge-m3") or "BAAI/bge-m3")


# ---------- M5：导出（设计文档 §5.2⑥、§8） ----------


def first_line_indent_inches() -> float:
    """docx.first_line_indent：导出 docx 全文段落首行缩进（英寸，默认 0.5，兼容旧版）。"""
    value = get_setting("docx.first_line_indent", 0.5)
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.5


def output_dir() -> str:
    """output.dir：导出目录。空串 = 默认 projects/<doc_id>/exports/。"""
    return str(get_setting("output.dir", "") or "").strip()
