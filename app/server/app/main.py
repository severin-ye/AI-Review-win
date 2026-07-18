"""FastAPI 应用入口：uvicorn app.main:app"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.api import corrections, documents, health, jobs, kb, models as models_api
from app.api import settings as settings_api
from app.core.config import get_settings
from app.core.db import engine, init_db
from app.models import Document, Job, KbDocument

# 进程中断（重启/崩溃）后会残留的瞬态状态：后台线程已死，永不自愈，启动时统一收敛为 failed
_DOC_TRANSIENT_STATUSES = ("reviewing", "retrieving")
_KB_TRANSIENT_STATUSES = ("indexing",)


def _sweep_interrupted_state() -> None:
    """启动清理：running jobs → error；瞬态文档/知识库状态 → failed（前端据此显示失败而非一直转圈）。"""
    with Session(engine) as session:
        interrupted = False
        for job in session.exec(select(Job).where(Job.status == "running")).all():
            job.status = "error"
            job.updated_at = datetime.utcnow()
            session.add(job)
            interrupted = True
        for doc in session.exec(
            select(Document).where(Document.status.in_(_DOC_TRANSIENT_STATUSES))
        ).all():
            doc.status = "failed"
            doc.error = "任务中断：后端服务已重启，请重新执行该操作"
            session.add(doc)
            interrupted = True
        for kb_doc in session.exec(
            select(KbDocument).where(KbDocument.status.in_(_KB_TRANSIENT_STATUSES))
        ).all():
            kb_doc.status = "failed"
            session.add(kb_doc)
            interrupted = True
        if interrupted:
            session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动时初始化 SQLite（数据目录自动创建，见 core.config / core.db）
    init_db()
    _sweep_interrupted_state()
    yield


app = FastAPI(title="句读 Caret Backend", version=get_settings().version, lifespan=lifespan)

# 仅允许本地渲染层来源（Electron dev server / 任意 localhost 端口）
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(corrections.router, prefix="/api")
app.include_router(kb.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(models_api.router, prefix="/api")
