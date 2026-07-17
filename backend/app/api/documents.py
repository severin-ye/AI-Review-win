"""文档接口：上传 / 列表 / 运行流水线（M2: ingest+segment）/ 详情 / parsed.md / 删除 / M3 检索 / M4 审校。"""
from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.db import engine
from app.core.joblog import create_job, finish_job, make_emit, record_event
from app.core.user_settings import llm_config, retrieve_enabled, review_references
from app.llm.client import LLMNotConfiguredError
from app.models import (
    Block,
    Correction,
    Document,
    Evidence,
    Job,
    JobEvent,
    Query,
    Sentence,
)
from app.pipeline.common import project_dir, set_document_status
from app.pipeline.export import EXPORTABLE_STATUSES, export_document, list_exports
from app.pipeline.ingest import ingest_document
from app.pipeline.review import RETRYABLE_STATUSES, review_document
from app.pipeline.segment import segment_document
from app.rag import store as rag_store
from app.rag.retrieve import PLACEHOLDER_RE, retrieve_document

router = APIRouter(prefix="/documents", tags=["documents"])


def _doc_json(doc: Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "error": doc.error,
        "created_at": doc.created_at.isoformat(),
    }


def _get_doc_or_404(session: Session, document_id: str) -> Document:
    doc = session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


def _parse_evidence_ids(raw: str) -> list:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


@router.get("")
def list_documents() -> list[dict]:
    with Session(engine) as session:
        docs = session.exec(select(Document).order_by(Document.created_at.desc())).all()
        return [_doc_json(d) for d in docs]


@router.post("", status_code=201)
def upload_document(file: UploadFile) -> dict:
    filename = file.filename or "document.docx"
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件")
    doc_id = uuid4().hex
    dest = project_dir(doc_id) / "original.docx"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    with Session(engine) as session:
        doc = Document(id=doc_id, filename=filename, status="uploaded")
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return _doc_json(doc)


@router.post("/{document_id}/run")
def run_pipeline(document_id: str) -> dict:
    """同步执行 M2 流水线（ingest + segment），可重复运行（重跑自动清理旧 blocks/sentences）。"""
    with Session(engine) as session:
        _get_doc_or_404(session, document_id)
        job = Job(document_id=document_id, type="pipeline", status="running")
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    def record_event(event: str, data: dict) -> None:
        with Session(engine) as session:
            session.add(
                JobEvent(job_id=job_id, event=event, data=json.dumps(data, ensure_ascii=False))
            )
            session.commit()

    def finish_job(status: str) -> None:
        with Session(engine) as session:
            row = session.get(Job, job_id)
            if row is not None:
                row.status = status
                row.updated_at = datetime.utcnow()
                session.add(row)
                session.commit()

    try:
        record_event("start", {"stage": "ingest"})
        ingest_result = ingest_document(document_id)
        record_event("stage_done", {"stage": "ingest", **ingest_result})

        record_event("start", {"stage": "segment"})
        segment_result = segment_document(document_id)
        record_event("stage_done", {"stage": "segment", **segment_result})

        record_event("done", {})
        finish_job("done")
    except Exception as exc:
        record_event("error", {"message": str(exc)})
        finish_job("error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        return {
            "job_id": job_id,
            "status": doc.status,
            "blocks": segment_result["blocks"],
            "sentences": segment_result["sentences"],
            "segmenter": segment_result["segmenter"],
        }


@router.get("/{document_id}/detail")
def document_detail(document_id: str) -> dict:
    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        blocks = session.exec(
            select(Block).where(Block.document_id == document_id).order_by(Block.idx)
        ).all()
        result_blocks = []
        for block in blocks:
            sentences = session.exec(
                select(Sentence).where(Sentence.block_id == block.id).order_by(Sentence.idx)
            ).all()
            result_sentences = []
            for s in sentences:
                corrections = session.exec(
                    select(Correction).where(Correction.sentence_id == s.id).order_by(Correction.id)
                ).all()
                evidences = session.exec(
                    select(Evidence)
                    .where(Evidence.sentence_id == s.id)
                    .order_by(Evidence.score.desc(), Evidence.id)
                ).all()
                result_sentences.append(
                    {
                        "id": s.id,
                        "idx": s.idx,
                        "text": s.text,
                        "corrections": [
                            {
                                "id": c.id,
                                "original": c.original,
                                "suggestion": c.suggestion,
                                "error_type": c.error_type,
                                "severity": c.severity,
                                "explanation": c.explanation,
                                "evidence_ids": _parse_evidence_ids(c.evidence_ids),
                                "decision": c.decision,
                                "custom_text": c.custom_text,
                                "decided_at": c.decided_at.isoformat() if c.decided_at else None,
                            }
                            for c in corrections
                        ],
                        "evidence": [
                            {
                                "id": e.id,
                                "source": e.source,
                                "chunk_text": e.chunk_text,
                                "doc_name": e.doc_name,
                                "score": e.score,
                                "rank": e.rank,
                            }
                            for e in evidences
                        ],
                    }
                )
            result_blocks.append(
                {
                    "id": block.id,
                    "idx": block.idx,
                    "chapter": block.chapter,
                    "is_reference": block.is_reference,
                    "text": block.text,
                    "sentences": result_sentences,
                }
            )
        return {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "error": doc.error,
            "blocks": result_blocks,
        }


@router.get("/{document_id}/parsed", response_class=PlainTextResponse)
def document_parsed(document_id: str) -> str:
    with Session(engine) as session:
        _get_doc_or_404(session, document_id)
    parsed_path = project_dir(document_id) / "parsed.md"
    if not parsed_path.exists():
        raise HTTPException(status_code=404, detail="parsed.md 尚未生成，请先运行解析")
    return parsed_path.read_text(encoding="utf-8")


@router.delete("/{document_id}")
def delete_document(document_id: str) -> dict:
    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        block_ids = [
            b.id for b in session.exec(select(Block).where(Block.document_id == document_id)).all()
        ]
        if block_ids:
            sentence_ids = session.exec(
                select(Sentence.id).where(Sentence.block_id.in_(block_ids))
            ).all()
            if sentence_ids:
                session.exec(delete(Query).where(Query.sentence_id.in_(sentence_ids)))
                session.exec(delete(Evidence).where(Evidence.sentence_id.in_(sentence_ids)))
                session.exec(delete(Correction).where(Correction.sentence_id.in_(sentence_ids)))
            session.exec(delete(Sentence).where(Sentence.block_id.in_(block_ids)))
        session.exec(delete(Block).where(Block.document_id == document_id))
        job_ids = session.exec(select(Job.id).where(Job.document_id == document_id)).all()
        if job_ids:
            session.exec(delete(JobEvent).where(JobEvent.job_id.in_(job_ids)))
        session.exec(delete(Job).where(Job.document_id == document_id))
        session.delete(doc)
        session.commit()
    shutil.rmtree(project_dir(document_id), ignore_errors=True)
    return {"ok": True}


@router.post("/{document_id}/retrieve")
def retrieve_document_evidence(document_id: str) -> dict:
    """M3 检索：对全文档待审校句子执行 查询重写 + 3+3 混合检索（同步执行 + jobs 记录）。

    状态机：segmented → retrieving → retrieved（可重跑，自动清旧 queries/evidence）。
    """
    if not retrieve_enabled():
        raise HTTPException(status_code=400, detail="检索已在设置中关闭（retrieve.enabled=false）")
    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        if doc.status not in ("segmented", "retrieved", "failed"):
            raise HTTPException(
                status_code=400, detail=f"当前状态 {doc.status} 不能检索，请先完成解析分句"
            )
    if rag_store.count_chunks() == 0:
        raise HTTPException(status_code=400, detail="知识库为空，请先在知识库页上传并索引参考文档")

    job_id = create_job("retrieve", document_id=document_id)
    try:
        set_document_status(document_id, "retrieving")
        result = retrieve_document(document_id, emit=make_emit(job_id))
        set_document_status(document_id, "retrieved")
        finish_job(job_id, "done")
    except Exception as exc:
        record_event(job_id, "error", {"message": str(exc)})
        finish_job(job_id, "error")
        set_document_status(document_id, "failed", str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"job_id": job_id, "status": "retrieved", **result}


@router.get("/{document_id}/evidence")
def document_evidence(document_id: str) -> dict:
    """按 block→sentence 分组返回每句的重写问题（queries）与 3+3 证据（evidence）。"""
    include_references = review_references()
    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        blocks = session.exec(
            select(Block).where(Block.document_id == document_id).order_by(Block.idx)
        ).all()
        result_blocks = []
        for block in blocks:
            block_skipped = block.is_reference and not include_references
            sentences = session.exec(
                select(Sentence).where(Sentence.block_id == block.id).order_by(Sentence.idx)
            ).all()
            result_sentences = []
            for s in sentences:
                queries = session.exec(
                    select(Query).where(Query.sentence_id == s.id).order_by(Query.idx)
                ).all()
                evidences = session.exec(
                    select(Evidence)
                    .where(Evidence.sentence_id == s.id)
                    .order_by(Evidence.score.desc())
                ).all()
                result_sentences.append(
                    {
                        "id": s.id,
                        "idx": s.idx,
                        "text": s.text,
                        "skipped": block_skipped or PLACEHOLDER_RE.match(s.text) is not None,
                        "queries": [{"id": q.id, "idx": q.idx, "text": q.text} for q in queries],
                        "evidence": [
                            {
                                "id": e.id,
                                "source": e.source,
                                "chunk_text": e.chunk_text,
                                "doc_name": e.doc_name,
                                "score": e.score,
                                "rank": e.rank,
                            }
                            for e in evidences
                        ],
                    }
                )
            result_blocks.append(
                {
                    "id": block.id,
                    "idx": block.idx,
                    "chapter": block.chapter,
                    "is_reference": block.is_reference,
                    "sentences": result_sentences,
                }
            )
        return {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "blocks": result_blocks,
        }


@router.post("/{document_id}/export")
def export_document_api(document_id: str) -> dict:
    """M5 导出：同步生成双版本 docx（清洁版 _审校修订1_ / 留痕版 _审校修订2_）。

    前置状态 pending_manual / manual_done / done；无 accepted/custom 决定时导出原文
    （adopted=0）。产物路径与 adopted 数记 documents.exports_json 与 job_events。
    """
    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        if doc.status not in EXPORTABLE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"当前状态 {doc.status} 不能导出，请先完成人工审校",
            )
    job_id = create_job("export", document_id=document_id)
    try:
        result = export_document(document_id, emit=make_emit(job_id))
        finish_job(job_id, "done")
    except Exception as exc:
        finish_job(job_id, "error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"job_id": job_id, **result}


@router.get("/{document_id}/exports")
def list_document_exports(document_id: str) -> dict:
    """列出最近一次的导出产物（清洁版 kind=1 / 留痕版 kind=2，含存在性与大小）。"""
    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        adopted = None
        if doc.exports_json:
            try:
                adopted = json.loads(doc.exports_json).get("adopted")
            except json.JSONDecodeError:
                adopted = None
        return {"exports": list_exports(doc), "adopted": adopted}


@router.get("/{document_id}/exports/{kind}")
def download_document_export(document_id: str, kind: int) -> FileResponse:
    """下载导出产物文件（kind=1 清洁版 / 2 留痕版）。"""
    if kind not in (1, 2):
        raise HTTPException(status_code=404, detail="kind 只能是 1（清洁版）或 2（留痕版）")
    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        item = next((e for e in list_exports(doc) if e["kind"] == kind), None)
    if item is None or not item["exists"]:
        raise HTTPException(status_code=404, detail="导出文件不存在，请先执行导出")
    return FileResponse(
        item["path"],
        filename=item["name"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/{document_id}/review")
def review_document_api(document_id: str, force: bool = False) -> dict:
    """M4 审校：后台线程执行 LLM 结构化审校，进度经 /api/jobs/{job_id}/events（SSE）推送。

    状态机：segmented/retrieved/pending_manual/manual_done/failed(重试) → reviewing →
    pending_manual（无 pending 决定时直接 manual_done）；失败 → failed 并记录原因。
    可重跑：默认保留已人工决定项，force=true 全清重审。LLM 未配置 → 400，数据与状态均不变。
    """
    with Session(engine) as session:
        doc = _get_doc_or_404(session, document_id)
        if doc.status not in RETRYABLE_STATUSES:
            raise HTTPException(
                status_code=400, detail=f"当前状态 {doc.status} 不能审校，请先完成解析分句"
            )
    try:
        cfg = llm_config()
        missing = [k for k in ("base_url", "api_key", "model") if not cfg[k]]
        if missing:
            raise LLMNotConfiguredError(f"未配置 LLM（缺少 {', '.join(missing)}）")
    except LLMNotConfiguredError as exc:
        raise HTTPException(
            status_code=400, detail=f"{exc}，请到设置页填写 llm.base_url / llm.api_key / llm.model"
        ) from exc

    job_id = create_job("review", document_id=document_id)

    def work() -> None:
        try:
            review_document(document_id, emit=make_emit(job_id), force=force)
            finish_job(job_id, "done")
        except Exception as exc:
            record_event(job_id, "error", {"message": str(exc)})
            finish_job(job_id, "error")

    threading.Thread(target=work, daemon=True).start()
    return {"job_id": job_id, "status": "reviewing"}
