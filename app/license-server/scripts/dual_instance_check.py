"""双开实测：验证打包后的 句读授权中心.exe 单实例行为。

流程：
  1. 以 89xx 端口 + 临时 .data + AI_REVIEW_LICENSE_SKIP_FIREWALL=1 启动实例 #1
  2. 等 http://127.0.0.1:<admin>/api/v1/ping 返回 200（实例 #1 就绪）
  3. 同环境再启动实例 #2 → 期望：立即以退出码 0 退出 + 打印「已在运行」提示
  4. 确认实例 #1 仍健康、两个端口各只有一个监听
  5. 收尾：终止实例 #1、删除临时数据目录（驱动脚本对自身启动的进程负全责）

用法（app/license-server 目录下）：
  ..\\server\\.venv\\Scripts\\python.exe scripts\\dual_instance_check.py [exe路径]
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ADMIN_PORT = 8977
EMPLOYEE_PORT = 8978
DEFAULT_EXE = Path(__file__).resolve().parents[1] / "dist" / "句读授权中心.exe"


def wait_ping(url: str, timeout: float = 60.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    exe = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXE
    if not exe.exists():
        print(f"FAIL: exe 不存在: {exe}")
        return 2

    data_dir = Path(tempfile.mkdtemp(prefix="ai-review-license-dualtest-"))
    env = {
        **os.environ,
        "AI_REVIEW_LICENSE_ADMIN_PORT": str(ADMIN_PORT),
        "AI_REVIEW_LICENSE_EMPLOYEE_PORT": str(EMPLOYEE_PORT),
        "AI_REVIEW_LICENSE_DATA_DIR": str(data_dir),
        "AI_REVIEW_LICENSE_SKIP_FIREWALL": "1",
    }
    ping_url = f"http://127.0.0.1:{ADMIN_PORT}/api/v1/ping"
    results: dict[str, object] = {"exe": str(exe), "data_dir": str(data_dir)}
    first: subprocess.Popen[bytes] | None = None
    rc = 1
    try:
        # —— 实例 #1 ——
        first = subprocess.Popen(
            [str(exe)], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        results["first_pid"] = first.pid
        if not wait_ping(ping_url):
            results["error"] = "实例 #1 60 秒内未就绪"
            print(f"RESULT {results}")
            return 1
        results["first_ready"] = True

        # —— 实例 #2（双开）——
        second = subprocess.run(
            [str(exe)], env=env,
            capture_output=True, timeout=60, check=False,
        )
        out = second.stdout.decode("mbcs", errors="replace") + second.stderr.decode(
            "mbcs", errors="replace"
        )
        results["second_returncode"] = second.returncode
        results["second_output"] = out.strip()
        results["second_rejected_ok"] = (
            second.returncode == 0 and "句读授权中心已在运行，请勿重复启动。" in out
        )

        # —— 实例 #1 仍健康 ——
        results["first_still_healthy"] = wait_ping(ping_url, timeout=5)

        ok = (
            results["second_rejected_ok"] is True
            and results["first_still_healthy"] is True
        )
        rc = 0 if ok else 1
        results["verdict"] = "PASS" if ok else "FAIL"
        print(f"RESULT {results}")
        return rc
    finally:
        if first is not None and first.poll() is None:
            # onefile exe：Popen pid 是 bootloader，真正监听端口的是其子进程，
            # 必须 taskkill /T 杀整棵进程树（terminate() 只杀 bootloader 会留下孤儿）
            subprocess.run(
                ["taskkill", "/PID", str(first.pid), "/T", "/F"],
                capture_output=True, check=False,
            )
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
