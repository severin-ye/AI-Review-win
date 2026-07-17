"""员工 API + 管理 API 端到端（任务书 §19.2 十六项全过 + 管理操作）。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from license_server.core import db, keys, timeutil
from license_server.crypto import canonical_json, verify_bytes
from license_server.main import create_admin_app, create_employee_app
from license_server.services.token import verify_credential

from conftest import (
    activate,
    create_license,
    fresh_nonce,
    get_public_key,
    heartbeat,
    make_device_id,
    refresh,
)


def _verify_response_signature(payload: dict, public) -> bool:
    body = {k: v for k, v in payload.items() if k != "signature"}
    return verify_bytes(public, canonical_json(body), payload["signature"])


# 1. 创建 → 首激活
def test_01_create_and_first_activation(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], name="张三")
    assert created["license_key"].startswith("AIREV-")
    assert created["license"]["status"] == "pending"
    resp = activate(clients["employee"], created["license_key"], make_device_id("d1"))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["license"]["license_id"] == created["license"]["id"]
    assert body["license"]["expires_at"] == "2026-07-24T15:00:00Z"
    # 凭证签名可被公钥验证
    public = get_public_key(clients["admin"])
    assert verify_credential(body["license"], body["signature"], public)
    # 管理端详情状态变为 active
    detail = clients["admin"].get(f"/api/v1/admin/licenses/{created['license']['id']}").json()
    assert detail["license"]["status"] == "active"
    assert detail["license"]["device_count"] == 1


# 2. 同设备重复激活（幂等，不占新额度）
def test_02_same_device_reactivation_idempotent(clients):
    created = create_license(clients["admin"], max_devices=1)
    key, device = created["license_key"], make_device_id("same")
    assert activate(clients["employee"], key, device).status_code == 200
    resp = activate(clients["employee"], key, device)
    assert resp.status_code == 200, resp.text
    detail = clients["admin"].get(f"/api/v1/admin/licenses/{created['license']['id']}").json()
    assert detail["license"]["device_count"] == 1
    assert len(detail["devices"]) == 1


# 3. 不同设备（额度内）
def test_03_second_device_within_limit(clients):
    created = create_license(clients["admin"], max_devices=2)
    key = created["license_key"]
    assert activate(clients["employee"], key, make_device_id("d1")).status_code == 200
    resp = activate(clients["employee"], key, make_device_id("d2"))
    assert resp.status_code == 200
    detail = clients["admin"].get(f"/api/v1/admin/licenses/{created['license']['id']}").json()
    assert detail["license"]["device_count"] == 2


# 4. 超限
def test_04_device_limit_reached(clients):
    created = create_license(clients["admin"], max_devices=1)
    key = created["license_key"]
    activate(clients["employee"], key, make_device_id("d1"))
    resp = activate(clients["employee"], key, make_device_id("d2"))
    assert resp.status_code == 403
    body = resp.json()
    assert body["success"] is False
    assert body["reason_code"] == "LICENSE_DEVICE_LIMIT_REACHED"
    assert body["message"]


# 5. 正常心跳
def test_05_heartbeat_active(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    device = make_device_id("hb")
    activate(clients["employee"], created["license_key"], device)
    resp = heartbeat(clients["employee"], lic_id, device, clock, license_version=1)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["license_version"] == 1
    assert body["next_heartbeat_seconds"] == 300
    assert "refresh_required" not in body
    public = get_public_key(clients["admin"])
    assert _verify_response_signature(body, public)


# 6. 暂停后心跳
def test_06_heartbeat_after_suspend(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    device = make_device_id("hb-susp")
    activate(clients["employee"], created["license_key"], device)
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/suspend")
    resp = heartbeat(clients["employee"], lic_id, device, clock)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "suspended"
    assert body["reason_code"] == "LICENSE_SUSPENDED"
    assert body["message"] == "许可证已被管理员暂停"
    assert body["server_time"]
    assert _verify_response_signature(body, get_public_key(clients["admin"]))


# 7. 恢复后心跳
def test_07_heartbeat_after_resume(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    device = make_device_id("hb-resume")
    activate(clients["employee"], created["license_key"], device)
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/suspend")
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/resume")
    resp = heartbeat(clients["employee"], lic_id, device, clock)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


# 8. 撤销后心跳（未到期也立即生效）
def test_08_heartbeat_after_revoke(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    device = make_device_id("hb-revoke")
    activate(clients["employee"], created["license_key"], device)
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/revoke", json={"reason": "离职"})
    resp = heartbeat(clients["employee"], lic_id, device, clock)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "revoked"
    assert body["reason_code"] == "LICENSE_REVOKED"
    assert body["message"] == "许可证已被管理员撤销"
    assert _verify_response_signature(body, get_public_key(clients["admin"]))


# 9. 到期刷新失败
def test_09_refresh_fails_when_expired(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], duration_days=7)
    lic_id = created["license"]["id"]
    device = make_device_id("exp-refresh")
    activate(clients["employee"], created["license_key"], device)
    clock.advance(days=8)
    resp = refresh(clients["employee"], lic_id, device)
    assert resp.status_code == 403
    assert resp.json()["reason_code"] == "LICENSE_EXPIRED"


# 10. 续期后刷新成功（version 更大、expires 更新）
def test_10_refresh_succeeds_after_renew(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], duration_days=7)
    lic_id = created["license"]["id"]
    device = make_device_id("renew-refresh")
    activate(clients["employee"], created["license_key"], device)
    clock.advance(days=8)
    # 到期后心跳先报 expired 且 license_version 变大前心跳带 refresh_required
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/renew", json={"extend_days": 7})
    resp = refresh(clients["employee"], lic_id, device)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["license"]["license_version"] == 2
    # 旧到期 2026-07-24 + 7 天（续期从 max(now, expires) 起算 = now 2026-07-25 + 7）
    assert body["license"]["expires_at"] > "2026-07-24T15:00:00Z"
    public = get_public_key(clients["admin"])
    assert verify_credential(body["license"], body["signature"], public)
    # 心跳携带旧 version → refresh_required
    hb = heartbeat(clients["employee"], lic_id, device, clock, license_version=1)
    assert hb.json().get("refresh_required") is True
    hb2 = heartbeat(clients["employee"], lic_id, device, clock, license_version=2)
    assert "refresh_required" not in hb2.json()


# 11. 无效 key
def test_11_invalid_key(clients):
    resp = activate(clients["employee"], "AIREV-AAAA-BBBB-CCCC", make_device_id("nobody"))
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["reason_code"] == "LICENSE_NOT_FOUND"


# 12. 伪造 device_id：未注册 / 属于其他许可证
def test_12_forged_device_id(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    device = make_device_id("real")
    activate(clients["employee"], created["license_key"], device)
    # 完全未注册的设备
    resp = heartbeat(clients["employee"], lic_id, make_device_id("forged"), clock)
    assert resp.status_code == 404
    assert resp.json()["reason_code"] == "DEVICE_NOT_REGISTERED"
    # 设备存在但挂在别的许可证下
    other = create_license(clients["admin"], name="另一人")
    other_device = make_device_id("other-dev")
    activate(clients["employee"], other["license_key"], other_device)
    resp2 = heartbeat(clients["employee"], lic_id, other_device, clock)
    assert resp2.status_code == 403
    assert resp2.json()["reason_code"] == "DEVICE_MISMATCH"


# 13. refresh 返回凭证验签通过
def test_13_refresh_credential_verifies(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    device = make_device_id("refresh-verify")
    activate(clients["employee"], created["license_key"], device)
    resp = refresh(clients["employee"], lic_id, device)
    assert resp.status_code == 200
    body = resp.json()
    public = get_public_key(clients["admin"])
    assert verify_credential(body["license"], body["signature"], public)


# 14. 过旧版本
def test_14_client_version_too_old(clients):
    created = create_license(clients["admin"], minimum_client_version="2.0.0")
    resp = activate(clients["employee"], created["license_key"],
                    make_device_id("old-client"), client_version="1.5.0")
    assert resp.status_code == 403
    assert resp.json()["reason_code"] == "CLIENT_VERSION_TOO_OLD"
    # 达到最低版本则放行
    resp2 = activate(clients["employee"], created["license_key"],
                     make_device_id("old-client"), client_version="2.0.0")
    assert resp2.status_code == 200


# 15. 重启后数据在（第二个 TestClient 同一数据目录重建 app）
def test_15_persistence_across_restart(clients, clock, workspace, monkeypatch):
    created = create_license(clients["admin"], name="持久化")
    lic_id = created["license"]["id"]
    device = make_device_id("persist")
    activate(clients["employee"], created["license_key"], device)
    # 模拟进程重启：丢弃 engine / key manager 缓存，同一数据目录重建 app
    db.reset_engine()
    keys.reset_key_manager()
    admin2 = create_admin_app()
    employee2 = create_employee_app()
    with TestClient(admin2) as a2, TestClient(employee2) as e2:
        detail = a2.get(f"/api/v1/admin/licenses/{lic_id}").json()
        assert detail["license"]["status"] == "active"
        assert detail["license"]["name"] == "持久化"
        assert len(detail["devices"]) == 1
        resp = heartbeat(e2, lic_id, device, clock)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"
        # 公钥从磁盘重载，签名仍可验证
        assert _verify_response_signature(resp.json(), get_public_key(a2))


# 16. 限流：activate 每 IP 固定窗口，超限 429 RATE_LIMITED
def test_16_rate_limited(workspace, clock, monkeypatch):
    monkeypatch.setenv("AI_REVIEW_LICENSE_RATE_LIMIT_PER_MINUTE", "2")
    app = create_employee_app()
    with TestClient(app) as emp:
        r1 = activate(emp, "AIREV-XXXX-YYYY-ZZZZ", make_device_id("rl"))
        r2 = activate(emp, "AIREV-XXXX-YYYY-ZZZZ", make_device_id("rl"))
        r3 = activate(emp, "AIREV-XXXX-YYYY-ZZZZ", make_device_id("rl"))
        assert r1.status_code == 404
        assert r2.status_code == 404
        assert r3.status_code == 429
        assert r3.json()["reason_code"] == "RATE_LIMITED"


# ---------- 心跳协议细节 ----------

def test_heartbeat_timestamp_skew_rejected(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    device = make_device_id("skew")
    activate(clients["employee"], created["license_key"], device)
    resp = heartbeat(clients["employee"], lic_id, device, clock,
                     timestamp="2020-01-01T00:00:00Z")
    assert resp.status_code == 400
    assert resp.json()["reason_code"] == "SERVER_TIME_INVALID"


def test_heartbeat_replay_nonce_rejected(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    device = make_device_id("replay")
    activate(clients["employee"], created["license_key"], device)
    nonce = fresh_nonce()
    assert heartbeat(clients["employee"], lic_id, device, clock, nonce=nonce).status_code == 200
    resp = heartbeat(clients["employee"], lic_id, device, clock, nonce=nonce)
    assert resp.status_code == 400
    assert resp.json()["reason_code"] == "REPLAY_DETECTED"


def test_heartbeat_pending_license(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    # 未激活的许可证：设备未注册优先命中
    resp = heartbeat(clients["employee"], lic_id, make_device_id("ghost"), clock)
    assert resp.status_code == 404
    assert resp.json()["reason_code"] == "DEVICE_NOT_REGISTERED"


def test_heartbeat_expired_status(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], duration_days=7)
    lic_id = created["license"]["id"]
    device = make_device_id("hb-exp")
    activate(clients["employee"], created["license_key"], device)
    clock.advance(days=8)
    resp = heartbeat(clients["employee"], lic_id, device, clock)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "expired"
    assert body["reason_code"] == "LICENSE_EXPIRED"
    # 惰性落库：详情状态已写为 expired
    detail = clients["admin"].get(f"/api/v1/admin/licenses/{lic_id}").json()
    assert detail["license"]["status"] == "expired"


# ---------- 管理操作 ----------

def test_admin_unbind_device_frees_slot(clients):
    created = create_license(clients["admin"], max_devices=1)
    lic_id = created["license"]["id"]
    key = created["license_key"]
    device = make_device_id("bound")
    activate(clients["employee"], key, device)
    detail = clients["admin"].get(f"/api/v1/admin/licenses/{lic_id}").json()
    row_id = detail["devices"][0]["id"]
    resp = clients["admin"].delete(f"/api/v1/admin/licenses/{lic_id}/devices/{row_id}")
    assert resp.status_code == 200
    # 解绑后新设备可激活
    assert activate(clients["employee"], key, make_device_id("new")).status_code == 200
    # 被解绑设备心跳 → DEVICE_REVOKED
    hb = refresh(clients["employee"], lic_id, device)
    assert hb.status_code == 403
    assert hb.json()["reason_code"] == "DEVICE_REVOKED"


def test_admin_reset_devices(clients):
    created = create_license(clients["admin"], max_devices=2)
    lic_id = created["license"]["id"]
    key = created["license_key"]
    activate(clients["employee"], key, make_device_id("r1"))
    activate(clients["employee"], key, make_device_id("r2"))
    resp = clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/devices/reset")
    assert resp.status_code == 200
    assert resp.json()["unbound"] == 2
    detail = clients["admin"].get(f"/api/v1/admin/licenses/{lic_id}").json()
    assert detail["license"]["device_count"] == 0


def test_admin_patch_note_and_search(clients):
    created = create_license(clients["admin"], name="原始名")
    lic_id = created["license"]["id"]
    resp = clients["admin"].patch(f"/api/v1/admin/licenses/{lic_id}",
                                  json={"name": "新名字", "note": "销售部"})
    assert resp.status_code == 200
    assert resp.json()["license"]["name"] == "新名字"
    lst = clients["admin"].get("/api/v1/admin/licenses", params={"search": "新名字"}).json()
    assert lst["total"] == 1
    lst2 = clients["admin"].get("/api/v1/admin/licenses", params={"search": "不存在"}).json()
    assert lst2["total"] == 0
    # 按前缀搜索
    prefix = created["license"]["key_prefix"]
    lst3 = clients["admin"].get("/api/v1/admin/licenses", params={"search": prefix}).json()
    assert lst3["total"] == 1


def test_admin_list_status_filter_and_no_full_key(clients):
    create_license(clients["admin"], name="过滤甲")
    lst = clients["admin"].get("/api/v1/admin/licenses", params={"status": "pending"}).json()
    assert lst["total"] == 1
    item = lst["items"][0]
    assert "license_key" not in item
    assert item["masked_key"].endswith("****-****")
    lst2 = clients["admin"].get("/api/v1/admin/licenses", params={"status": "active"}).json()
    assert lst2["total"] == 0


def test_admin_events_audit_trail(clients, clock):
    created = create_license(clients["admin"])
    lic_id = created["license"]["id"]
    key = created["license_key"]
    device = make_device_id("audit")
    activate(clients["employee"], key, device)
    heartbeat(clients["employee"], lic_id, device, clock)
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/suspend")
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/resume")
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/renew", json={"extend_days": 1})
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/revoke", json={"reason": "测试"})
    events = clients["admin"].get(f"/api/v1/admin/licenses/{lic_id}/events").json()["items"]
    types = {e["event_type"] for e in events}
    assert {
        "LICENSE_CREATED", "ACTIVATION_SUCCEEDED", "HEARTBEAT_SUCCEEDED",
        "LICENSE_SUSPENDED", "LICENSE_RESUMED", "LICENSE_RENEWED", "LICENSE_REVOKED",
    } <= types
    # 事件不含完整 key
    for e in events:
        assert key not in str(e["metadata"])


def test_admin_server_endpoints(clients):
    status = clients["admin"].get("/api/v1/admin/server/status").json()
    assert status["success"] is True
    assert "lan_ip" in status and "employee_url" in status
    stop = clients["admin"].post("/api/v1/admin/server/stop").json()
    assert stop["employee_running"] is False
    start = clients["admin"].post("/api/v1/admin/server/start").json()
    assert start["employee_running"] is True
    pk = clients["admin"].get("/api/v1/admin/server/public-key").json()
    assert pk["public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")
    assert pk["fingerprint"].startswith("SHA256:")
    assert pk["dev"] is True


def test_ping_endpoint(clients):
    resp = clients["employee"].get("/api/v1/ping")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["server_time"]
    assert body["key_fingerprint"].startswith("SHA256:")


def test_error_responses_never_leak_stack(clients):
    resp = clients["employee"].post("/api/v1/licenses/heartbeat", json={"bad": "body"})
    assert resp.status_code == 422
    assert "Traceback" not in resp.text
