"""管理 API（仅 admin app，绑 127.0.0.1）+ 静态托管管理页。"""
from __future__ import annotations

import json
import logging
import socket
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session, func, select

from ..core import timeutil
from ..core.db import get_engine
from ..models.tables import Device, License, LicenseEvent
from ..schemas import (
    CreateLicenseRequest,
    EventType,
    PatchLicenseRequest,
    RenewLicenseRequest,
    RevokeLicenseRequest,
    ServerConfigUpdate,
    device_summary,
    event_summary,
    license_summary,
)
from ..services import license_ops

logger = logging.getLogger("license_server.api.admin")

router = APIRouter(prefix="/api/v1")
ADMIN_UI_DIR = Path(__file__).resolve().parent.parent / "admin_ui"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _lan_ip() -> str:
    """取本机局域网 IP（UDP connect 不实际发包）；失败退回 127.0.0.1。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _get_license_or_404(session: Session, license_id: str) -> License:
    license = session.get(License, license_id)
    if license is None:
        raise HTTPException(status_code=404, detail="许可证不存在")
    return license


def _run(request: Request, fn, commit: bool = True):
    engine = get_engine(request.app.state.settings)
    try:
        with Session(engine) as session:
            result = fn(session)
            if commit:
                session.commit()
        return result
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("管理 API 内部错误")
        raise HTTPException(status_code=500, detail="服务器内部错误")


# ---------- 许可证 ----------

@router.post("/admin/licenses")
def create_license(req: CreateLicenseRequest, request: Request) -> dict:
    def op(session: Session):
        result = license_ops.create_license(session, req)
        lic = result["license"]
        return {
            "success": True,
            "license_key": result["license_key"],  # 仅此一次返回完整 key
            "license": license_summary(lic),
        }

    return _run(request, op)


@router.get("/admin/licenses")
def list_licenses(request: Request, search: str | None = None, status: str | None = None,
                  sort: str = "created_at", order: str = "desc") -> dict:
    def op(session: Session):
        licenses = license_ops.list_licenses(session, search=search, status=status,
                                             sort=sort, order=order)
        hb = license_ops.last_heartbeat_map(session, [lic.id for lic in licenses])
        items = []
        for lic in licenses:
            count = license_ops.bound_device_count(session, lic.id)
            items.append(license_summary(lic, device_count=count,
                                         last_heartbeat=hb.get(lic.id)))
        return {"success": True, "items": items, "total": len(items)}

    return _run(request, op, commit=False)


@router.get("/admin/licenses/{license_id}")
def license_detail(license_id: str, request: Request) -> dict:
    def op(session: Session):
        lic = _get_license_or_404(session, license_id)
        devices = list(session.exec(
            select(Device).where(Device.license_id == lic.id)
        ).all())
        hb = license_ops.last_heartbeat_map(session, [lic.id])
        return {
            "success": True,
            "license": license_summary(lic, device_count=license_ops.bound_device_count(session, lic.id),
                                       last_heartbeat=hb.get(lic.id)),
            "devices": [device_summary(d) for d in devices],
        }

    return _run(request, op, commit=False)


@router.post("/admin/licenses/{license_id}/renew")
def renew_license(license_id: str, req: RenewLicenseRequest, request: Request) -> dict:
    def op(session: Session):
        lic = _get_license_or_404(session, license_id)
        if req.extend_days is None and req.new_expires_at is None:
            raise HTTPException(status_code=400, detail="需提供 extend_days 或 new_expires_at")
        license_ops.renew_license(session, lic, req.extend_days, req.new_expires_at,
                                  ip_address=_client_ip(request))
        return {"success": True, "license": license_summary(lic)}

    return _run(request, op)


@router.post("/admin/licenses/{license_id}/suspend")
def suspend_license(license_id: str, request: Request) -> dict:
    def op(session: Session):
        lic = _get_license_or_404(session, license_id)
        license_ops.suspend_license(session, lic, ip_address=_client_ip(request))
        return {"success": True, "license": license_summary(lic)}

    return _run(request, op)


@router.post("/admin/licenses/{license_id}/resume")
def resume_license(license_id: str, request: Request) -> dict:
    def op(session: Session):
        lic = _get_license_or_404(session, license_id)
        license_ops.resume_license(session, lic, ip_address=_client_ip(request))
        return {"success": True, "license": license_summary(lic)}

    return _run(request, op)


@router.post("/admin/licenses/{license_id}/revoke")
def revoke_license(license_id: str, req: RevokeLicenseRequest, request: Request) -> dict:
    def op(session: Session):
        lic = _get_license_or_404(session, license_id)
        license_ops.revoke_license(session, lic, req.reason, ip_address=_client_ip(request))
        return {"success": True, "license": license_summary(lic)}

    return _run(request, op)


@router.delete("/admin/licenses/{license_id}/devices/{device_row_id}")
def unbind_device(license_id: str, device_row_id: str, request: Request) -> dict:
    def op(session: Session):
        lic = _get_license_or_404(session, license_id)
        device = license_ops.unbind_device(session, lic, device_row_id,
                                           ip_address=_client_ip(request))
        if device is None:
            raise HTTPException(status_code=404, detail="设备不存在或已解绑")
        return {"success": True, "device": device_summary(device)}

    return _run(request, op)


@router.post("/admin/licenses/{license_id}/devices/reset")
def reset_devices(license_id: str, request: Request) -> dict:
    def op(session: Session):
        lic = _get_license_or_404(session, license_id)
        count = license_ops.reset_devices(session, lic, ip_address=_client_ip(request))
        return {"success": True, "unbound": count}

    return _run(request, op)


@router.patch("/admin/licenses/{license_id}")
def patch_license(license_id: str, req: PatchLicenseRequest, request: Request) -> dict:
    def op(session: Session):
        lic = _get_license_or_404(session, license_id)
        if req.name is not None:
            lic.name = req.name
        if req.note is not None:
            lic.note = req.note
        lic.updated_at = timeutil.now()
        session.add(lic)
        return {"success": True, "license": license_summary(lic)}

    return _run(request, op)


@router.get("/admin/licenses/{license_id}/events")
def license_events(license_id: str, request: Request, limit: int = 200) -> dict:
    def op(session: Session):
        _get_license_or_404(session, license_id)
        events = list(session.exec(
            select(LicenseEvent)
            .where(LicenseEvent.license_id == license_id)
            .order_by(LicenseEvent.event_time.desc())
            .limit(min(limit, 1000))
        ).all())
        return {"success": True, "items": [event_summary(e) for e in events]}

    return _run(request, op, commit=False)


# ---------- 服务器 ----------

def _load_runtime_config(request: Request) -> dict:
    path = request.app.state.settings.runtime_config_path
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _save_runtime_config(request: Request, config: dict) -> None:
    path = request.app.state.settings.runtime_config_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def _effective_server_config(request: Request) -> dict:
    settings = request.app.state.settings
    overrides = _load_runtime_config(request)
    lan_only = overrides.get("lan_only", False)
    employee_host = overrides.get("employee_host") or ("127.0.0.1" if lan_only else settings.employee_host)
    return {
        "admin_host": settings.admin_host,
        "admin_port": settings.admin_port,
        "employee_host": employee_host,
        "employee_port": overrides.get("employee_port") or settings.employee_port,
        "lan_only": lan_only,
        "log_level": overrides.get("log_level") or settings.log_level,
    }


@router.get("/admin/server/status")
def server_status(request: Request) -> dict:
    settings = request.app.state.settings
    controller = request.app.state.controller
    km = request.app.state.key_manager
    config = _effective_server_config(request)
    now = timeutil.now()
    window_start = now - timedelta(minutes=10)

    engine = get_engine(settings)
    with Session(engine) as session:
        active_clients = session.exec(
            select(func.count(func.distinct(LicenseEvent.device_id))).where(
                LicenseEvent.event_type == EventType.HEARTBEAT_SUCCEEDED.value,
                LicenseEvent.event_time >= window_start,
                LicenseEvent.device_id.is_not(None),
            )
        ).one()
        last_hb = session.exec(
            select(func.max(LicenseEvent.event_time)).where(
                LicenseEvent.event_type == EventType.HEARTBEAT_SUCCEEDED.value
            )
        ).one()

    lan_ip = _lan_ip()
    started_at = request.app.state.started_at
    return {
        "success": True,
        "employee_running": controller.employee_running(),
        "admin": {"host": settings.admin_host, "port": settings.admin_port},
        "employee": {
            "host": config["employee_host"],
            "port": config["employee_port"],
            "lan_only": config["lan_only"],
        },
        "lan_ip": lan_ip,
        "employee_url": f"http://{lan_ip}:{config['employee_port']}",
        "started_at": timeutil.to_iso_z(started_at),
        "uptime_seconds": int((now - started_at).total_seconds()) if started_at else 0,
        "active_clients_10m": active_clients,
        "last_heartbeat_at": timeutil.to_iso_z(last_hb),
        "dev": km.dev,
        "log_level": config["log_level"],
    }


@router.post("/admin/server/start")
def server_start(request: Request) -> dict:
    controller = request.app.state.controller
    controller.start_employee()
    return {"success": True, "employee_running": controller.employee_running()}


@router.post("/admin/server/stop")
def server_stop(request: Request) -> dict:
    controller = request.app.state.controller
    controller.stop_employee()
    return {"success": True, "employee_running": controller.employee_running()}


@router.get("/admin/server/config")
def get_server_config(request: Request) -> dict:
    return {"success": True, "config": _effective_server_config(request)}


@router.put("/admin/server/config")
def put_server_config(req: ServerConfigUpdate, request: Request) -> dict:
    config = _load_runtime_config(request)
    for field in ("employee_host", "employee_port", "lan_only", "log_level"):
        value = getattr(req, field)
        if value is not None:
            config[field] = value
    _save_runtime_config(request, config)
    return {"success": True, "config": _effective_server_config(request)}


@router.get("/admin/server/public-key")
def public_key(request: Request) -> dict:
    km = request.app.state.key_manager
    return {
        "success": True,
        "public_key_pem": km.public_pem,
        "fingerprint": km.fingerprint,
        "dev": km.dev,
        "dpapi_protected": km.dpapi_used,
    }


@router.post("/admin/server/regenerate-keys")
def regenerate_keys(request: Request) -> dict:
    km = request.app.state.key_manager
    km.regenerate()
    logger.warning("管理员重新生成了密钥对")
    return {
        "success": True,
        "public_key_pem": km.public_pem,
        "fingerprint": km.fingerprint,
        "dev": km.dev,
        "warning": "密钥对已重新生成，所有已签发凭证立即失效",
    }


@router.get("/ping")
def admin_ping(request: Request) -> dict:
    km = request.app.state.key_manager
    return {
        "success": True,
        "server_time": timeutil.to_iso_z(timeutil.now()),
        "key_fingerprint": km.fingerprint,
        "dev": km.dev,
    }


# ---------- 管理页静态托管 ----------

def register_admin_ui(app) -> None:
    from fastapi import APIRouter as _Router

    page_router = _Router()

    @page_router.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(ADMIN_UI_DIR / "index.html")

    app.include_router(page_router)
