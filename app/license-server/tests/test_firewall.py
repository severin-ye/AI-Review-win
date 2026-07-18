"""firewall.py 单元测试：mock subprocess / ctypes / sys，不真实弹 UAC、不改防火墙。

覆盖：
- 规则已存在 → 不弹提权（ShellExecuteW 未被调用）
- 规则缺失且提权成功 → ShellExecuteW 参数正确（runas/netsh/规则名/端口）+ 复查确认
- 用户取消（返回值 <=32）→ 警告且不抛异常、返回 False
- 非 Windows / 非 frozen / SKIP_FIREWALL=1 → 跳过（不查询、不提权）
- rule_exists 的 netsh 输出解析（中英文"无匹配规则"、含端口规则详情）
"""
from __future__ import annotations

import subprocess
import sys
import time
import types

import pytest

from license_server.core import firewall

PORT = 8768


# ---------- 通用辅助 ----------

class _FakeCompleted:
    def __init__(self, stdout: bytes = b"", stderr: bytes = b""):
        self.stdout = stdout
        self.stderr = stderr


def _enable(monkeypatch):
    """模拟 Windows + frozen exe 环境。"""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("AI_REVIEW_LICENSE_SKIP_FIREWALL", raising=False)


def _mock_shell_execute(monkeypatch, ret: int) -> list:
    """替换 ShellExecuteW，返回指定码；返回调用记录列表。
    firewall.py 在使用处局部 `import ctypes`，补丁打在真实 ctypes 模块的 windll 上即可生效，
    monkeypatch 会在用例结束后还原。"""
    calls = []
    fake_windll = types.SimpleNamespace(
        shell32=types.SimpleNamespace(
            ShellExecuteW=lambda *a: (calls.append(a), ret)[1],
        )
    )
    import ctypes

    monkeypatch.setattr(ctypes, "windll", fake_windll)
    return calls


# ---------- 启用条件 ----------

class TestEnabled:
    def test_skip_when_not_frozen(self, monkeypatch):
        """源码运行（非 frozen）：不查询、不提权。"""
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delattr(sys, "frozen", raising=False)
        called = []
        monkeypatch.setattr(firewall, "rule_exists", lambda p: called.append(p) or True)
        assert firewall.ensure_firewall_rule(PORT) is False
        assert called == []

    def test_skip_when_not_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        called = []
        monkeypatch.setattr(firewall, "rule_exists", lambda p: called.append(p) or True)
        assert firewall.ensure_firewall_rule(PORT) is False
        assert called == []

    def test_skip_when_env_set(self, monkeypatch):
        """AI_REVIEW_LICENSE_SKIP_FIREWALL=1：即使 Windows+frozen 也完全跳过。"""
        _enable(monkeypatch)
        monkeypatch.setenv("AI_REVIEW_LICENSE_SKIP_FIREWALL", "1")
        called = []
        monkeypatch.setattr(firewall, "rule_exists", lambda p: called.append(p) or True)
        assert firewall.ensure_firewall_rule(PORT) is False
        assert called == []


# ---------- rule_exists ----------

class TestRuleExists:
    def test_rule_found_with_port(self, monkeypatch):
        """netsh 输出规则详情（含端口号）→ True，且 subprocess 带 CREATE_NO_WINDOW。"""
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            seen["kwargs"] = kwargs
            detail = (
                'Rule Name:                            AI-Review License Server\r\n'
                'LocalPort:                            8768\r\n'
            ).encode("mbcs", errors="ignore")
            return _FakeCompleted(stdout=detail)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert firewall.rule_exists(PORT) is True
        assert seen["cmd"] == ["netsh", "advfirewall", "firewall", "show", "rule",
                               f"name={firewall.RULE_NAME}"]
        assert seen["kwargs"].get("creationflags") == firewall._CREATE_NO_WINDOW
        assert seen["kwargs"].get("capture_output") is True

    def test_rule_not_found_en(self, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **k: _FakeCompleted(stdout=b"No rules match the specified criteria.\r\n"),
        )
        assert firewall.rule_exists(PORT) is False

    def test_rule_not_found_zh(self, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **k: _FakeCompleted(stdout="没有与指定标准相匹配的规则。\r\n".encode("gbk")),
        )
        assert firewall.rule_exists(PORT) is False

    def test_netsh_failure_returns_false(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("netsh missing")

        monkeypatch.setattr(subprocess, "run", boom)
        assert firewall.rule_exists(PORT) is False


# ---------- ensure_firewall_rule ----------

class TestEnsure:
    def test_already_exists_no_elevation(self, monkeypatch):
        """规则已存在 → 直接返回 True，不触发提权。"""
        _enable(monkeypatch)
        monkeypatch.setattr(firewall, "rule_exists", lambda p: True)
        calls = _mock_shell_execute(monkeypatch, 42)
        assert firewall.ensure_firewall_rule(PORT) is True
        assert calls == []

    def test_missing_rule_elevates_with_correct_args(self, monkeypatch):
        """规则缺失 → ShellExecuteW(runas, netsh, 正确参数) → 复查确认成功。"""
        _enable(monkeypatch)
        checks = []
        monkeypatch.setattr(
            firewall, "rule_exists",
            lambda p: (checks.append(p), len(checks) > 1)[1],  # 先无后有
        )
        monkeypatch.setattr(time, "sleep", lambda s: None)  # 测试不真等
        calls = _mock_shell_execute(monkeypatch, 42)
        assert firewall.ensure_firewall_rule(PORT) is True
        assert len(calls) == 1
        hwnd, verb, exe, args, cwd, show = calls[0]
        assert hwnd is None
        assert verb == "runas"
        assert exe == "netsh"
        assert f'name="{firewall.RULE_NAME}"' in args
        assert f"localport={PORT}" in args
        assert "dir=in" in args and "action=allow" in args and "protocol=TCP" in args
        assert cwd is None and show == 0

    def test_user_cancel_warns_but_does_not_raise(self, monkeypatch, caplog):
        """用户取消 UAC（返回值 <=32）→ 返回 False、记醒目警告、不抛异常、不阻断。"""
        _enable(monkeypatch)
        monkeypatch.setattr(firewall, "rule_exists", lambda p: False)
        calls = _mock_shell_execute(monkeypatch, 5)  # ERROR_ACCESS_DENIED / 用户取消
        with caplog.at_level("WARNING", logger="license_server.core.firewall"):
            assert firewall.ensure_firewall_rule(PORT) is False
        assert len(calls) == 1
        assert any("防火墙规则添加被取消或失败" in m for m in caplog.messages)
        assert any("netsh advfirewall firewall add rule" in m for m in caplog.messages)

    def test_elevation_ok_but_rule_still_missing(self, monkeypatch, caplog):
        """提权成功返回但复查仍无规则 → 警告并返回 False。"""
        _enable(monkeypatch)
        monkeypatch.setattr(firewall, "rule_exists", lambda p: False)
        monkeypatch.setattr(time, "sleep", lambda s: None)
        _mock_shell_execute(monkeypatch, 42)
        with caplog.at_level("WARNING", logger="license_server.core.firewall"):
            assert firewall.ensure_firewall_rule(PORT) is False
        assert any("未检测到防火墙规则" in m for m in caplog.messages)

    def test_unexpected_exception_never_blocks(self, monkeypatch):
        """任意内部异常都不阻断启动。"""
        _enable(monkeypatch)

        def boom(p):
            raise RuntimeError("unexpected")

        monkeypatch.setattr(firewall, "rule_exists", boom)
        assert firewall.ensure_firewall_rule(PORT) is False
