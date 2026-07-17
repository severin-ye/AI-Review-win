"""管理操作 + 通用许可证状态助手。

文件顶部 record_event / resolve_effective_status / apply_lazy_expiry 是
activation、heartbeat 共用的助手（统一放这里避免循环导入）。
所有管理操作都会写审计事件；任何日志/响应不回完整 license key。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlmodel import Session, func, select

from ..core import timeutil
from ..crypto import (
    generate_license_key,
    hash_license_key,
    license_key_prefix,
    new_event_id,
    new_license_id,
)
from ..models.tables import Device, License, LicenseEvent, new_device_id  # noqa: F401
from ..schemas import EventType

logger = logging.getLogger("license_server.license_ops")

STATUS_PRIORITY = ("revoked", "suspended", "expired", "active", "pending")
_METADATA_VALUE_MAX = 200


# ---------- 通用助手 ----------

def _truncate_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """截断过长字符串，防止事件表膨胀；绝不接收完整 key/私钥/完整签名。"""
    if not metadata:
        return {}
    out: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str) and len(value) > _METADATA_VALUE_MAX:
            out[key] = value[:_METADATA_VALUE_MAX] + "…"
        else:
            out[key] = value
    return out


def record_event(
    session: Session,
    event_type: EventType,
    license_id: Optional[str] = None,
    device_id: Optional[str] = None,
    ip_address: str = "",
    client_version: str = "",
    result: str = "success",
    reason_code: str = "",
    metadata: dict[str, Any] | None = None,
) -> LicenseEvent:
    event = LicenseEvent(
        id=new_event_id(),
        license_id=license_id,
        device_id=device_id,
        event_type=event_type.value,
        event_time=timeutil.now(),
        ip_address=ip_address,
        client_version=client_version,
        result=result,
        reason_code=reason_code,
        event_metadata=_truncate_metadata(metadata),
    )
    session.add(event)
    return event


def resolve_effective_status(license: License, now: datetime | None = None) -> str:
    """动态状态判定：revoked > suspended > expired > active；pending 不变。"""
    now = timeutil.ensure_utc(now or timeutil.now())
    if license.status == "revoked":
        return "revoked"
    if license.status == "suspended":
        return "suspended"
    expires_at = timeutil.ensure_utc(license.expires_at)
    if expires_at is not None and now > expires_at:
        return "expired"
    return license.status


def apply_lazy_expiry(session: Session, license: License, now: datetime | None = None) -> str:
    """惰性过期落库：到期则 status=expired 并记 LICENSE_EXPIRED（仅一次），返回生效状态。"""
    now = now or timeutil.now()
    effective = resolve_effective_status(license, now)
    if (
        effective == "expired"
        and license.status in ("active", "pending")
        and license.expires_at is not None
    ):
        license.status = "expired"
        license.updated_at = now
        session.add(license)
        record_event(
            session,
            EventType.LICENSE_EXPIRED,
            license_id=license.id,
            reason_code="LICENSE_EXPIRED",
            metadata={"expires_at": timeutil.to_iso_z(license.expires_at)},
        )
    return effective


def get_license_by_key(session: Session, license_key: str) -> License | None:
    from ..crypto import normalize_license_key

    digest = hash_license_key(normalize_license_key(license_key))
    return session.exec(select(License).where(License.license_key_hash == digest)).first()


def bound_device_count(session: Session, license_id: str) -> int:
    return session.exec(
        select(func.count(Device.id)).where(
            Device.license_id == license_id, Device.revoked == False  # noqa: E712
        )
    ).one()


# ---------- 管理操作 ----------

def create_license(session: Session, req) -> dict:
    """创建许可证，返回完整 key（仅此一次可见）。"""
    key = generate_license_key()
    now = timeutil.now()
    validity_mode = req.validity_mode if req.validity_mode in ("duration", "fixed") else "duration"
    duration_seconds = None
    expires_at = None
    if validity_mode == "duration":
        days = req.duration_days if req.duration_days and req.duration_days > 0 else 365
        duration_seconds = days * 86400
    else:
        expires_at = timeutil.parse_iso(req.fixed_expires_at)
        if expires_at is None:
            expires_at = now + timedelta(days=365)
    license = License(
        id=new_license_id(),
        license_key_hash=hash_license_key(key),
        license_key_prefix=license_key_prefix(key),
        name=req.name or "",
        note=req.note or "",
        status="pending",
        validity_mode=validity_mode,
        duration_seconds=duration_seconds,
        expires_at=expires_at,
        max_devices=max(1, req.max_devices or 1),
        features=req.features or ["main"],
        minimum_client_version=req.minimum_client_version or "0.0.0",
        license_version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(license)
    record_event(
        session,
        EventType.LICENSE_CREATED,
        license_id=license.id,
        metadata={
            "name": license.name,
            "validity_mode": license.validity_mode,
            "max_devices": license.max_devices,
            "key_prefix": license.license_key_prefix,
        },
    )
    logger.info("创建许可证 %s（前缀 %s）", license.id, license.license_key_prefix)
    return {"license": license, "license_key": key}


def list_licenses(session: Session, search: str | None = None, status: str | None = None,
                  sort: str = "created_at", order: str = "desc") -> list[License]:
    stmt = select(License)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (License.name.like(like))
            | (License.note.like(like))
            | (License.license_key_prefix.like(f"{search}%"))
        )
    if status:
        stmt = stmt.where(License.status == status)
    sort_col = {
        "created_at": License.created_at,
        "expires_at": License.expires_at,
        "name": License.name,
        "status": License.status,
    }.get(sort, License.created_at)
    stmt = stmt.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    return list(session.exec(stmt).all())


def renew_license(session: Session, license: License, extend_days: int | None,
                  new_expires_at, ip_address: str = "") -> License:
    now = timeutil.ensure_utc(timeutil.now())
    expires_at = timeutil.ensure_utc(license.expires_at)
    activated_at = timeutil.ensure_utc(license.activated_at)
    old_expires_at = expires_at
    target = timeutil.parse_iso(new_expires_at)
    if target is not None:
        expires_at = target
        if license.validity_mode == "duration" and activated_at:
            license.duration_seconds = int((target - activated_at).total_seconds())
    elif extend_days:
        if expires_at is not None:
            base = expires_at if expires_at > now else now
            expires_at = base + timedelta(days=extend_days)
            if license.validity_mode == "duration" and activated_at:
                license.duration_seconds = int((expires_at - activated_at).total_seconds())
        elif license.duration_seconds is not None:
            license.duration_seconds += extend_days * 86400
        else:
            license.duration_seconds = extend_days * 86400
    license.expires_at = expires_at
    # 续期后若新截止在未来且当前为 expired，则恢复 active（曾被撤销/暂停的不动）
    if license.status == "expired" and (
        expires_at is None or expires_at > now
    ):
        license.status = "active"
    license.license_version += 1
    license.updated_at = now
    session.add(license)
    record_event(
        session,
        EventType.LICENSE_RENEWED,
        license_id=license.id,
        ip_address=ip_address,
        metadata={
            "old_expires_at": timeutil.to_iso_z(old_expires_at),
            "new_expires_at": timeutil.to_iso_z(license.expires_at),
            "license_version": license.license_version,
        },
    )
    return license


def suspend_license(session: Session, license: License, ip_address: str = "") -> License:
    now = timeutil.now()
    if license.status not in ("revoked",):
        license.status = "suspended"
        license.suspended_at = now
        license.updated_at = now
        session.add(license)
        record_event(session, EventType.LICENSE_SUSPENDED, license_id=license.id, ip_address=ip_address)
    return license


def resume_license(session: Session, license: License, ip_address: str = "") -> License:
    now = timeutil.now()
    if license.status == "suspended":
        # 恢复：到期判定交回动态逻辑
        license.status = "active" if license.activated_at else "pending"
        expires_at = timeutil.ensure_utc(license.expires_at)
        if expires_at is not None and now > expires_at:
            license.status = "expired"
        license.suspended_at = None
        license.updated_at = now
        session.add(license)
        record_event(session, EventType.LICENSE_RESUMED, license_id=license.id, ip_address=ip_address)
    return license


def revoke_license(session: Session, license: License, reason: str = "", ip_address: str = "") -> License:
    now = timeutil.now()
    license.status = "revoked"
    license.revoked_at = now
    license.revoked_reason = reason or None
    license.updated_at = now
    session.add(license)
    record_event(
        session,
        EventType.LICENSE_REVOKED,
        license_id=license.id,
        ip_address=ip_address,
        metadata={"reason": reason},
    )
    return license


def unbind_device(session: Session, license: License, device_row_id: str,
                  ip_address: str = "") -> Device | None:
    now = timeutil.now()
    device = session.get(Device, device_row_id)
    if device is None or device.license_id != license.id or device.revoked:
        return None
    device.revoked = True
    device.revoked_at = now
    device.updated_at = now
    session.add(device)
    record_event(
        session,
        EventType.DEVICE_UNBOUND,
        license_id=license.id,
        device_id=device.device_id,
        ip_address=ip_address,
        metadata={"device_name": device.device_name},
    )
    return device


def reset_devices(session: Session, license: License, ip_address: str = "") -> int:
    devices = list(
        session.exec(
            select(Device).where(Device.license_id == license.id, Device.revoked == False)  # noqa: E712
        ).all()
    )
    for device in devices:
        unbind_device(session, license, device.id, ip_address=ip_address)
    return len(devices)


def last_heartbeat_map(session: Session, license_ids: list[str]) -> dict[str, datetime]:
    """各许可证最近一次心跳成功时间。"""
    if not license_ids:
        return {}
    stmt = (
        select(LicenseEvent.license_id, func.max(LicenseEvent.event_time))
        .where(
            LicenseEvent.license_id.in_(license_ids),
            LicenseEvent.event_type == EventType.HEARTBEAT_SUCCEEDED.value,
        )
        .group_by(LicenseEvent.license_id)
    )
    return {lid: ts for lid, ts in session.exec(stmt).all()}
