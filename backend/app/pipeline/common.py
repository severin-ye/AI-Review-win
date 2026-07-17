"""pipeline 共用工具：项目目录与文档状态推进。"""
from __future__ import annotations

from pathlib import Path

from sqlmodel import Session

from app.core.config import get_settings
from app.core.db import engine
from app.models import Document


def project_dir(doc_id: str) -> Path:
    """projects/<doc_id>/ 目录（不存在则创建）。"""
    directory = get_settings().data_dir / "projects" / doc_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def set_document_status(doc_id: str, status: str, error: str | None = None) -> None:
    """推进 documents 状态机；error=None 时清空错误字段。"""
    with Session(engine) as session:
        doc = session.get(Document, doc_id)
        if doc is None:
            raise KeyError(f"文档不存在: {doc_id}")
        doc.status = status
        doc.error = error
        session.add(doc)
        session.commit()
