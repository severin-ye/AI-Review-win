"""数据库表：License / Device / LicenseEvent。

全部时间 UTC 存储；features 与事件 metadata 为 JSON 列。
事件 metadata 严禁包含完整 license key、私钥、完整签名。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from ..core import timeutil


def _utcnow() -> datetime:
    return timeutil.now()


class License(SQLModel, table=True):
    __tablename__ = "licenses"

    id: str = Field(primary_key=True)  # lic_<hex>
    license_key_hash: str = Field(index=True, unique=True)  # SHA256(key) hex
    license_key_prefix: str = Field(index=True)  # 第一组 4 字符
    name: str = ""
    note: str = ""
    status: str = Field(default="pending", index=True)  # pending/active/suspended/revoked/expired
    validity_mode: str = "duration"  # duration(模式A) / fixed(模式B)
    duration_seconds: Optional[int] = None  # 模式A：首激活起算秒数
    activated_at: Optional[datetime] = None  # 首次激活时刻
    expires_at: Optional[datetime] = None  # 到期时刻（模式B 创建时指定）
    max_devices: int = 1
    features: list[str] = Field(default_factory=lambda: ["main"], sa_column=Column(JSON))
    minimum_client_version: str = "0.0.0"
    license_version: int = 1  # 任何影响凭证内容的变更 +1
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    suspended_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None


class Device(SQLModel, table=True):
    __tablename__ = "devices"

    id: str = Field(primary_key=True)  # dev_<uuid>
    license_id: str = Field(foreign_key="licenses.id", index=True)
    device_id: str = Field(index=True)  # 客户端算好的 sha256 hex
    device_name: str = ""
    platform: str = ""
    os_version: str = ""
    first_activated_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime = Field(default_factory=_utcnow)
    last_ip: str = ""
    last_client_version: str = ""
    last_nonce: Optional[str] = None  # 心跳防重放
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class LicenseEvent(SQLModel, table=True):
    __tablename__ = "license_events"

    id: str = Field(primary_key=True)  # evt_<uuid>
    license_id: Optional[str] = Field(default=None, index=True)
    device_id: Optional[str] = None
    event_type: str = Field(index=True)  # 见 schemas.EventType
    event_time: datetime = Field(default_factory=_utcnow, index=True)
    ip_address: str = ""
    client_version: str = ""
    result: str = ""  # success / failure
    reason_code: str = ""
    event_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))


def new_device_id() -> str:
    import uuid

    return "dev_" + uuid.uuid4().hex
