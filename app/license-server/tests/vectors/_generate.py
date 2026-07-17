"""生成 tests/vectors/license_vectors.json（一次性工具，可重复运行，输出确定性）。

密钥来自固定 32 字节种子 bytes(range(32))，Ed25519 签名确定性，便于员工端 TS 对拍。
运行：cd app/license-server && ../server/.venv/Scripts/python.exe tests/vectors/_generate.py
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from license_server.crypto import canonical_json

SEED_HEX = bytes(range(32)).hex()

BASE_TOKEN = {
    "schema_version": 1,
    "license_id": "lic_" + "ab" * 16,
    "device_id": "cd" * 32,
    "issued_at": "2026-07-17T15:00:00Z",
    "expires_at": "2026-07-24T15:00:00Z",
    "features": ["main"],
    "license_version": 1,
}


def main() -> None:
    private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(SEED_HEX))
    public = private.public_key()
    public_pem = public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    canonical = canonical_json(BASE_TOKEN)
    signature = base64.b64encode(private.sign(canonical)).decode("ascii")

    tampered_expires = dict(BASE_TOKEN, expires_at="2026-07-25T15:00:00Z")
    tampered_device = dict(BASE_TOKEN, device_id="ef" * 32)
    bad_signature = signature[:-4] + ("AAAA" if not signature.endswith("AAAA") else "BBBB")

    vectors = {
        "description": (
            "AI-Review 许可证签名对拍向量。canonical 规则：JSON 键递归排序、无空白、"
            "UTF-8 原样非 ASCII（Python: json.dumps(obj, sort_keys=True, "
            "separators=(',',':'), ensure_ascii=False).encode('utf-8')）。"
            "签名 = Ed25519(canonical bytes)，base64 编码。"
        ),
        "seed_hex": SEED_HEX,
        "private_key_seed_note": "私钥 = Ed25519PrivateKey.from_private_bytes(seed_hex)，仅供对拍，非生产密钥",
        "public_key_pem": public_pem,
        "cases": [
            {
                "name": "valid_token",
                "token": BASE_TOKEN,
                "canonical": canonical.decode("utf-8"),
                "signature": signature,
                "expect_verify": True,
            },
            {
                "name": "tampered_expires_at",
                "token": tampered_expires,
                "canonical": canonical_json(tampered_expires).decode("utf-8"),
                "signature": signature,
                "expect_verify": False,
                "note": "expires_at 被篡改后，原签名验签必须失败",
            },
            {
                "name": "tampered_device_id",
                "token": tampered_device,
                "canonical": canonical_json(tampered_device).decode("utf-8"),
                "signature": signature,
                "expect_verify": False,
                "note": "device_id 被篡改后，原签名验签必须失败",
            },
            {
                "name": "bad_signature",
                "token": BASE_TOKEN,
                "canonical": canonical.decode("utf-8"),
                "signature": bad_signature,
                "expect_verify": False,
                "note": "签名串本身被破坏，验签必须失败",
            },
        ],
    }
    out = Path(__file__).resolve().parent / "license_vectors.json"
    out.write_text(json.dumps(vectors, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"vectors written: {out}")


if __name__ == "__main__":
    main()
