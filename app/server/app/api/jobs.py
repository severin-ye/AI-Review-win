"""任务 SSE 事件流：从 job_events 表轮询回放，job 结束后发 done 关闭。"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.core.db import engine
from app.models import Job, JobEvent

router = APIRouter(prefix="/jobs", tags=["jobs"])

_POLL_INTERVAL = 0.5  # 秒
_MAX_SECONDS = 1800  # SSE 最长保活（兜底防悬挂）


def _fetch_events(job_id: str, after_id: int) -> list[JobEvent]:
    with Session(engine) as session:
        return list(
            session.exec(
                select(JobEvent)
                .where(JobEvent.job_id == job_id, JobEvent.id > after_id)
                .order_by(JobEvent.id)
            ).all()
        )


def _fetch_job_status(job_id: str) -> str | None:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        return job.status if job is not None else None


@router.get("/{job_id}")
def job_status(job_id: str) -> dict:
    """任务状态查询（轮询用；实时事件走下方 SSE）。"""
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {
            "id": job.id,
            "type": job.type,
            "status": job.status,
            "document_id": job.document_id,
            "kb_document_id": job.kb_document_id,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }


@router.get("/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    """SSE：先回放已有事件，再每 0.5s 轮询增量；job done/error 且事件冲刷完毕后发 done 关闭。"""
    if _fetch_job_status(job_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_stream():
        last_id = 0
        deadline = time.monotonic() + _MAX_SECONDS
        while True:
            rows = await asyncio.to_thread(_fetch_events, job_id, last_id)
            for row in rows:
                # data 列本身即 JSON 字符串，直接作为 SSE data 负载
                yield f"event: {row.event}\ndata: {row.data}\n\n"
                last_id = row.id
            status = await asyncio.to_thread(_fetch_job_status, job_id)
            if status in ("done", "error"):
                # 终态：事件已全部冲刷（jobs 写事件先于终态落库）
                yield f"event: done\ndata: {json.dumps({'status': status})}\n\n"
                return
            if time.monotonic() > deadline:
                yield f"event: timeout\ndata: {json.dumps({'status': status})}\n\n"
                return
            await asyncio.sleep(_POLL_INTERVAL)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
