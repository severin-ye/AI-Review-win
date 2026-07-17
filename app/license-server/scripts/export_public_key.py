"""导出公钥 PEM 到 app/desktop/resources/license-public.pem（员工端验签内嵌用）。

DEV 模式（默认）会额外写 license-public.dev.json 标注文件并在终端醒目提示。
用法（在 app/license-server 下）：
    ../server/.venv/Scripts/python.exe scripts/export_public_key.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from license_server.core.config import REPO_ROOT, get_settings  # noqa: E402
from license_server.core.keys import get_key_manager  # noqa: E402


def main() -> None:
    settings = get_settings()
    km = get_key_manager(settings)
    out_dir = REPO_ROOT / "app" / "desktop" / "resources"
    out_dir.mkdir(parents=True, exist_ok=True)
    pem_path = out_dir / "license-public.pem"
    pem_path.write_text(km.public_pem, encoding="ascii")
    print(f"公钥已导出: {pem_path}")
    print(f"指纹: {km.fingerprint}")
    if km.dev:
        marker = out_dir / "license-public.dev.json"
        marker.write_text(
            json.dumps(
                {
                    "dev": True,
                    "fingerprint": km.fingerprint,
                    "warning": "DEV 密钥对，仅用于开发联调，生产构建前必须重新导出正式公钥",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print("!!! DEV 密钥对已导出（仅开发联调用），标注文件: license-public.dev.json")


if __name__ == "__main__":
    main()
