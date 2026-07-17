"""Ed25519 密钥对管理。

首启在数据目录 keys/ 下生成密钥对：
- Windows 且 win32crypt 可用 → 私钥经 DPAPI(CryptProtectData) 加密存 private.key.bin
- 否则明文 private_key.pem + 醒目警告日志（仅开发用）
- 公钥始终存 public_key.pem

DEV 标记来自 Settings.dev_keys（env AI_REVIEW_LICENSE_DEV_KEYS，默认 1）。
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .config import Settings

logger = logging.getLogger("license_server.keys")

_DPAPI_FILE = "private.key.bin"
_PLAIN_FILE = "private_key.pem"
_PUBLIC_FILE = "public_key.pem"

try:  # DPAPI（Windows）
    import win32crypt  # type: ignore

    _HAS_DPAPI = True
except ImportError:  # pragma: no cover - 非 Windows
    win32crypt = None  # type: ignore
    _HAS_DPAPI = False


def _public_pem(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _private_pem(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


class KeyManager:
    """加载或生成密钥对，提供签名/验签所需的 key 对象与公钥信息。"""

    def __init__(self, settings: Settings):
        self._settings = settings
        self.dev = settings.dev_keys
        self.keys_dir = settings.keys_dir
        self.dpapi_used = False
        self._private_key: Ed25519PrivateKey | None = None
        self._public_key: Ed25519PublicKey | None = None
        self.load_or_create()

    # ---------- 加载 / 生成 ----------

    def load_or_create(self) -> None:
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        private = self._load_private()
        if private is None:
            private = Ed25519PrivateKey.generate()
            self._store_private(private)
            logger.info("已生成新的 Ed25519 密钥对（目录 %s）", self.keys_dir)
        self._private_key = private
        self._public_key = private.public_key()
        public_path = self.keys_dir / _PUBLIC_FILE
        public_path.write_bytes(_public_pem(self._public_key))
        if self.dev:
            logger.warning("密钥对处于 DEV 模式（AI_REVIEW_LICENSE_DEV_KEYS=1），生产部署请显式关闭")

    def _load_private(self) -> Ed25519PrivateKey | None:
        dpapi_path = self.keys_dir / _DPAPI_FILE
        plain_path = self.keys_dir / _PLAIN_FILE
        if dpapi_path.exists():
            if not _HAS_DPAPI:
                logger.error("发现 DPAPI 私钥但当前环境无 win32crypt，无法解密")
                return None
            blob = win32crypt.CryptUnprotectData(dpapi_path.read_bytes(), None, None, None, 0)[1]
            self.dpapi_used = True
            return serialization.load_pem_private_key(blob, password=None)
        if plain_path.exists():
            logger.warning("使用明文私钥 %s（仅开发用，生产请启用 DPAPI）", plain_path)
            return serialization.load_pem_private_key(plain_path.read_bytes(), password=None)
        return None

    def _store_private(self, private: Ed25519PrivateKey) -> None:
        pem = _private_pem(private)
        if _HAS_DPAPI:
            blob = win32crypt.CryptProtectData(pem, None, None, None, None, 0)
            (self.keys_dir / _DPAPI_FILE).write_bytes(blob)
            self.dpapi_used = True
            logger.info("私钥已用 DPAPI 加密存储（private.key.bin）")
        else:
            path = self.keys_dir / _PLAIN_FILE
            path.write_bytes(pem)
            logger.warning("win32crypt 不可用：私钥以明文 PEM 存储于 %s（仅开发用！）", path)

    # ---------- 对外 ----------

    @property
    def private_key(self) -> Ed25519PrivateKey:
        assert self._private_key is not None
        return self._private_key

    @property
    def public_key(self) -> Ed25519PublicKey:
        assert self._public_key is not None
        return self._public_key

    @property
    def public_pem(self) -> str:
        return _public_pem(self.public_key).decode("ascii")

    @property
    def fingerprint(self) -> str:
        der = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return "SHA256:" + hashlib.sha256(der).hexdigest()

    def regenerate(self) -> None:
        """重新生成密钥对（危险：所有已签发凭证立即失效）。"""
        for name in (_DPAPI_FILE, _PLAIN_FILE, _PUBLIC_FILE):
            path = self.keys_dir / name
            if path.exists():
                path.unlink()
        self.dpapi_used = False
        self.load_or_create()
        logger.warning("密钥对已重新生成：所有已签发凭证从此刻起无法通过验签")


_key_manager: KeyManager | None = None
_key_manager_dir: Path | None = None


def get_key_manager(settings: Settings | None = None) -> KeyManager:
    global _key_manager, _key_manager_dir
    from .config import get_settings

    settings = settings or get_settings()
    if _key_manager is None or _key_manager_dir != settings.keys_dir:
        _key_manager = KeyManager(settings)
        _key_manager_dir = settings.keys_dir
    return _key_manager


def reset_key_manager() -> None:
    global _key_manager, _key_manager_dir
    _key_manager = None
    _key_manager_dir = None
