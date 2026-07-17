"""请求/响应模型、错误码全集、事件类型、错误 -> HTTP/中文文案 映射。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------- 错误码全集 ----------

class ErrorCode(str, Enum):
    LICENSE_NOT_FOUND = "LICENSE_NOT_FOUND"
    LICENSE_PENDING = "LICENSE_PENDING"
    LICENSE_SUSPENDED = "LICENSE_SUSPENDED"
    LICENSE_REVOKED = "LICENSE_REVOKED"
    LICENSE_EXPIRED = "LICENSE_EXPIRED"
    LICENSE_DEVICE_LIMIT_REACHED = "LICENSE_DEVICE_LIMIT_REACHED"
    DEVICE_NOT_REGISTERED = "DEVICE_NOT_REGISTERED"
    DEVICE_REVOKED = "DEVICE_REVOKED"
    DEVICE_MISMATCH = "DEVICE_MISMATCH"
    CLIENT_VERSION_TOO_OLD = "CLIENT_VERSION_TOO_OLD"
    INVALID_LICENSE_SIGNATURE = "INVALID_LICENSE_SIGNATURE"
    INVALID_REQUEST_SIGNATURE = "INVALID_REQUEST_SIGNATURE"
    SERVER_TIME_INVALID = "SERVER_TIME_INVALID"
    LICENSE_REFRESH_REQUIRED = "LICENSE_REFRESH_REQUIRED"
    SERVER_UNREACHABLE = "SERVER_UNREACHABLE"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    REPLAY_DETECTED = "REPLAY_DETECTED"
    RATE_LIMITED = "RATE_LIMITED"


# 错误 -> HTTP 状态码（员工 API）
ERROR_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.LICENSE_NOT_FOUND: 404,
    ErrorCode.LICENSE_PENDING: 403,
    ErrorCode.LICENSE_SUSPENDED: 403,
    ErrorCode.LICENSE_REVOKED: 403,
    ErrorCode.LICENSE_EXPIRED: 403,
    ErrorCode.LICENSE_DEVICE_LIMIT_REACHED: 403,
    ErrorCode.DEVICE_NOT_REGISTERED: 404,
    ErrorCode.DEVICE_REVOKED: 403,
    ErrorCode.DEVICE_MISMATCH: 403,
    ErrorCode.CLIENT_VERSION_TOO_OLD: 403,
    ErrorCode.INVALID_LICENSE_SIGNATURE: 403,
    ErrorCode.INVALID_REQUEST_SIGNATURE: 400,
    ErrorCode.SERVER_TIME_INVALID: 400,
    ErrorCode.LICENSE_REFRESH_REQUIRED: 409,
    ErrorCode.SERVER_UNREACHABLE: 503,
    ErrorCode.REQUEST_TIMEOUT: 408,
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.REPLAY_DETECTED: 400,
    ErrorCode.RATE_LIMITED: 429,
}

# 错误 -> 中文用户文案
ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.LICENSE_NOT_FOUND: "许可证密钥无效，请核对后重试",
    ErrorCode.LICENSE_PENDING: "许可证尚未激活，请先完成激活",
    ErrorCode.LICENSE_SUSPENDED: "许可证已被管理员暂停，请联系管理员",
    ErrorCode.LICENSE_REVOKED: "许可证已被管理员撤销",
    ErrorCode.LICENSE_EXPIRED: "许可证已到期，请联系管理员续期",
    ErrorCode.LICENSE_DEVICE_LIMIT_REACHED: "已达设备数量上限，请先在管理端解绑其他设备",
    ErrorCode.DEVICE_NOT_REGISTERED: "设备未注册，请先激活",
    ErrorCode.DEVICE_REVOKED: "设备已被解绑，请重新激活",
    ErrorCode.DEVICE_MISMATCH: "设备与许可证不匹配",
    ErrorCode.CLIENT_VERSION_TOO_OLD: "客户端版本过旧，请升级后重试",
    ErrorCode.INVALID_LICENSE_SIGNATURE: "许可证凭证签名校验失败",
    ErrorCode.INVALID_REQUEST_SIGNATURE: "请求签名校验失败",
    ErrorCode.SERVER_TIME_INVALID: "本机时间与服务器偏差过大，请校准系统时间",
    ErrorCode.LICENSE_REFRESH_REQUIRED: "许可证信息已更新，请刷新凭证",
    ErrorCode.SERVER_UNREACHABLE: "无法连接许可证服务器",
    ErrorCode.REQUEST_TIMEOUT: "请求超时，请稍后重试",
    ErrorCode.INTERNAL_SERVER_ERROR: "服务器内部错误，请稍后重试",
    ErrorCode.REPLAY_DETECTED: "检测到重放请求，已拒绝",
    ErrorCode.RATE_LIMITED: "请求过于频繁，请稍后再试",
}


def error_payload(code: ErrorCode, message: str | None = None) -> dict:
    """员工 API 统一错误体：{"success": false, "reason_code": ..., "message": ...}"""
    return {
        "success": False,
        "reason_code": code.value,
        "message": message or ERROR_MESSAGES[code],
    }


def error_http_status(code: ErrorCode) -> int:
    return ERROR_HTTP_STATUS.get(code, 400)


# ---------- 事件类型 ----------

class EventType(str, Enum):
    LICENSE_CREATED = "LICENSE_CREATED"
    ACTIVATION_SUCCEEDED = "ACTIVATION_SUCCEEDED"
    ACTIVATION_FAILED = "ACTIVATION_FAILED"
    HEARTBEAT_SUCCEEDED = "HEARTBEAT_SUCCEEDED"
    HEARTBEAT_FAILED = "HEARTBEAT_FAILED"
    LICENSE_RENEWED = "LICENSE_RENEWED"
    LICENSE_SUSPENDED = "LICENSE_SUSPENDED"
    LICENSE_RESUMED = "LICENSE_RESUMED"
    LICENSE_REVOKED = "LICENSE_REVOKED"
    DEVICE_UNBOUND = "DEVICE_UNBOUND"
    LICENSE_EXPIRED = "LICENSE_EXPIRED"


# ---------- 员工 API 请求 ----------

class ActivateRequest(BaseModel):
    license_key: str
    device_id: str = Field(min_length=8, max_length=128)
    device_name: str = ""
    platform: str = ""
    os_version: str = ""
    client_version: str = "0.0.0"
    session_id: str = ""
    nonce: str = Field(min_length=1, max_length=128)


class HeartbeatRequest(BaseModel):
    license_id: str
    device_id: str
    session_id: str = ""
    client_version: str = "0.0.0"
    license_version: int = 0
    timestamp: datetime
    nonce: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    license_id: str
    device_id: str
    client_version: str = "0.0.0"


# ---------- 签名凭证 ----------

class LicenseToken(BaseModel):
    schema_version: int = 1
    license_id: str
    device_id: str
    issued_at: str
    expires_at: Optional[str] = None
    features: list[str] = ["main"]
    license_version: int = 1


class CredentialResponse(BaseModel):
    success: bool = True
    license: LicenseToken
    signature: str


# ---------- 管理 API 请求 ----------

class CreateLicenseRequest(BaseModel):
    name: str = ""
    note: str = ""
    validity_mode: str = "duration"  # duration / fixed
    duration_days: Optional[int] = 365
    fixed_expires_at: Optional[datetime] = None
    max_devices: int = 1
    features: list[str] = ["main"]
    minimum_client_version: str = "0.0.0"


class RenewLicenseRequest(BaseModel):
    extend_days: Optional[int] = None
    new_expires_at: Optional[datetime] = None


class RevokeLicenseRequest(BaseModel):
    reason: str = ""


class PatchLicenseRequest(BaseModel):
    name: Optional[str] = None
    note: Optional[str] = None


class ServerConfigUpdate(BaseModel):
    employee_host: Optional[str] = None
    employee_port: Optional[int] = None
    lan_only: Optional[bool] = None
    log_level: Optional[str] = None


# ---------- 管理 API 响应（序列化辅助） ----------

def license_summary(lic, device_count: int = 0, last_heartbeat: datetime | None = None) -> dict[str, Any]:
    from .core.timeutil import to_iso_z

    return {
        "id": lic.id,
        "key_prefix": lic.license_key_prefix,
        "masked_key": f"AIREV-{lic.license_key_prefix}-****-****",
        "name": lic.name,
        "note": lic.note,
        "status": lic.status,
        "validity_mode": lic.validity_mode,
        "duration_seconds": lic.duration_seconds,
        "activated_at": to_iso_z(lic.activated_at),
        "expires_at": to_iso_z(lic.expires_at),
        "max_devices": lic.max_devices,
        "device_count": device_count,
        "features": lic.features,
        "minimum_client_version": lic.minimum_client_version,
        "license_version": lic.license_version,
        "created_at": to_iso_z(lic.created_at),
        "updated_at": to_iso_z(lic.updated_at),
        "suspended_at": to_iso_z(lic.suspended_at),
        "revoked_at": to_iso_z(lic.revoked_at),
        "revoked_reason": lic.revoked_reason,
        "last_heartbeat_at": to_iso_z(last_heartbeat),
    }


def device_summary(dev) -> dict[str, Any]:
    from .core.timeutil import to_iso_z

    return {
        "id": dev.id,
        "license_id": dev.license_id,
        "device_id": dev.device_id,
        "device_name": dev.device_name,
        "platform": dev.platform,
        "os_version": dev.os_version,
        "first_activated_at": to_iso_z(dev.first_activated_at),
        "last_seen_at": to_iso_z(dev.last_seen_at),
        "last_ip": dev.last_ip,
        "last_client_version": dev.last_client_version,
        "revoked": dev.revoked,
        "revoked_at": to_iso_z(dev.revoked_at),
    }


def event_summary(evt) -> dict[str, Any]:
    from .core.timeutil import to_iso_z

    return {
        "id": evt.id,
        "license_id": evt.license_id,
        "device_id": evt.device_id,
        "event_type": evt.event_type,
        "event_time": to_iso_z(evt.event_time),
        "ip_address": evt.ip_address,
        "client_version": evt.client_version,
        "result": evt.result,
        "reason_code": evt.reason_code,
        "metadata": evt.event_metadata,
    }
