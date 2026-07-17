"""SQLite / SQLModel 引擎与初始化。"""
from __future__ import annotations

from sqlmodel import SQLModel, create_engine

from app.core.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    # 导入 models 以注册全部表结构后建表
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate()


def _migrate() -> None:
    """轻量迁移：为已存在的 dev 库补充后续里程碑新增列（create_all 不会改旧表）。"""
    with engine.begin() as conn:
        block_cols = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(blocks)").fetchall()
        }
        if "is_reference" not in block_cols:
            conn.exec_driver_sql(
                "ALTER TABLE blocks ADD COLUMN is_reference BOOLEAN NOT NULL DEFAULT 0"
            )
        job_cols = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(jobs)").fetchall()
        }
        if "kb_document_id" not in job_cols:
            # M3：知识库索引任务关联（外键仅声明，SQLite 旧表无法补 FK 约束，不影响使用）
            conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN kb_document_id VARCHAR")
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_jobs_kb_document_id ON jobs (kb_document_id)"
            )
        doc_cols = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(documents)").fetchall()
        }
        if "exports_json" not in doc_cols:
            # M5：导出产物路径与 adopted 计数（JSON）
            conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN exports_json VARCHAR")
