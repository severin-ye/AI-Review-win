"""协议密码学原语：canonical JSON、Ed25519 签名、License Key 生成与哈希。

canonical JSON 规则（员工端 Node 必须逐字节一致）：
    json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
等价 JS：JSON.stringify(obj, Object.keys(obj).sort())（对嵌套对象需稳定 stringify，
键递归排序、无空白、非 ASCII 字符原样 UTF-8 输出、不转义 "/"）。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# License Key 字符集：32 个，排除 0/O/1/I/L
LICENSE_KEY_CHARSET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
LICENSE_KEY_PREFIX = "AIREV"
LICENSE_KEY_GROUPS = 3
LICENSE_KEY_GROUP_LEN = 4


def canonical_json(obj) -> bytes:
    """canonical JSON bytes：键递归排序、无空白、UTF-8 原样输出非 ASCII。"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ---------- Ed25519 ----------

def sign_bytes(private_key: Ed25519PrivateKey, payload: bytes) -> str:
    """签名并返回 base64。"""
    return base64.b64encode(private_key.sign(payload)).decode("ascii")


def verify_bytes(public_key: Ed25519PublicKey, payload: bytes, signature_b64: str) -> bool:
    """验签；签名格式非法或验签失败均返回 False。"""
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception:
        return False
    try:
        public_key.verify(signature, payload)
        return True
    except InvalidSignature:
        return False


def sign_object(private_key: Ed25519PrivateKey, obj) -> str:
    """对对象 canonical bytes 签名。"""
    return sign_bytes(private_key, canonical_json(obj))


def verify_object(public_key: Ed25519PublicKey, obj, signature_b64: str) -> bool:
    return verify_bytes(public_key, canonical_json(obj), signature_b64)


# ---------- License Key ----------

def generate_license_key() -> str:
    """生成 AIREV-XXXX-XXXX-XXXX（字符集 32，secrets.choice）。"""
    groups = [
        "".join(secrets.choice(LICENSE_KEY_CHARSET) for _ in range(LICENSE_KEY_GROUP_LEN))
        for _ in range(LICENSE_KEY_GROUPS)
    ]
    return f"{LICENSE_KEY_PREFIX}-" + "-".join(groups)


def hash_license_key(key: str) -> str:
    """SHA256(key) hex，DB 仅存此哈希。"""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def license_key_prefix(key: str) -> str:
    """第一组 4 字符（脱敏展示用），如 AIREV-7K2Q-XXXX-XXXX -> 7K2Q。"""
    parts = key.split("-")
    return parts[1] if len(parts) >= 2 else ""


def verify_license_key_hash(candidate_key: str, stored_hash: str) -> bool:
    """候选 key 的哈希与存储哈希比较（hmac.compare_digest 防时序）。"""
    candidate = hash_license_key(candidate_key)
    return hmac.compare_digest(candidate, stored_hash)


def normalize_license_key(key: str) -> str:
    """规整输入：去空白、转大写（对用户友好，不改变哈希语义）。"""
    return key.strip().upper()


# ---------- 其它 ----------

def new_license_id() -> str:
    return "lic_" + uuid.uuid4().hex


def new_event_id() -> str:
    return "evt_" + uuid.uuid4().hex


def version_gte(client_version: str, minimum_version: str) -> bool:
    """语义化版本比较：client >= minimum（按数值段比较，缺段补 0，非数字段忽略）。"""

    def parse(v: str) -> tuple[int, ...]:
        parts = []
        for piece in (v or "0").strip().lstrip("v").split("."):
            digits = "".join(ch for ch in piece if ch.isdigit())
            parts.append(int(digits) if digits else 0)
        return tuple(parts)

    c, m = parse(client_version), parse(minimum_version)
    length = max(len(c), len(m))
    c += (0,) * (length - len(c))
    m += (0,) * (length - len(m))
    return c >= m
