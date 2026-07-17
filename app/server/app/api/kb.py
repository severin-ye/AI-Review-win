"""医学知识库接口：上传（异步线程索引 + job 事件）/ 列表 / 删除 / 重新索引。"""
from __future__ import annotations

import shutil
import threading
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.db import engine
from app.core.joblog import create_job, finish_job, make_emit
from app.models import Job, JobEvent, KbDocument
from app.rag.index import SUPPORTED_SUFFIXES, delete_kb_document, index_kb_document, kb_file_path

router = APIRouter(prefix="/kb", tags=["kb"])


def _kb_json(row: KbDocument) -> dict:
    return {
        "id": row.id,
        "filename": row.filename,
        "status": row.status,
        "chunk_count": row.chunk_count,
        "content_hash": row.content_hash[:12] if row.content_hash else "",
        "created_at": row.created_at.isoformat(),
    }


def _get_kb_or_404(session: Session, kb_document_id: str) -> KbDocument:
    row = session.get(KbDocument, kb_document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="知识库文档不存在")
    return row


def _start_index_job(kb_document_id: str) -> str:
    """创建 kb_index 任务并后台线程执行索引；进度写 job_events 供 SSE。"""
    job_id = create_job("kb_index", kb_document_id=kb_document_id)

    def run() -> None:
        try:
            index_kb_document(kb_document_id, emit=make_emit(job_id))
            finish_job(job_id, "done")
        except Exception:
            finish_job(job_id, "error")

    threading.Thread(target=run, daemon=True).start()
    return job_id


@router.get("/documents")
def list_kb_documents() -> list[dict]:
    with Session(engine) as session:
        rows = session.exec(select(KbDocument).order_by(KbDocument.created_at.desc())).all()
        return [_kb_json(r) for r in rows]


@router.post("/documents", status_code=201)
def upload_kb_document(file: UploadFile) -> dict:
    """上传参考文档（pdf/txt/csv/docx），落盘后异步线程索引，返回 job_id 供 SSE 订阅进度。"""
    filename = file.filename or "kb.txt"
    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 pdf / txt / csv / docx 文件")
    kb_id = uuid4().hex
    dest = kb_file_path(kb_id, suffix)
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    with Session(engine) as session:
        row = KbDocument(id=kb_id, filename=filename, status="indexing")
        session.add(row)
        session.commit()
    job_id = _start_index_job(kb_id)
    with Session(engine) as session:
        row = _get_kb_or_404(session, kb_id)
        return {**_kb_json(row), "job_id": job_id}


@router.post("/documents/{kb_document_id}/reindex")
def reindex_kb_document(kb_document_id: str) -> dict:
    """重新索引：内容 hash 未变时增量跳过（见 rag/index.py），变更则全量重建该文档 chunks。"""
    with Session(engine) as session:
        _get_kb_or_404(session, kb_document_id)
    job_id = _start_index_job(kb_document_id)
    return {"job_id": job_id, "id": kb_document_id}


@router.delete("/documents/{kb_document_id}")
def remove_kb_document(kb_document_id: str) -> dict:
    """删除文档：同步删 LanceDB chunks、重建 BM25、删落盘文件与 DB 行（含其索引任务记录）。"""
    with Session(engine) as session:
        _get_kb_or_404(session, kb_document_id)
        job_ids = session.exec(select(Job.id).where(Job.kb_document_id == kb_document_id)).all()
        if job_ids:
            session.exec(delete(JobEvent).where(JobEvent.job_id.in_(job_ids)))
        session.exec(delete(Job).where(Job.kb_document_id == kb_document_id))
        session.commit()
    delete_kb_document(kb_document_id)
    return {"ok": True}
