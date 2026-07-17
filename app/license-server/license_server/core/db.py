"""SQLModel engine 与建表。

engine 按数据目录惰性创建并缓存；测试切换 AI_REVIEW_LICENSE_DATA_DIR 后调用
reset_engine() 使下一个 app 使用新目录。
"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlmodel import SQLModel, create_engine

from .config import Settings, get_settings

logger = logging.getLogger("license_server.db")

_engine = None
_engine_db_path: Path | None = None


def get_engine(settings: Settings | None = None):
    global _engine, _engine_db_path
    settings = settings or get_settings()
    db_path = settings.db_path
    if _engine is None or _engine_db_path != db_path:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        _engine_db_path = db_path
    return _engine


def init_db(settings: Settings | None = None) -> None:
    # 确保表模型已注册
    from ..models import tables  # noqa: F401

    engine = get_engine(settings)
    SQLModel.metadata.create_all(engine)
    logger.info("数据库已就绪: %s", engine.url)


def reset_engine() -> None:
    """丢弃缓存 engine（测试隔离用）。"""
    global _engine, _engine_db_path
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_db_path = None
