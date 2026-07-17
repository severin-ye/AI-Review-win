"""核心规则：模式 A/B 有效期、状态优先级、设备上限、版本比较、回拨检测、错误码映射。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from license_server.core import timeutil
from license_server.crypto import version_gte
from license_server.models.tables import License
from license_server.schemas import (
    ERROR_HTTP_STATUS,
    ERROR_MESSAGES,
    ErrorCode,
)
from license_server.services.license_ops import resolve_effective_status
from license_server.services.token import credential_status

from conftest import activate, create_license, get_public_key, make_device_id


# ---------- 模式 A：duration 首激活起算 ----------

def test_mode_a_expires_at_first_activation_plus_duration(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], validity_mode="duration", duration_days=7)
    device = make_device_id("mode-a-device")
    resp = activate(clients["employee"], created["license_key"], device)
    assert resp.status_code == 200, resp.text
    token = resp.json()["license"]
    assert token["issued_at"] == "2026-07-17T15:00:00Z"
    assert token["expires_at"] == "2026-07-24T15:00:00Z"


# ---------- 模式 B：fixed 固定截止 ----------

def test_mode_b_fixed_expires_at(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(
        clients["admin"], validity_mode="fixed", fixed_expires_at="2026-08-01T00:00:00Z"
    )
    device = make_device_id("mode-b-device")
    resp = activate(clients["employee"], created["license_key"], device)
    assert resp.status_code == 200, resp.text
    assert resp.json()["license"]["expires_at"] == "2026-08-01T00:00:00Z"


# ---------- 离线放行 / 拒绝 ----------

def test_offline_credential_valid_before_expiry_denied_after(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], duration_days=7)
    resp = activate(clients["employee"], created["license_key"], make_device_id("offline"))
    body = resp.json()
    public = get_public_key(clients["admin"])
    # 未到期：本地验签 + 未过期 → 放行
    clock.set("2026-07-20T15:00:00Z")
    assert credential_status(body["license"], body["signature"], public, clock.now()) == "valid"
    # 已过期：拒绝
    clock.set("2026-07-25T15:00:01Z")
    assert credential_status(body["license"], body["signature"], public, clock.now()) == "expired"


# ---------- 状态优先级：revoked > suspended > expired > active ----------

def _lic(status: str, expires_at) -> License:
    return License(
        id="lic_t", license_key_hash="x" * 64, license_key_prefix="ABCD",
        status=status, expires_at=expires_at,
    )


def test_status_priority():
    now = datetime(2026, 7, 17, tzinfo=timezone.utc)
    future = now + timedelta(days=7)
    past = now - timedelta(days=1)
    # 未到期但 revoked / suspended → 立即生效
    assert resolve_effective_status(_lic("revoked", future), now) == "revoked"
    assert resolve_effective_status(_lic("suspended", future), now) == "suspended"
    # 已到期且 active → expired
    assert resolve_effective_status(_lic("active", past), now) == "expired"
    # revoked/suspended 优先于 expired
    assert resolve_effective_status(_lic("revoked", past), now) == "revoked"
    assert resolve_effective_status(_lic("suspended", past), now) == "suspended"
    # 正常 active / pending
    assert resolve_effective_status(_lic("active", future), now) == "active"
    assert resolve_effective_status(_lic("pending", None), now) == "pending"


# ---------- 设备上限计数 ----------

def test_device_limit_counts_bound_devices(clients, clock):
    created = create_license(clients["admin"], max_devices=1)
    key = created["license_key"]
    assert activate(clients["employee"], key, make_device_id("dev-1")).status_code == 200
    resp = activate(clients["employee"], key, make_device_id("dev-2"))
    assert resp.status_code == 403
    assert resp.json()["reason_code"] == "LICENSE_DEVICE_LIMIT_REACHED"


# ---------- license_version 比较 ----------

def test_license_version_bump_on_renew(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    assert created["license"]["license_version"] == 1
    resp = clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/renew",
                                 json={"extend_days": 7})
    assert resp.status_code == 200
    assert resp.json()["license"]["license_version"] == 2


# ---------- 语义化版本比较 ----------

def test_version_gte():
    assert version_gte("1.2.0", "1.2.0")
    assert version_gte("1.10.0", "1.9.0")
    assert version_gte("2.0.0", "1.99.99")
    assert not version_gte("1.2", "1.2.1")
    assert not version_gte("0.9.9", "1.0.0")
    assert version_gte("v1.2.3", "1.2.2")


# ---------- 时间回拨检测 ----------

def test_detect_time_rollback_with_tolerance():
    trusted = datetime(2026, 7, 17, 15, 0, 0, tzinfo=timezone.utc)
    # 回拨 400s > 容差 300s → 检出
    assert timeutil.detect_time_rollback(trusted, trusted - timedelta(seconds=400))
    # 回拨 100s < 容差 → 放行
    assert not timeutil.detect_time_rollback(trusted, trusted - timedelta(seconds=100))
    # 正向不走字
    assert not timeutil.detect_time_rollback(trusted, trusted + timedelta(seconds=3600))
    # 自定义容差
    assert timeutil.detect_time_rollback(trusted, trusted - timedelta(seconds=100),
                                         tolerance_seconds=60)


# ---------- 错误码映射完整性 ----------

def test_error_code_catalog_complete():
    expected = {
        "LICENSE_NOT_FOUND", "LICENSE_PENDING", "LICENSE_SUSPENDED", "LICENSE_REVOKED",
        "LICENSE_EXPIRED", "LICENSE_DEVICE_LIMIT_REACHED", "DEVICE_NOT_REGISTERED",
        "DEVICE_REVOKED", "DEVICE_MISMATCH", "CLIENT_VERSION_TOO_OLD",
        "INVALID_LICENSE_SIGNATURE", "INVALID_REQUEST_SIGNATURE", "SERVER_TIME_INVALID",
        "LICENSE_REFRESH_REQUIRED", "SERVER_UNREACHABLE", "REQUEST_TIMEOUT",
        "INTERNAL_SERVER_ERROR", "REPLAY_DETECTED", "RATE_LIMITED",
    }
    assert {c.value for c in ErrorCode} == expected
    for code in ErrorCode:
        assert code in ERROR_HTTP_STATUS, code
        assert 400 <= ERROR_HTTP_STATUS[code] <= 599
        assert ERROR_MESSAGES[code], code
