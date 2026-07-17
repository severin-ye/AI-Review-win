"""签名凭证：签发（token + signature）与验签。

凭证结构：
    {"schema_version":1,"license_id":"lic_<hex>","device_id":"<sha256 hex>",
     "issued_at":"<ISO Z>","expires_at":"<ISO Z>","features":["main"],"license_version":1}
响应结构：{"license": {...}, "signature": "<base64>"}
signature = 对 token 对象 canonical bytes 的 Ed25519 签名。
"""
from __future__ import annotations

from datetime import datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ..core import timeutil
from ..core.keys import KeyManager
from ..crypto import canonical_json, sign_bytes, verify_bytes
from ..models.tables import License

SCHEMA_VERSION = 1


def build_token(license: License, device_id: str, now: datetime | None = None) -> dict:
    now = now or timeutil.now()
    return {
        "schema_version": SCHEMA_VERSION,
        "license_id": license.id,
        "device_id": device_id,
        "issued_at": timeutil.to_iso_z(now),
        "expires_at": timeutil.to_iso_z(license.expires_at),
        "features": list(license.features or ["main"]),
        "license_version": license.license_version,
    }


def sign_token(token: dict, key_manager: KeyManager) -> str:
    return sign_bytes(key_manager.private_key, canonical_json(token))


def issue_credential(license: License, device_id: str, key_manager: KeyManager,
                     now: datetime | None = None) -> dict:
    """签发凭证：{"license": token, "signature": b64}"""
    token = build_token(license, device_id, now)
    return {"license": token, "signature": sign_token(token, key_manager)}


def verify_credential(token: dict, signature_b64: str, public_key: Ed25519PublicKey) -> bool:
    """客户端（或测试）验签：对 token canonical bytes 验 Ed25519 签名。"""
    return verify_bytes(public_key, canonical_json(token), signature_b64)


def credential_status(token: dict, signature_b64: str, public_key: Ed25519PublicKey,
                      now: datetime | None = None) -> str:
    """本地凭证体检（员工端离线逻辑的服务层镜像）：

    返回 "invalid_signature" / "expired" / "valid"。
    """
    now = now or timeutil.now()
    if not verify_credential(token, signature_b64, public_key):
        return "invalid_signature"
    expires_at = timeutil.parse_iso(token.get("expires_at"))
    if expires_at is not None and now > expires_at:
        return "expired"
    return "valid"


def sign_response(payload: dict, key_manager: KeyManager) -> dict:
    """对响应体（除 signature 外）整体签名并附加 signature 字段（心跳响应用）。"""
    body = {k: v for k, v in payload.items() if k != "signature"}
    body["signature"] = sign_bytes(key_manager.private_key, canonical_json(body))
    return body
