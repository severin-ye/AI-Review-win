"""激活服务：幂等、设备上限、模式 A/B 有效期、最低版本。

流程：key 存在（按哈希查）→ 状态（挂起/撤销/过期）→ 客户端版本 → 设备：
同 device_id 已绑定且未 revoked → 幂等成功（更新 last_seen，不占新额度）；
新设备且绑定数 ≥ max_devices → LICENSE_DEVICE_LIMIT_REACHED；否则绑定并签发凭证。
失败同样记 ACTIVATION_FAILED（带 reason_code）。
"""
from __future__ import annotations

from sqlmodel import Session, select

from ..core import timeutil
from ..core.keys import KeyManager
from ..crypto import version_gte
from ..models.tables import Device, new_device_id
from ..schemas import ActivateRequest, ErrorCode, EventType, error_payload
from .license_ops import (
    apply_lazy_expiry,
    bound_device_count,
    get_license_by_key,
    record_event,
)
from .token import issue_credential


def _fail(session: Session, code: ErrorCode, license_id=None, device_id=None,
          ip="", client_version="", metadata=None) -> tuple[int, dict]:
    record_event(
        session,
        EventType.ACTIVATION_FAILED,
        license_id=license_id,
        device_id=device_id,
        ip_address=ip,
        client_version=client_version,
        result="failure",
        reason_code=code.value,
        metadata=metadata,
    )
    from ..schemas import error_http_status

    return error_http_status(code), error_payload(code)


def activate(session: Session, req: ActivateRequest, ip_address: str,
             key_manager: KeyManager) -> tuple[int, dict]:
    now = timeutil.now()
    license = get_license_by_key(session, req.license_key)
    if license is None:
        return _fail(session, ErrorCode.LICENSE_NOT_FOUND, device_id=req.device_id,
                     ip=ip_address, client_version=req.client_version)

    effective = apply_lazy_expiry(session, license, now)
    if effective == "revoked":
        return _fail(session, ErrorCode.LICENSE_REVOKED, license.id, req.device_id,
                     ip_address, req.client_version)
    if effective == "suspended":
        return _fail(session, ErrorCode.LICENSE_SUSPENDED, license.id, req.device_id,
                     ip_address, req.client_version)
    if effective == "expired":
        return _fail(session, ErrorCode.LICENSE_EXPIRED, license.id, req.device_id,
                     ip_address, req.client_version)

    if not version_gte(req.client_version, license.minimum_client_version):
        return _fail(
            session, ErrorCode.CLIENT_VERSION_TOO_OLD, license.id, req.device_id,
            ip_address, req.client_version,
            metadata={"minimum_client_version": license.minimum_client_version},
        )

    # 设备：同 device_id 已绑定且未 revoked → 幂等成功
    device = session.exec(
        select(Device).where(Device.license_id == license.id, Device.device_id == req.device_id)
    ).first()
    if device is not None and device.revoked:
        return _fail(session, ErrorCode.DEVICE_REVOKED, license.id, req.device_id,
                     ip_address, req.client_version)

    first_activation = False
    if device is None:
        if bound_device_count(session, license.id) >= license.max_devices:
            return _fail(session, ErrorCode.LICENSE_DEVICE_LIMIT_REACHED, license.id,
                         req.device_id, ip_address, req.client_version,
                         metadata={"max_devices": license.max_devices})
        device = Device(
            id=new_device_id(),
            license_id=license.id,
            device_id=req.device_id,
            device_name=req.device_name,
            platform=req.platform,
            os_version=req.os_version,
            first_activated_at=now,
            last_seen_at=now,
            last_ip=ip_address,
            last_client_version=req.client_version,
            last_nonce=req.nonce or None,
            created_at=now,
            updated_at=now,
        )
        session.add(device)
        first_activation = license.activated_at is None

    # 首激活：模式 A 从此刻起算有效期；状态 pending -> active
    if first_activation:
        license.activated_at = now
        if license.validity_mode == "duration":
            duration = license.duration_seconds or 365 * 86400
            from datetime import timedelta

            license.expires_at = now + timedelta(seconds=duration)
        license.status = "active"
        license.updated_at = now
        session.add(license)

    # 幂等路径：更新 last_seen，不占用新额度
    device.last_seen_at = now
    device.last_ip = ip_address
    device.last_client_version = req.client_version
    if req.device_name:
        device.device_name = req.device_name
    if req.nonce:
        device.last_nonce = req.nonce
    device.updated_at = now
    session.add(device)

    credential = issue_credential(license, req.device_id, key_manager, now)
    record_event(
        session,
        EventType.ACTIVATION_SUCCEEDED,
        license_id=license.id,
        device_id=req.device_id,
        ip_address=ip_address,
        client_version=req.client_version,
        metadata={"session_id": req.session_id, "key_prefix": license.license_key_prefix},
    )
    return 200, {"success": True, **credential}
