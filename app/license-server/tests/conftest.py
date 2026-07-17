"""pytest 公共夹具：临时数据目录、admin/employee 两个 TestClient、可注入时钟。

- 每个用例独立临时数据目录（AI_REVIEW_LICENSE_DATA_DIR），互不影响
- 服务层时间一律经 timeutil.now() 读取，clock 夹具 monkeypatch 该函数
- 不依赖网络与真实时间
"""
from __future__ import annotations

import hashlib
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from license_server.core import db, keys, timeutil  # noqa: E402
from license_server.main import create_admin_app, create_employee_app  # noqa: E402


class ClockControl:
    """可注入时钟：set() 设定时刻，advance() 推移，now() 供 timeutil.now 调用。"""

    def __init__(self) -> None:
        self._now = datetime.now(timezone.utc).replace(microsecond=0)

    def now(self) -> datetime:
        return self._now

    def set(self, dt: datetime | str) -> None:
        if isinstance(dt, str):
            dt = timeutil.parse_iso(dt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        self._now = dt

    def advance(self, seconds: float = 0, days: float = 0) -> None:
        self._now = self._now + timedelta(seconds=seconds, days=days)


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    """独立数据目录 + 高限流阈值（限流专项测试自行调低）。"""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("AI_REVIEW_LICENSE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AI_REVIEW_LICENSE_RATE_LIMIT_PER_MINUTE", "100000")
    db.reset_engine()
    keys.reset_key_manager()
    yield data_dir
    db.reset_engine()
    keys.reset_key_manager()


@pytest.fixture()
def clock(monkeypatch):
    ctl = ClockControl()
    monkeypatch.setattr(timeutil, "now", ctl.now)
    return ctl


@pytest.fixture()
def admin_client(workspace, clock):
    app = create_admin_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def employee_client(workspace, clock):
    app = create_employee_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def clients(admin_client, employee_client):
    return {"admin": admin_client, "employee": employee_client}


# ---------- 公共辅助 ----------

def make_device_id(name: str) -> str:
    """客户端语义：device_id = sha256 hex。"""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def fresh_nonce() -> str:
    return uuid.uuid4().hex


def create_license(admin: TestClient, **overrides) -> dict:
    body = {
        "name": "测试员工",
        "note": "",
        "validity_mode": "duration",
        "duration_days": 7,
        "max_devices": 1,
        "features": ["main"],
        "minimum_client_version": "0.0.0",
    }
    body.update(overrides)
    resp = admin.post("/api/v1/admin/licenses", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def activate(employee: TestClient, license_key: str, device: str,
             client_version: str = "1.0.0", nonce: str | None = None,
             device_name: str = "测试机") -> object:
    return employee.post(
        "/api/v1/licenses/activate",
        json={
            "license_key": license_key,
            "device_id": device,
            "device_name": device_name,
            "platform": "win32",
            "os_version": "Windows 11",
            "client_version": client_version,
            "session_id": uuid.uuid4().hex,
            "nonce": nonce or fresh_nonce(),
        },
    )


def heartbeat(employee: TestClient, license_id: str, device: str, clock: ClockControl,
              nonce: str | None = None, license_version: int = 1,
              client_version: str = "1.0.0", timestamp: str | None = None) -> object:
    return employee.post(
        "/api/v1/licenses/heartbeat",
        json={
            "license_id": license_id,
            "device_id": device,
            "session_id": uuid.uuid4().hex,
            "client_version": client_version,
            "license_version": license_version,
            "timestamp": timestamp or timeutil.to_iso_z(clock.now()),
            "nonce": nonce or fresh_nonce(),
        },
    )


def refresh(employee: TestClient, license_id: str, device: str,
            client_version: str = "1.0.0") -> object:
    return employee.post(
        "/api/v1/licenses/refresh",
        json={"license_id": license_id, "device_id": device,
              "client_version": client_version},
    )


def get_public_key(admin: TestClient):
    """从管理 API 取公钥对象（验签用）。"""
    from cryptography.hazmat.primitives import serialization

    pem = admin.get("/api/v1/admin/server/public-key").json()["public_key_pem"]
    return serialization.load_pem_public_key(pem.encode("ascii"))
