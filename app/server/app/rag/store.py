"""知识库底层存储：LanceDB 向量表 + BM25 关键词索引（pickle 落盘）。

- LanceDB：嵌入式向量库（设计文档 §3），目录 data/kb/lancedb/，表 kb_chunks：
  chunk_id / kb_document_id / idx / text / source_name / vector。
  （设计文档 §6 中 SQLite 的 kb_chunks 表在本实现中由 LanceDB 单一来源取代——text 一并入列，
  检索与重建 BM25 均不再需要回查 SQLite。）
- BM25：LangChain 组件 BM25Retriever（内部即 rank_bm25.BM25Okapi）+ jieba 分词
  （preprocess_func=jieba.lcut，调研笔记 §2）；索引变更后整体重建并 pickle 到 data/kb/bm25.pkl。
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import jieba
import pyarrow as pa
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from app.core.config import get_settings

TABLE_NAME = "kb_chunks"

_bm25_cache: tuple[float, BM25Retriever] | None = None  # (mtime, retriever) 进程内缓存


def kb_dir() -> Path:
    directory = get_settings().data_dir / "kb"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def bm25_path() -> Path:
    return kb_dir() / "bm25.pkl"


def _db():
    import lancedb

    return lancedb.connect(str(kb_dir() / "lancedb"))


def _table(dim: int | None = None):
    """打开 kb_chunks 表；不存在且给了 dim 时按维度建表。维度不匹配时删表重建（需重新索引）。"""
    db = _db()
    if TABLE_NAME in db.list_tables().tables:
        table = db.open_table(TABLE_NAME)
        if dim is not None:
            field_dim = table.schema.field("vector").type.list_size
            if field_dim != dim:
                # embedding 维度变更（如 stub↔BGE-M3 切换）：向量表删旧重建，需重新索引知识库
                db.drop_table(TABLE_NAME)
            else:
                return table
        else:
            return table
    if dim is None:
        return None
    schema = pa.schema(
        [
            pa.field("chunk_id", pa.string()),
            pa.field("kb_document_id", pa.string()),
            pa.field("idx", pa.int32()),
            pa.field("text", pa.string()),
            pa.field("source_name", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), dim)),
        ]
    )
    return db.create_table(TABLE_NAME, schema=schema)


def upsert_chunks(rows: list[dict[str, Any]], dim: int) -> int:
    """批量写入 chunk（含向量）；按 chunk_id 先删后加实现幂等 upsert。"""
    if not rows:
        return 0
    table = _table(dim=dim)
    ids = ", ".join(f"'{r['chunk_id']}'" for r in rows)
    table.delete(f"chunk_id IN ({ids})")
    table.add(rows)
    return len(rows)


def delete_chunks_for_document(kb_document_id: str) -> None:
    table = _table()
    if table is not None:
        table.delete(f"kb_document_id = '{kb_document_id}'")


def all_chunks() -> list[dict[str, Any]]:
    """全部 chunk 的元数据（不含向量），用于重建 BM25。"""
    table = _table()
    if table is None:
        return []
    return table.search().select(["chunk_id", "kb_document_id", "idx", "text", "source_name"]).to_list()


def count_chunks() -> int:
    table = _table()
    return table.count_rows() if table is not None else 0


def vector_search(query_vector: list[float], limit: int) -> list[dict[str, Any]]:
    """cosine 相似度检索（向量已归一化）。返回按距离升序的候选，含 _distance。"""
    table = _table()
    if table is None or table.count_rows() == 0:
        return []
    return (
        table.search(query_vector)
        .metric("cosine")
        .select(["chunk_id", "kb_document_id", "idx", "text", "source_name"])
        .limit(limit)
        .to_list()
    )


# ---------- BM25（BM25Retriever + jieba，pickle 落盘） ----------


def rebuild_bm25() -> int:
    """从 LanceDB 全量 chunk 重建 BM25 索引并 pickle 落盘。返回索引的 chunk 数。

    BM25Retriever 内含 _thread.RLock 无法整体 pickle，故只落可序列化状态
    （BM25Okapi vectorizer + docs），加载时重组 Retriever。
    """
    global _bm25_cache
    path = bm25_path()
    chunks = all_chunks()
    if not chunks:
        path.unlink(missing_ok=True)
        _bm25_cache = None
        return 0
    docs = [
        Document(
            page_content=c["text"],
            metadata={
                "chunk_id": c["chunk_id"],
                "kb_document_id": c["kb_document_id"],
                "source_name": c["source_name"],
            },
        )
        for c in chunks
    ]
    retriever = BM25Retriever.from_documents(docs, preprocess_func=jieba.lcut)
    with path.open("wb") as f:
        pickle.dump({"vectorizer": retriever.vectorizer, "docs": retriever.docs}, f)
    _bm25_cache = None  # 下次检索时按新 mtime 重载
    return len(docs)


def _load_bm25() -> BM25Retriever | None:
    global _bm25_cache
    path = bm25_path()
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _bm25_cache is not None and _bm25_cache[0] == mtime:
        return _bm25_cache[1]
    with path.open("rb") as f:
        state = pickle.load(f)  # 本应用自产文件：{vectorizer: BM25Okapi, docs: [Document]}
    retriever = BM25Retriever(
        vectorizer=state["vectorizer"], docs=state["docs"], preprocess_func=jieba.lcut
    )
    _bm25_cache = (mtime, retriever)
    return retriever


def bm25_search(query: str, limit: int) -> list[Document]:
    """jieba 分词 + BM25 检索，返回按相关度排序的 Document（metadata 含 chunk_id/source_name）。"""
    retriever = _load_bm25()
    if retriever is None:
        return []
    retriever.k = limit
    return retriever.invoke(query)


def reset_bm25_cache() -> None:
    """测试用：清进程内 BM25 缓存。"""
    global _bm25_cache
    _bm25_cache = None
