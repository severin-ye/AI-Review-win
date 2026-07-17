"""员工 API：activate / heartbeat / refresh / ping。

所有 DB 多步写在一个请求事务内提交；内部异常不回堆栈，统一 500。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

from ..core.db import get_engine
from ..schemas import (
    ActivateRequest,
    ErrorCode,
    HeartbeatRequest,
    RefreshRequest,
    error_payload,
)
from ..services import activation, heartbeat as heartbeat_svc

logger = logging.getLogger("license_server.api.employee")

router = APIRouter(prefix="/api/v1")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def _run(request: Request, fn) -> JSONResponse:
    """统一事务包裹 + 异常兜底（不泄堆栈）。"""
    engine = get_engine(request.app.state.settings)
    try:
        with Session(engine) as session:
            status, payload = fn(session)
            session.commit()
        return JSONResponse(status_code=status, content=payload)
    except Exception:  # noqa: BLE001
        logger.exception("员工 API 内部错误")
        return JSONResponse(
            status_code=500,
            content=error_payload(ErrorCode.INTERNAL_SERVER_ERROR),
        )


@router.post("/licenses/activate")
def activate(req: ActivateRequest, request: Request) -> JSONResponse:
    ip = _client_ip(request)
    limiter = request.app.state.rate_limiter
    if not limiter.allow(ip):
        return JSONResponse(
            status_code=429,
            content=error_payload(ErrorCode.RATE_LIMITED),
        )
    return _run(request, lambda s: activation.activate(s, req, ip, request.app.state.key_manager))


@router.post("/licenses/heartbeat")
def heartbeat(req: HeartbeatRequest, request: Request) -> JSONResponse:
    ip = _client_ip(request)
    return _run(
        request,
        lambda s: heartbeat_svc.heartbeat(
            s, req, ip, request.app.state.key_manager, request.app.state.settings
        ),
    )


@router.post("/licenses/refresh")
def refresh(req: RefreshRequest, request: Request) -> JSONResponse:
    ip = _client_ip(request)
    return _run(request, lambda s: heartbeat_svc.refresh(s, req, ip, request.app.state.key_manager))


@router.get("/ping")
def ping(request: Request) -> dict:
    from ..core import timeutil
    from ..version import __version__

    km = request.app.state.key_manager
    return {
        "success": True,
        "server_time": timeutil.to_iso_z(timeutil.now()),
        "key_fingerprint": km.fingerprint,
        "dev": km.dev,
        "server_version": __version__,
    }
