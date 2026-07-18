"""单实例锁（core.singleinstance）与 run.main 重复启动拒绝路径。

约束：不创建真实全局 Mutex（避免影响本机及其它测试进程），ctypes 全部 mock；
happy path 用假 uvicorn.Server，不真绑端口、不阻塞。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from license_server import run as run_module
from license_server.core import singleinstance


class FakeKernel32:
    """kernel32 假身：记录 CreateMutexW / CloseHandle 调用。"""

    def __init__(self, handle: int = 4242) -> None:
        self._handle = handle
        self.created_names: list[str] = []
        self.closed_handles: list[int] = []

    def CreateMutexW(self, _security_attrs, _initial_owner, name):
        self.created_names.append(name)
        return self._handle

    def CloseHandle(self, handle):
        self.closed_handles.append(handle)
        return 1


def _mock_ctypes(monkeypatch: pytest.MonkeyPatch, kernel32: FakeKernel32, last_error: int) -> None:
    fake_ctypes = SimpleNamespace(
        WinDLL=lambda *_args, **_kwargs: kernel32,
        get_last_error=lambda: last_error,
    )
    monkeypatch.setattr(singleinstance, "ctypes", fake_ctypes)
    monkeypatch.setattr(singleinstance.sys, "platform", "win32")


@pytest.fixture(autouse=True)
def _reset_mutex_handle():
    """每个用例结束后清掉模块级句柄，互不影响。"""
    yield
    singleinstance._mutex_handle = None


def test_acquire_success_holds_handle(monkeypatch):
    """正常路径：抢到锁，句柄模块级持有（防 GC），release 时正确关闭。"""
    k32 = FakeKernel32()
    _mock_ctypes(monkeypatch, k32, last_error=0)

    assert singleinstance.acquire_single_instance_lock() is True
    assert k32.created_names == [singleinstance.MUTEX_NAME]
    assert singleinstance._mutex_handle == 4242
    assert k32.closed_handles == []

    singleinstance.release_single_instance_lock()
    assert k32.closed_handles == [4242]
    assert singleinstance._mutex_handle is None


def test_acquire_rejected_when_already_exists(monkeypatch):
    """mutex 已存在（ERROR_ALREADY_EXISTS）→ 拒绝，且不持有、句柄不泄漏。"""
    k32 = FakeKernel32()
    _mock_ctypes(monkeypatch, k32, last_error=singleinstance.ERROR_ALREADY_EXISTS)

    assert singleinstance.acquire_single_instance_lock() is False
    assert singleinstance._mutex_handle is None
    assert k32.closed_handles == [4242]


def test_acquire_permissive_when_create_fails(monkeypatch):
    """CreateMutexW 返回 NULL（极少见）→ 保守放行，交给端口绑定兜底。"""
    k32 = FakeKernel32(handle=0)
    _mock_ctypes(monkeypatch, k32, last_error=0)

    assert singleinstance.acquire_single_instance_lock() is True
    assert singleinstance._mutex_handle is None


def test_non_windows_is_noop(monkeypatch):
    """非 Windows：no-op 永远成功，完全不触碰 Win32 API。"""
    k32 = FakeKernel32()
    _mock_ctypes(monkeypatch, k32, last_error=0)
    monkeypatch.setattr(singleinstance.sys, "platform", "linux")

    assert singleinstance.acquire_single_instance_lock() is True
    assert k32.created_names == []


def test_main_rejects_second_instance(monkeypatch, capsys, tmp_path):
    """mutex 已存在 → 醒目中文提示 + 退出码 0，且拒绝发生在数据目录初始化之前。"""
    monkeypatch.setattr(singleinstance, "acquire_single_instance_lock", lambda: False)
    monkeypatch.setenv("AI_REVIEW_LICENSE_DATA_DIR", str(tmp_path / "data"))

    with pytest.raises(SystemExit) as exc_info:
        run_module.main()

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "许可证服务器已在运行，请勿重复启动。" in out
    assert "管理页：http://127.0.0.1:8767/" in out
    assert not (tmp_path / "data").exists()


def test_main_bootstrap_happy_path(monkeypatch, workspace):
    """正常路径：抢到锁后继续完整启动流程（假 uvicorn.Server，不真绑端口）。"""
    created_configs: list[object] = []

    class _FakeServer:
        def __init__(self, config):
            self.config = config
            self.started = True
            created_configs.append(config)

        def run(self):
            return None

    monkeypatch.setattr(singleinstance, "acquire_single_instance_lock", lambda: True)
    monkeypatch.setattr(run_module.uvicorn, "Server", _FakeServer)
    monkeypatch.setattr(run_module.webbrowser, "open", lambda *_args, **_kwargs: True)
    monkeypatch.setenv("AI_REVIEW_LICENSE_ADMIN_PORT", "8977")
    monkeypatch.setenv("AI_REVIEW_LICENSE_EMPLOYEE_PORT", "8978")

    run_module.main()  # 应正常返回（不 SystemExit、不异常）

    assert workspace.exists()  # 数据目录已初始化
    assert any(getattr(c, "port", None) == 8977 for c in created_configs)  # admin 用 8977
    assert any(getattr(c, "port", None) == 8978 for c in created_configs)  # employee 用 8978
