"""任务书 §19.3 协议级场景模拟 A–F。

客户端侧逻辑用服务层函数（token.credential_status）模拟：
- 本地验签 + 未过期 → 放行
- 心跳返回 revoked/suspended/expired → 锁定
- 本地已过期 + 服务器不可达 → 拒绝
- 心跳超时（无响应）→ 不锁定
"""
from __future__ import annotations

from license_server.services.token import credential_status

from conftest import (
    activate,
    create_license,
    get_public_key,
    heartbeat,
    make_device_id,
    refresh,
)

# 客户端锁定规则（员工端实现语义的镜像）
LOCK_STATUSES = {"revoked", "suspended", "expired"}


def client_should_lock(hb_body: dict | None) -> bool:
    """心跳有响应且状态在锁定集合 → 锁定；无响应（超时/不可达）→ 不锁定。"""
    if hb_body is None:
        return False
    return hb_body.get("status") in LOCK_STATUSES


# A. 正常激活全流程
def test_scenario_a_normal_full_flow(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], name="场景A", duration_days=30)
    device = make_device_id("scenario-a")
    act = activate(clients["employee"], created["license_key"], device)
    assert act.status_code == 200
    cred = act.json()
    public = get_public_key(clients["admin"])
    assert credential_status(cred["license"], cred["signature"], public, clock.now()) == "valid"
    lic_id = cred["license"]["license_id"]
    for _ in range(3):
        clock.advance(seconds=300)
        hb = heartbeat(clients["employee"], lic_id, device, clock,
                       license_version=cred["license"]["license_version"])
        assert hb.status_code == 200
        assert hb.json()["status"] == "active"
        assert not client_should_lock(hb.json())


# B. 凭证未到期时服务器关闭 → 本地验签 + 未过期 → 放行
def test_scenario_b_offline_grace_while_credential_valid(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], duration_days=7)
    cred = activate(clients["employee"], created["license_key"],
                    make_device_id("scenario-b")).json()
    public = get_public_key(clients["admin"])
    # 服务器关闭 = 此后不再发任何请求；客户端仅凭本地凭证判断
    clock.advance(days=2)
    assert credential_status(cred["license"], cred["signature"], public, clock.now()) == "valid"
    assert not client_should_lock(None)  # 无响应不锁定


# C. 使用中心跳拿到 revoked → 锁定语义
def test_scenario_c_revoked_mid_session_locks(clients, clock):
    created = create_license(clients["admin"], duration_days=7)
    device = make_device_id("scenario-c")
    cred = activate(clients["employee"], created["license_key"], device).json()
    lic_id = cred["license"]["license_id"]
    assert heartbeat(clients["employee"], lic_id, device, clock).json()["status"] == "active"
    # 管理员撤销
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/revoke",
                          json={"reason": "违规使用"})
    clock.advance(seconds=300)
    hb = heartbeat(clients["employee"], lic_id, device, clock)
    assert hb.status_code == 200
    assert hb.json()["status"] == "revoked"
    assert hb.json()["reason_code"] == "LICENSE_REVOKED"
    assert client_should_lock(hb.json()) is True
    # 锁定后即使本地凭证未到期也不再放行（心跳已确认撤销）
    # 员工端语义：锁定状态一经心跳确认即持久，不回落到本地验签
    refresh_resp = refresh(clients["employee"], lic_id, device)
    assert refresh_resp.status_code == 403
    assert refresh_resp.json()["reason_code"] == "LICENSE_REVOKED"


# D. 本地已过期 + 服务器不可达 → 拒绝
def test_scenario_d_expired_offline_denied(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], duration_days=7)
    cred = activate(clients["employee"], created["license_key"],
                    make_device_id("scenario-d")).json()
    public = get_public_key(clients["admin"])
    # 服务器不可达 = 不再发请求；时钟越过到期
    clock.advance(days=8)
    status = credential_status(cred["license"], cred["signature"], public, clock.now())
    assert status == "expired"
    # 客户端规则：expired → 拒绝（即使无法联系服务器确认）
    assert status != "valid"


# E. 续期 7 天 → refresh → 新截止时间
def test_scenario_e_renew_then_refresh(clients, clock):
    clock.set("2026-07-17T15:00:00Z")
    created = create_license(clients["admin"], duration_days=7)
    device = make_device_id("scenario-e")
    cred = activate(clients["employee"], created["license_key"], device).json()
    lic_id = cred["license"]["license_id"]
    old_expires = cred["license"]["expires_at"]
    assert old_expires == "2026-07-24T15:00:00Z"
    clients["admin"].post(f"/api/v1/admin/licenses/{lic_id}/renew", json={"extend_days": 7})
    # 心跳提示需要刷新
    hb = heartbeat(clients["employee"], lic_id, device, clock, license_version=1)
    assert hb.json().get("refresh_required") is True
    # refresh 取新凭证
    resp = refresh(clients["employee"], lic_id, device)
    assert resp.status_code == 200
    new_cred = resp.json()
    assert new_cred["license"]["license_version"] == 2
    assert new_cred["license"]["expires_at"] == "2026-07-31T15:00:00Z"
    # 新凭证本地验签通过
    public = get_public_key(clients["admin"])
    assert credential_status(new_cred["license"], new_cred["signature"], public,
                             clock.now()) == "valid"


# F. 单次心跳超时 → 不锁定（模拟网络异常路径）
def test_scenario_f_single_heartbeat_timeout_no_lock(clients, clock):
    created = create_license(clients["admin"], duration_days=7)
    device = make_device_id("scenario-f")
    cred = activate(clients["employee"], created["license_key"], device).json()
    lic_id = cred["license"]["license_id"]
    public = get_public_key(clients["admin"])
    # 第一次心跳正常
    hb1 = heartbeat(clients["employee"], lic_id, device, clock)
    assert hb1.json()["status"] == "active"
    # 第二次心跳"超时"：客户端捕获网络异常，得不到响应体
    timed_out_body = None  # 模拟 httpx.ReadTimeout 被捕获后的状态
    assert client_should_lock(timed_out_body) is False
    # 本地凭证仍有效 → 继续使用
    assert credential_status(cred["license"], cred["signature"], public, clock.now()) == "valid"
    # 网络恢复后心跳正常，仍未锁定
    clock.advance(seconds=300)
    hb3 = heartbeat(clients["employee"], lic_id, device, clock)
    assert hb3.json()["status"] == "active"
    assert not client_should_lock(hb3.json())
