"""心跳 / 刷新服务。

心跳校验顺序：
  1. 时间戳与服务器时差 > 300s → SERVER_TIME_INVALID
  2. 许可证存在性 / 设备注册 / 设备归属 / 设备解绑
  3. nonce 与该 (license, device) 上次相同 → REPLAY_DETECTED（400）
  4. 状态优先级 revoked > suspended > expired > active；pending → LICENSE_PENDING
业务状态响应（revoked/suspended/expired/active）为 200 + 对响应体 canonical 的签名；
请求级失败为 4xx + {"success": false, ...}。成功/失败均记事件（metadata 截断）。
"""
from __future__ import annotations

from sqlmodel import Session, select

from ..core import timeutil
from ..core.config import Settings
from ..core.keys import KeyManager
from ..models.tables import Device, License
from ..schemas import (
    ErrorCode,
    EventType,
    HeartbeatRequest,
    RefreshRequest,
    error_http_status,
    error_payload,
)
from .license_ops import apply_lazy_expiry, record_event
from .token import issue_credential, sign_response


def _fail(session: Session, event_type: EventType, code: ErrorCode, license_id=None,
          device_id=None, ip="", client_version="", metadata=None) -> tuple[int, dict]:
    record_event(
        session,
        event_type,
        license_id=license_id,
        device_id=device_id,
        ip_address=ip,
        client_version=client_version,
        result="failure",
        reason_code=code.value,
        metadata=metadata,
    )
    return error_http_status(code), error_payload(code)


def _lookup_device(session: Session, license_id: str, device_id: str) -> Device | None:
    return session.exec(
        select(Device).where(Device.license_id == license_id, Device.device_id == device_id)
    ).first()


def _device_error(session: Session, req, ip: str, event_type: EventType) -> tuple[int, dict] | None:
    """设备链校验：存在（全局）→ 归属 → 未解绑。无问题返回 None。"""
    any_device = session.exec(select(Device).where(Device.device_id == req.device_id)).first()
    if any_device is None:
        return _fail(session, event_type, ErrorCode.DEVICE_NOT_REGISTERED,
                     req.license_id, req.device_id, ip, req.client_version)
    if any_device.license_id != req.license_id:
        return _fail(session, event_type, ErrorCode.DEVICE_MISMATCH,
                     req.license_id, req.device_id, ip, req.client_version)
    if any_device.revoked:
        return _fail(session, event_type, ErrorCode.DEVICE_REVOKED,
                     req.license_id, req.device_id, ip, req.client_version)
    return None


def heartbeat(session: Session, req: HeartbeatRequest, ip_address: str,
              key_manager: KeyManager, settings: Settings) -> tuple[int, dict]:
    now = timeutil.now()
    meta = {"session_id": req.session_id}

    # 1. 时间戳偏差
    client_ts = timeutil.parse_iso(req.timestamp)
    if client_ts is None or timeutil.skew_exceeds(client_ts, now, settings.timestamp_tolerance_seconds):
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.SERVER_TIME_INVALID,
                     req.license_id, req.device_id, ip_address, req.client_version, meta)

    # 2. 许可证与设备
    license = session.get(License, req.license_id)
    if license is None:
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.LICENSE_NOT_FOUND,
                     req.license_id, req.device_id, ip_address, req.client_version, meta)
    device_error = _device_error(session, req, ip_address, EventType.HEARTBEAT_FAILED)
    if device_error is not None:
        return device_error
    device = _lookup_device(session, req.license_id, req.device_id)

    # 3. 防重放：nonce 与上次相同 → 拒绝
    if device.last_nonce is not None and req.nonce == device.last_nonce:
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.REPLAY_DETECTED,
                     req.license_id, req.device_id, ip_address, req.client_version, meta)
    device.last_nonce = req.nonce

    # 4. 状态
    effective = apply_lazy_expiry(session, license, now)
    server_time = timeutil.to_iso_z(now)

    if effective == "pending":
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.LICENSE_PENDING,
                     req.license_id, req.device_id, ip_address, req.client_version, meta)

    if effective in ("revoked", "suspended", "expired"):
        code = {
            "revoked": ErrorCode.LICENSE_REVOKED,
            "suspended": ErrorCode.LICENSE_SUSPENDED,
            "expired": ErrorCode.LICENSE_EXPIRED,
        }[effective]
        record_event(
            session,
            EventType.HEARTBEAT_SUCCEEDED,
            license_id=license.id,
            device_id=req.device_id,
            ip_address=ip_address,
            client_version=req.client_version,
            result="success",
            reason_code=code.value,
            metadata=meta,
        )
        body = {
            "status": effective,
            "reason_code": code.value,
            "message": {
                "revoked": "许可证已被管理员撤销",
                "suspended": "许可证已被管理员暂停",
                "expired": "许可证已到期，请联系管理员续期",
            }[effective],
            "server_time": server_time,
        }
        return 200, sign_response(body, key_manager)

    # active
    device.last_seen_at = now
    device.last_ip = ip_address
    device.last_client_version = req.client_version
    device.updated_at = now
    session.add(device)
    refresh_required = license.license_version > (req.license_version or 0)
    record_event(
        session,
        EventType.HEARTBEAT_SUCCEEDED,
        license_id=license.id,
        device_id=req.device_id,
        ip_address=ip_address,
        client_version=req.client_version,
        metadata={**meta, "refresh_required": refresh_required},
    )
    body = {
        "status": "active",
        "server_time": server_time,
        "expires_at": timeutil.to_iso_z(license.expires_at),
        "license_version": license.license_version,
        "next_heartbeat_seconds": settings.heartbeat_interval_seconds,
    }
    if refresh_required:
        body["refresh_required"] = True
    return 200, sign_response(body, key_manager)


def refresh(session: Session, req: RefreshRequest, ip_address: str,
            key_manager: KeyManager) -> tuple[int, dict]:
    """刷新凭证：同心跳的状态校验；active 则签发新凭证。"""
    now = timeutil.now()
    license = session.get(License, req.license_id)
    if license is None:
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.LICENSE_NOT_FOUND,
                     req.license_id, req.device_id, ip_address, req.client_version)
    device_error = _device_error(session, req, ip_address, EventType.HEARTBEAT_FAILED)
    if device_error is not None:
        return device_error

    effective = apply_lazy_expiry(session, license, now)
    if effective == "pending":
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.LICENSE_PENDING,
                     req.license_id, req.device_id, ip_address, req.client_version)
    if effective == "revoked":
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.LICENSE_REVOKED,
                     req.license_id, req.device_id, ip_address, req.client_version)
    if effective == "suspended":
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.LICENSE_SUSPENDED,
                     req.license_id, req.device_id, ip_address, req.client_version)
    if effective == "expired":
        return _fail(session, EventType.HEARTBEAT_FAILED, ErrorCode.LICENSE_EXPIRED,
                     req.license_id, req.device_id, ip_address, req.client_version)

    device = _lookup_device(session, req.license_id, req.device_id)
    device.last_seen_at = now
    device.last_ip = ip_address
    device.last_client_version = req.client_version
    device.updated_at = now
    session.add(device)

    credential = issue_credential(license, req.device_id, key_manager, now)
    record_event(
        session,
        EventType.HEARTBEAT_SUCCEEDED,
        license_id=license.id,
        device_id=req.device_id,
        ip_address=ip_address,
        client_version=req.client_version,
        metadata={"action": "refresh"},
    )
    return 200, {"success": True, **credential}
