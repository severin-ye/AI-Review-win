"""UTC 时间工具：新值带时区，旧库 naive 值按 UTC 兼容。"""
from datetime import datetime, timedelta, timezone

from app.core.timeutil import ensure_utc, to_iso_utc, utc_now


def test_utc_now_is_timezone_aware() -> None:
    value = utc_now()
    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


def test_naive_legacy_value_is_interpreted_as_utc() -> None:
    legacy = datetime(2026, 7, 18, 12, 34, 56)
    assert ensure_utc(legacy) == legacy.replace(tzinfo=timezone.utc)
    assert to_iso_utc(legacy) == "2026-07-18T12:34:56Z"


def test_aware_value_is_normalized_to_utc() -> None:
    value = datetime(2026, 7, 18, 20, 34, 56, tzinfo=timezone(timedelta(hours=8)))
    assert to_iso_utc(value) == "2026-07-18T12:34:56Z"
