"""核心流水线：① ingest（docx 解析）→ ② segment（SaT 分割分块）→ 后续里程碑扩展。"""
from app.pipeline.common import project_dir, set_document_status

__all__ = ["project_dir", "set_document_status"]
