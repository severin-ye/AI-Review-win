"""统一 UTC 时间语义，并兼容旧 SQLite 中的 naive UTC 值。"""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """返回带时区的当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """旧库 naive datetime 按 UTC 解释；aware datetime 统一转换为 UTC。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_iso_utc(value: datetime | None) -> str | None:
    """输出明确包含 UTC 时区的 ISO 8601 字符串。"""
    if value is None:
        return None
    return ensure_utc(value).isoformat().replace("+00:00", "Z")
