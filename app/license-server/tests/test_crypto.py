"""密码学原语：canonical JSON 稳定性、签名/验签、License Key 生成、对拍向量。"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from license_server import crypto
from license_server.crypto import (
    LICENSE_KEY_CHARSET,
    canonical_json,
    generate_license_key,
    hash_license_key,
    sign_object,
    verify_license_key_hash,
    verify_object,
)

VECTORS_PATH = Path(__file__).resolve().parent / "vectors" / "license_vectors.json"


def _seed_private_key() -> Ed25519PrivateKey:
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(vectors["seed_hex"]))


# ---------- canonical JSON ----------

def test_canonical_sorts_keys_recursively_and_compacts():
    obj = {"b": {"d": 1, "c": 2}, "a": [3, 1]}
    assert canonical_json(obj) == b'{"a":[3,1],"b":{"c":2,"d":1}}'


def test_canonical_unicode_raw_utf8_no_ascii_escape():
    obj = {"b": "中文审校", "a": 1}
    assert canonical_json(obj) == '{"a":1,"b":"中文审校"}'.encode("utf-8")


def test_canonical_is_stable_across_calls():
    obj = {"z": 1, "y": {"w": [1, 2], "v": None}, "x": True}
    assert canonical_json(obj) == canonical_json(obj)


# ---------- 签名 ----------

def test_sign_verify_roundtrip_and_tamper_fails():
    private = _seed_private_key()
    public = private.public_key()
    token = {"license_id": "lic_x", "device_id": "ab" * 32,
             "expires_at": "2026-07-24T15:00:00Z"}
    signature = sign_object(private, token)
    assert verify_object(public, token, signature)
    # 改 expires_at / device_id 验签必须失败
    assert not verify_object(public, dict(token, expires_at="2026-07-25T15:00:00Z"), signature)
    assert not verify_object(public, dict(token, device_id="cd" * 32), signature)


def test_malformed_signature_fails_closed():
    public = _seed_private_key().public_key()
    assert not verify_object(public, {"a": 1}, "!!!not-base64!!!")
    assert not verify_object(public, {"a": 1}, base64.b64encode(b"short").decode())


# ---------- License Key ----------

KEY_PATTERN = re.compile(r"^AIREV(-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}){3}$")


def test_license_key_format():
    for _ in range(200):
        assert KEY_PATTERN.match(generate_license_key())


def test_license_key_1000_unique_no_confusing_chars():
    keys = {generate_license_key() for _ in range(1000)}
    assert len(keys) == 1000
    confusing = set("0O1IL")
    for key in keys:
        body = key.split("-", 1)[1].replace("-", "")
        assert len(body) == 12
        assert not (set(body) & confusing)
        assert all(ch in LICENSE_KEY_CHARSET for ch in body)


def test_license_key_charset_matches_spec_string():
    # brief 锁定的字符集字符串（0-9+A-Z 共 36 个，排除 0/O/1/I/L 共 5 个 → 31 个）
    assert LICENSE_KEY_CHARSET == "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    assert len(LICENSE_KEY_CHARSET) == 31
    assert len(set(LICENSE_KEY_CHARSET)) == 31


def test_key_hash_compare_uses_compare_digest():
    source = Path(crypto.__file__).read_text(encoding="utf-8")
    assert "hmac.compare_digest" in source


def test_verify_license_key_hash():
    key = generate_license_key()
    digest = hash_license_key(key)
    assert verify_license_key_hash(key, digest)
    assert not verify_license_key_hash(generate_license_key(), digest)


# ---------- 对拍向量（员工端 TS 用） ----------

def test_vectors_file_complete_and_reproducible():
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert len(vectors["cases"]) >= 4
    private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(vectors["seed_hex"]))
    public = private.public_key()
    # 公钥与种子一致
    pem = public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    assert pem == vectors["public_key_pem"]

    names = set()
    for case in vectors["cases"]:
        names.add(case["name"])
        # canonical 字符串与规则重算逐字节一致
        assert canonical_json(case["token"]).decode("utf-8") == case["canonical"]
        # 正常用例的签名可由种子私钥复现（Ed25519 确定性）
        if case["name"] == "valid_token":
            assert sign_object(private, case["token"]) == case["signature"]
        assert verify_object(public, case["token"], case["signature"]) is case["expect_verify"]
    assert {"valid_token", "tampered_expires_at", "tampered_device_id", "bad_signature"} <= names
