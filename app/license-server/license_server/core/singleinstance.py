"""Windows Named Mutex 单实例锁：保证许可证服务器全机只跑一个实例。

背景：2026-07-18 两个 exe 并发启动互相覆盖 .data 密钥的事故
（调研见 docs/research/single-instance-chatgpt.md）。

实现要点：
- Windows：ctypes 调 kernel32 CreateMutexW(None, False, "Local\\CaretLicenseServer")，
  句柄非空且 GetLastError == ERROR_ALREADY_EXISTS(183) → 已有实例在跑。
  CreateMutex 是原子操作，不存在「先检查再创建」的竞争窗口。
  用 Local\\ 而非 Global\\：老板机单用户场景，且避免全局命名空间需要的额外权限。
- 非 Windows：本项目 Windows-only，降级为 no-op（永远抢锁成功）；若未来移植
  Linux/macOS，可在此换成文件锁（fcntl/msvcrt 锁 .data/server.lock）。
- 锁句柄必须进程生命周期内持有（模块级引用 _mutex_handle 防 GC）；
  进程退出（含崩溃）时内核自动关闭句柄并释放 Mutex，无需显式清理。
- CreateMutexW 失败（极少见，如权限异常）：保守放行，由端口绑定兜底
  （8767/8768 已被占用时 uvicorn 起不来，run.py 会报「端口被占用」退出）。
"""
from __future__ import annotations

import ctypes
import sys

MUTEX_NAME = r"Local\CaretLicenseServer"
ERROR_ALREADY_EXISTS = 183

# 模块级句柄：防 GC 回收导致锁提前释放（进程退出由内核自动回收）
_mutex_handle: int | None = None


def acquire_single_instance_lock() -> bool:
    """抢单实例锁。已存在实例 → False；抢到 → True 并持有至进程退出。

    非 Windows 平台永远返回 True（no-op，见模块 docstring）。
    """
    global _mutex_handle
    if sys.platform != "win32":
        return True

    # use_last_error=True：ctypes 保存 LastError 线程局部副本，避免被其它 FFI 调用覆盖
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        # 创建失败（极少见）：不误判为重复实例，放行走端口绑定兜底
        return True
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        # 已有实例持有：关闭本进程拿到的重复句柄，不持有锁
        kernel32.CloseHandle(handle)
        return False
    _mutex_handle = handle
    return True


def release_single_instance_lock() -> None:
    """显式释放（仅测试用）；正常进程退出由内核自动回收，业务代码无需调用。"""
    global _mutex_handle
    if sys.platform != "win32" or _mutex_handle is None:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle(_mutex_handle)
    _mutex_handle = None
