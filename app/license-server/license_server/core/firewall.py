"""Windows 防火墙自动放行（仅 PyInstaller frozen exe 启用）。

背景：员工 API 监听 0.0.0.0:8768，员工电脑要连进来需要 Windows 防火墙放行。
打包成 exe 后，首次启动检查规则是否存在，缺失则通过 ShellExecuteW("runas")
触发一次 UAC 提权窗口自动添加——老板只需点「是」。

设计约束：
- 仅 Windows 且 frozen（getattr(sys, "frozen", False)）时启用；源码运行不弹
  （开发者自己会处理防火墙）。
- 用户取消或失败：只记醒目警告日志，绝不阻断服务器启动。
- 每次启动都检查（规则可能被人删掉），已存在则静默跳过。
- AI_REVIEW_LICENSE_SKIP_FIREWALL=1 完全跳过（自动化测试/特殊部署用）。
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time

logger = logging.getLogger("license_server.core.firewall")

RULE_NAME = "Caret License Server"

# 子进程不弹黑色控制台窗口
_CREATE_NO_WINDOW = 0x08000000

# ShellExecuteW 返回值 <= 32 表示失败（如 5=ERROR_ACCESS_DENIED 用户取消 UAC）
_SHELL_EXECUTE_SUCCESS_MIN = 32


def _firewall_enabled() -> bool:
    """是否启用自动放行：Windows + frozen exe + 未被环境变量禁用。"""
    if os.environ.get("AI_REVIEW_LICENSE_SKIP_FIREWALL") == "1":
        return False
    return sys.platform == "win32" and getattr(sys, "frozen", False)


def _decode_console_output(data: bytes) -> str:
    """netsh 输出为系统 OEM/ANSI 代码页（cp936/cp437 等），端口数字 ASCII 安全。"""
    for encoding in ("mbcs", "utf-8"):
        try:
            return data.decode(encoding, errors="ignore")
        except (LookupError, ValueError):
            continue
    return data.decode("utf-8", errors="ignore")


def rule_exists(port: int) -> bool:
    """用 netsh show rule 判断放行本端口的规则是否已存在。查询失败按不存在处理。"""
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_NAME}"],
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        logger.warning("查询防火墙规则失败（netsh 不可用？），按规则不存在处理")
        return False
    output = _decode_console_output(result.stdout) + _decode_console_output(result.stderr)
    # 无匹配规则时输出只有「没有与指定标准相匹配的规则/No rules match...」（不含端口号）；
    # 有匹配时输出规则详情（含 LocalPort/本地端口 = 端口号，数字 ASCII 安全）
    return str(port) in output


def _manual_hint(port: int) -> str:
    return (
        f'可稍后以管理员身份打开 PowerShell 手动执行：\n'
        f'netsh advfirewall firewall add rule name="{RULE_NAME}" dir=in action=allow '
        f'protocol=TCP localport={port}'
    )


def ensure_firewall_rule(port: int) -> bool:
    """确保防火墙放行规则存在；缺失则 UAC 提权添加。返回规则是否最终可用。

    任何失败都只记日志、返回 False，不阻断服务器启动。
    """
    if not _firewall_enabled():
        return False
    try:
        if rule_exists(port):
            logger.info("防火墙放行规则已存在：%s（TCP %d）", RULE_NAME, port)
            return True

        logger.warning(
            "首次运行需要放行防火墙端口 %d，即将弹出「用户账户控制」窗口，请点击「是」……", port
        )
        import ctypes

        args = (
            f'advfirewall firewall add rule name="{RULE_NAME}" dir=in action=allow '
            f"protocol=TCP localport={port}"
        )
        # SW_HIDE=0：netsh 执行完即退出，不留窗口
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "netsh", args, None, 0)
        if rc <= _SHELL_EXECUTE_SUCCESS_MIN:
            logger.warning(
                "防火墙规则添加被取消或失败（返回值 %d）。员工将无法连接本机 %d 端口！\n%s",
                rc,
                port,
                _manual_hint(port),
            )
            return False

        # 提权进程异步执行，稍候复查确认
        time.sleep(2)
        if rule_exists(port):
            logger.info("防火墙放行规则已添加：%s（TCP %d）", RULE_NAME, port)
            return True
        logger.warning(
            "提权命令已执行但未检测到防火墙规则，员工可能无法连接本机 %d 端口。\n%s",
            port,
            _manual_hint(port),
        )
        return False
    except Exception:  # noqa: BLE001
        logger.exception("防火墙自动放行异常（已忽略，不影响服务器启动）。\n%s", _manual_hint(port))
        return False
