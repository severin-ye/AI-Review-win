"""PyInstaller 打包入口：python run.py --port <port>（或环境变量 PORT）。

Electron prod sidecar 以 `ai-review-backend.exe --port <port>` 拉起（见 electron/main/sidecar.ts）。
开发模式仍用 `uvicorn app.main:app --reload`（package.json backend:dev），不经本入口。
"""
from __future__ import annotations

import multiprocessing
import os
import sys


def _parse_port(default: int = 8765) -> int:
    port = default
    argv = sys.argv[1:]
    if "--port" in argv:
        try:
            port = int(argv[argv.index("--port") + 1])
        except (IndexError, ValueError):
            pass
    env_port = os.environ.get("PORT")
    if env_port:
        try:
            port = int(env_port)
        except ValueError:
            pass
    return port


def main() -> None:
    # PyInstaller onefile 下 uvicorn 内部 multiprocessing 需要 freeze_support
    multiprocessing.freeze_support()
    import uvicorn

    port = _parse_port()
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
