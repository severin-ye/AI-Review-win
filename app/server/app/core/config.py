"""全局配置：数据目录解析与基础设置。

数据目录优先级：
1. 环境变量 AI_REVIEW_DATA_DIR（显式覆盖，测试/调试使用）
2. 打包后（Electron prod 注入 AI_REVIEW_PACKAGED=1）→ %APPDATA%\\ai-review\\
3. 开发模式 → backend\\.data\\

M5：本地模型目录自动探测——环境变量（AI_REVIEW_SAT_MODEL_PATH 等）仍可显式覆盖；
未设置时若 <data_dir>/models/ 下存在对应模型目录则直接使用，Electron sidecar 因此
无需额外注入环境变量（修复 M2/M3 已知问题：sidecar 读不到本地模型路径）。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"

# 本地模型目录名（<data_dir>/models/ 下；与 hf-mirror 预下载布局一致，见 api/models.py）
SAT_MODEL_DIRNAME = "sat-3l-sm"
SAT_TOKENIZER_DIRNAME = "xlm-roberta-base"
EMBEDDING_MODEL_DIRNAME = "bge-m3"


def _default_data_dir() -> Path:
    env = os.environ.get("AI_REVIEW_DATA_DIR")
    if env:
        return Path(env)
    if os.environ.get("AI_REVIEW_PACKAGED") == "1":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "ai-review"
    return Path(__file__).resolve().parents[2] / ".data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_REVIEW_")

    app_name: str = "ai-review"
    version: str = APP_VERSION
    data_dir: Path = _default_data_dir()

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    def ensure_dirs(self) -> None:
        """按设计文档布局创建 projects/ kb/ models/ 子目录"""
        for sub in ("projects", "kb", "models"):
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings


# ---------- M5：本地模型目录探测（环境变量优先，<data_dir>/models/ 兜底） ----------


def models_dir() -> Path:
    """本地模型根目录 <data_dir>/models/（ensure_dirs 已保证存在）。"""
    return get_settings().data_dir / "models"


def _env_or_default_dir(env_var: str, dirname: str) -> Path | None:
    """环境变量指向的目录存在 → 用之；否则 <data_dir>/models/<dirname> 存在 → 用之；否则 None。"""
    env = os.environ.get(env_var)
    if env and Path(env).exists():
        return Path(env)
    default = models_dir() / dirname
    return default if default.exists() else None


def sat_model_dir() -> Path | None:
    """SaT 分割模型目录（sat-3l-sm）；None 表示回退 HF Hub 自动下载。"""
    return _env_or_default_dir("AI_REVIEW_SAT_MODEL_PATH", SAT_MODEL_DIRNAME)


def sat_tokenizer_dir() -> Path | None:
    """SaT 配套 tokenizer 目录（xlm-roberta-base）；None 时用 HF 名 facebookAI/xlm-roberta-base。"""
    return _env_or_default_dir("AI_REVIEW_SAT_TOKENIZER_PATH", SAT_TOKENIZER_DIRNAME)


def embedding_model_dir() -> Path | None:
    """BGE-M3 embedding 模型目录；None 表示按 settings embedding.model 走 HF Hub。"""
    return _env_or_default_dir("AI_REVIEW_EMBEDDING_MODEL_PATH", EMBEDDING_MODEL_DIRNAME)
