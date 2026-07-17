"""时间工具：全部 UTC；API 序列化为 ISO8601 Z。

服务层一律通过 timeutil.now() 取当前时间，测试可 monkeypatch 该函数注入假时钟。
"""
from __future__ import annotations

from datetime import datetime, timezone

DEFAULT_TOLERANCE_SECONDS = 300


def now() -> datetime:
    """当前 UTC 时间（aware）。测试注入点。"""
    return datetime.now(timezone.utc)


def utc_now() -> datetime:
    return now()


def ensure_utc(dt: datetime | None) -> datetime | None:
    """归一化为 aware UTC（SQLite 读回的 datetime 是 naive，按 UTC 解释）。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso_z(dt: datetime | None) -> str | None:
    """datetime -> '2026-07-17T15:00:00Z'。None 透传。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(value: str | datetime | None) -> datetime | None:
    """解析 ISO8601（支持 Z 后缀）为 aware UTC datetime。None/空串透传 None。"""
    if value is None or isinstance(value, datetime):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def detect_time_rollback(
    last_trusted: datetime,
    observed: datetime,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
) -> bool:
    """时间回拨检测（客户端/服务器通用逻辑）。

    observed 比最近可信时间早超过容差（默认 300s）即视为回拨。
    """
    if last_trusted.tzinfo is None:
        last_trusted = last_trusted.replace(tzinfo=timezone.utc)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return (last_trusted - observed).total_seconds() > tolerance_seconds


def skew_exceeds(a: datetime, b: datetime, tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS) -> bool:
    """两个时间点差值绝对值是否超过容差。"""
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return abs((a - b).total_seconds()) > tolerance_seconds
