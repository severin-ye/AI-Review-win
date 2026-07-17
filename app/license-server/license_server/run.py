"""入口：同进程起两个 uvicorn Server。

- admin    仅 127.0.0.1:8767（可用 AI_REVIEW_LICENSE_ADMIN_HOST/PORT 改）
- employee 0.0.0.0:8768（可用 AI_REVIEW_LICENSE_EMPLOYEE_HOST/PORT 改，
  或管理页「设置」里保存的运行时配置覆盖）
启动后自动打开浏览器到管理页。employee 监听可被管理 API 启动/停止（admin 进程不死）。
"""
from __future__ import annotations

import json
import logging
import multiprocessing
import threading
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
            thread = threading.Thread(target=server.run, name="employee-server", daemon=True)
            self._server = server
            self._thread = thread
            thread.start()
            logger.info("员工端监听已启动: http://%s:%d", host, port)

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


def main() -> None:
    multiprocessing.freeze_support()
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    controller = EmployeeServerController(settings)
    admin_app = create_admin_app(settings, controller=controller)

    controller.start_employee()

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
    finally:
        controller.shutdown()


if __name__ == "__main__":
    main()
