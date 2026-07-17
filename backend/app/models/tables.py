"""SQLModel 表定义（对应设计文档第 6 节，M1 简化版，表先建全）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid4().hex


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=_uuid, primary_key=True)
    filename: str
    # 状态机：uploaded → parsing → segmenting → retrieving → reviewing → done / error
    status: str = "uploaded"
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # M5：最近一次导出结果（JSON：clean/marked 路径、adopted 数、exported_at、warnings）
    exports_json: Optional[str] = None


class Block(SQLModel, table=True):
    __tablename__ = "blocks"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    idx: int
    chapter: Optional[str] = None
    is_reference: bool = False  # 参考文献块（M2 起；默认不审校）
    text: str


class Sentence(SQLModel, table=True):
    __tablename__ = "sentences"

    id: Optional[int] = Field(default=None, primary_key=True)
    block_id: int = Field(foreign_key="blocks.id", index=True)
    idx: int
    text: str


class Query(SQLModel, table=True):
    """重写后的检索问题（每句 retrieve.query_count 条）"""
    __tablename__ = "queries"

    id: Optional[int] = Field(default=None, primary_key=True)
    sentence_id: int = Field(foreign_key="sentences.id", index=True)
    idx: int
    text: str


class Evidence(SQLModel, table=True):
    """3+3 证据：向量 / 关键词两路检索结果"""
    __tablename__ = "evidence"

    id: Optional[int] = Field(default=None, primary_key=True)
    sentence_id: int = Field(foreign_key="sentences.id", index=True)
    source: str  # vector | keyword
    chunk_text: str
    doc_name: str
    score: float = 0.0
    rank: int = 0


class Correction(SQLModel, table=True):
    __tablename__ = "corrections"

    id: Optional[int] = Field(default=None, primary_key=True)
    sentence_id: int = Field(foreign_key="sentences.id", index=True)
    original: str
    suggestion: str
    error_type: str = ""
    severity: str = ""
    explanation: str = ""
    evidence_ids: str = "[]"  # json
    decision: str = "pending"  # pending | accepted | rejected | custom
    custom_text: Optional[str] = None
    decided_at: Optional[datetime] = None


class KbDocument(SQLModel, table=True):
    __tablename__ = "kb_documents"

    id: str = Field(default_factory=_uuid, primary_key=True)
    filename: str
    content_hash: str = ""
    status: str = "uploaded"
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KbChunk(SQLModel, table=True):
    """知识库分块（向量后续外挂 LanceDB）"""
    __tablename__ = "kb_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    kb_document_id: str = Field(foreign_key="kb_documents.id", index=True)
    idx: int
    text: str


class Setting(SQLModel, table=True):
    __tablename__ = "settings"

    key: str = Field(primary_key=True)
    value: str = ""  # json


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: str = Field(default_factory=_uuid, primary_key=True)
    document_id: Optional[str] = Field(default=None, foreign_key="documents.id", index=True)
    kb_document_id: Optional[str] = Field(
        default=None, foreign_key="kb_documents.id", index=True
    )  # M3：知识库索引任务
    type: str = "pipeline"  # pipeline | kb_index | retrieve | review
    status: str = "pending"  # pending | running | done | error
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobEvent(SQLModel, table=True):
    """任务事件流水（SSE 回放来源）"""
    __tablename__ = "job_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="jobs.id", index=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    event: str
    data: str = "{}"  # json
