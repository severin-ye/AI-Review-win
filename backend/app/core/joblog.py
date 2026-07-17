"""Job 与 job_events 的写侧辅助（kb 索引 / retrieve 共用，SSE 从 job_events 表回放）。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.core.db import engine
from app.models import Job, JobEvent


def create_job(
    job_type: str,
    document_id: str | None = None,
    kb_document_id: str | None = None,
) -> str:
    with Session(engine) as session:
        job = Job(
            document_id=document_id,
            kb_document_id=kb_document_id,
            type=job_type,
            status="running",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


def record_event(job_id: str, event: str, data: dict[str, Any]) -> None:
    with Session(engine) as session:
        session.add(
            JobEvent(job_id=job_id, event=event, data=json.dumps(data, ensure_ascii=False))
        )
        session.commit()


def finish_job(job_id: str, status: str) -> None:
    """status: done | error"""
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job is not None:
            job.status = status
            job.updated_at = datetime.utcnow()
            session.add(job)
            session.commit()


def make_emit(job_id: str):
    """生成 pipeline/rag 模块用的 emit(event, data) 回调。"""

    def emit(event: str, data: dict[str, Any]) -> None:
        record_event(job_id, event, data)

    return emit
