"""运行配置：pydantic-settings，环境变量前缀 AI_REVIEW_LICENSE_。

默认数据目录为 app/license-server/.data（可用 AI_REVIEW_LICENSE_DATA_DIR 覆盖，
测试里每个用例指向独立临时目录）。
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# app/license-server/
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
# 仓库根（app/license-server/../..）
REPO_ROOT = PACKAGE_ROOT.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_REVIEW_LICENSE_")

    # 数据目录（SQLite、密钥、运行时配置都放这里）
    data_dir: Path = PACKAGE_ROOT / ".data"

    # 管理端监听（仅本机）
    admin_host: str = "127.0.0.1"
    admin_port: int = 8767
    # 员工端监听（默认对局域网开放）
    employee_host: str = "0.0.0.0"
    employee_port: int = 8768

    # DEV 密钥标记：默认 True（开发期），生产部署显式置 0
    dev_keys: bool = True

    log_level: str = "info"

    # activate 固定窗口限流：每 IP 每分钟次数
    rate_limit_per_minute: int = 10

    # 心跳建议间隔 / 客户端时间戳容差（秒）
    heartbeat_interval_seconds: int = 300
    timestamp_tolerance_seconds: int = 300

    @property
    def db_path(self) -> Path:
        return self.data_dir / "license.db"

    @property
    def keys_dir(self) -> Path:
        return self.data_dir / "keys"

    @property
    def runtime_config_path(self) -> Path:
        """设置页保存的运行时覆盖配置（监听地址/端口/仅局域网/日志级别）。"""
        return self.data_dir / "server_config.json"


def get_settings() -> Settings:
    """每次调用重新读环境变量（测试通过 monkeypatch env 后重建 app 生效）。"""
    return Settings()
