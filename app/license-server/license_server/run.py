"""入口：同进程起两个 uvicorn Server。

- admin    仅 127.0.0.1:8767（可用 AI_REVIEW_LICENSE_ADMIN_HOST/PORT 改）
- employee 0.0.0.0:8768（可用 AI_REVIEW_LICENSE_EMPLOYEE_HOST/PORT 改，
  或管理页「设置」里保存的运行时配置覆盖）
启动后自动打开浏览器到管理页。employee 监听可被管理 API 启动/停止（admin 进程不死）。

单实例（2026-07-18 双开覆盖密钥事故后加，调研见 docs/research/single-instance-chatgpt.md）：
- main() 最早期（数据目录初始化、密钥生成、防火墙、uvicorn 全部之前）抢
  Windows Named Mutex；已存在 → 醒目中文提示并以退出码 0 退出（不是错误，不 traceback）。
- 端口绑定失败兜底：mutex 之外的第二道防线（如端口被其它程序/残留进程占用），
  admin 或 employee 监听起不来时打印「端口被占用，服务可能已在运行」并以非 0 码退出。
"""
from __future__ import annotations

import json
import logging
import multiprocessing
import sys
import threading
import time
import webbrowser

import uvicorn

from .core.config import Settings, get_settings
from .main import create_admin_app, create_employee_app

logger = logging.getLogger("license_server.run")


class EmployeeServerController:
    """管理 employee uvicorn 监听的生命周期（管理 API start/stop 用）。"""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._desired_running = True

    def _runtime_config(self) -> dict:
        path = self._settings.runtime_config_path
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def employee_running(self) -> bool:
        with self._lock:
            return self._server is not None and not self._server.should_exit

    def _run_server(self, server: uvicorn.Server) -> None:
        """线程入口：端口被占等 OSError 只记日志，不让线程裸抛 traceback。"""
        try:
            server.run()
        except OSError as exc:
            logger.error("员工端监听启动失败（端口被占用？）: %s", exc)

    def start_employee(self) -> None:
        with self._lock:
            self._desired_running = True
            if self._server is not None and not self._server.should_exit:
                return
            overrides = self._runtime_config()
            host = overrides.get("employee_host") or (
                "127.0.0.1" if overrides.get("lan_only") else self._settings.employee_host
            )
            port = int(overrides.get("employee_port") or self._settings.employee_port)
            app = create_employee_app(self._settings)
            config = uvicorn.Config(
                app, host=host, port=port,
                log_level=overrides.get("log_level") or self._settings.log_level,
            )
            server = uvicorn.Server(config)
            thread = threading.Thread(
                target=self._run_server, args=(server,), name="employee-server", daemon=True
            )
            self._server = server
            self._thread = thread
            thread.start()
            logger.info("员工端监听已启动: http://%s:%d", host, port)

    def wait_started(self, timeout: float = 5.0) -> bool:
        """等待 employee 监听完成启动；线程启动失败（如端口被占）或超时返回 False。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                server = self._server
                thread = self._thread
            if server is not None and server.started:
                return True
            if thread is not None and not thread.is_alive():
                return False
            time.sleep(0.05)
        return False

    def stop_employee(self) -> None:
        with self._lock:
            self._desired_running = False
            if self._server is not None:
                self._server.should_exit = True
            thread = self._thread
            self._server = None
            self._thread = None
        if thread is not None:
            thread.join(timeout=5)
        logger.info("员工端监听已停止")

    def shutdown(self) -> None:
        self.stop_employee()


def _effective_employee_port(settings: Settings) -> int:
    """员工监听实际端口（管理页「设置」保存的运行时配置可能覆盖默认 8768）。"""
    path = settings.runtime_config_path
    if path.exists():
        try:
            overrides = json.loads(path.read_text(encoding="utf-8"))
            return int(overrides.get("employee_port") or settings.employee_port)
        except Exception:  # noqa: BLE001
            pass
    return settings.employee_port


def main() -> None:
    multiprocessing.freeze_support()
    settings = get_settings()  # 仅读环境变量，无文件系统副作用

    # 单实例锁：必须最早（数据目录初始化、密钥生成、防火墙、uvicorn 全部之前）。
    # 已存在实例 → 醒目提示并以退出码 0 退出（不是错误，不 traceback）。
    from .core.singleinstance import acquire_single_instance_lock

    if not acquire_single_instance_lock():
        print(
            "=" * 64,
            "许可证服务器已在运行，请勿重复启动。",
            f"管理页：http://{settings.admin_host}:{settings.admin_port}/",
            "=" * 64,
            sep="\n",
            flush=True,
        )
        raise SystemExit(0)

    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # frozen exe 首次启动：UAC 提权放行防火墙（源码运行/非 Windows/失败均不阻断）
    from .core.firewall import ensure_firewall_rule

    ensure_firewall_rule(_effective_employee_port(settings))

    controller = EmployeeServerController(settings)
    admin_app = create_admin_app(settings, controller=controller)

    controller.start_employee()
    if not controller.wait_started():
        # mutex 之外的第二道防线：端口被其它程序/残留进程占用
        print(
            f"端口被占用，服务可能已在运行"
            f"（员工端 {settings.employee_host}:{_effective_employee_port(settings)}）",
            file=sys.stderr,
            flush=True,
        )
        controller.shutdown()
        raise SystemExit(1)

    admin_url = f"http://{settings.admin_host}:{settings.admin_port}/"
    logger.info("管理页: %s", admin_url)
    try:
        webbrowser.open(admin_url)
    except Exception:  # noqa: BLE001
        pass

    admin_config = uvicorn.Config(
        admin_app, host=settings.admin_host, port=settings.admin_port,
        log_level=settings.log_level,
    )
    try:
        uvicorn.Server(admin_config).run()
    except OSError:
        print(
            f"端口被占用，服务可能已在运行（管理端 {settings.admin_host}:{settings.admin_port}）",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
    finally:
        controller.shutdown()


if __name__ == "__main__":
    main()
