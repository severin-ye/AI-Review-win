"""FastAPI 应用工厂：create_admin_app() / create_employee_app()。

- admin app：管理 API + 管理页，默认仅绑 127.0.0.1:8767
- employee app：员工激活/心跳/刷新 API，默认绑 0.0.0.0:8768
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import admin as admin_api
from .api import employee as employee_api
from .api.ratelimit import FixedWindowRateLimiter
from .core import timeutil
from .core.config import Settings, get_settings
from .core.db import init_db
from .core.keys import get_key_manager
from .version import __version__


class NullEmployeeController:
    """测试/嵌入式场景的占位控制器：仅记录期望状态，不操作真实监听。"""

    def __init__(self) -> None:
        self._running = True

    def employee_running(self) -> bool:
        return self._running

    def start_employee(self) -> None:
        self._running = True

    def stop_employee(self) -> None:
        self._running = False


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _lifespan(app: FastAPI, settings: Settings, with_rate_limiter: bool):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        init_db(settings)
        app.state.key_manager = get_key_manager(settings)
        if with_rate_limiter:
            app.state.rate_limiter = FixedWindowRateLimiter(settings.rate_limit_per_minute, 60)
        app.state.started_at = timeutil.now()
        yield

    return lifespan


def create_employee_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    _configure_logging(settings)
    app = FastAPI(
        title="AI-Review License Server (employee)",
        version=__version__,
    )
    app.router.lifespan_context = _lifespan(app, settings, with_rate_limiter=True)
    app.state.settings = settings
    app.include_router(employee_api.router)
    return app


def create_admin_app(settings: Settings | None = None, controller=None) -> FastAPI:
    settings = settings or get_settings()
    _configure_logging(settings)
    app = FastAPI(
        title="AI-Review License Server (admin)",
        version=__version__,
    )
    app.router.lifespan_context = _lifespan(app, settings, with_rate_limiter=False)
    app.state.settings = settings
    app.state.controller = controller or NullEmployeeController()
    app.include_router(admin_api.router)
    admin_api.register_admin_ui(app)
    return app
