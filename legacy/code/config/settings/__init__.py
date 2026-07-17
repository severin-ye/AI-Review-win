"""
配置文件模块
"""

import os
import json
from ..managers.path_manager import path_manager

# 加载主题配置
def load_theme():
    """加载主题配置"""
    try:
        with open(path_manager.theme_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        import logging
        logging.error(f"加载主题配置失败：{str(e)}")
        return {}

# 加载应用配置
def load_app_config():
    """加载应用配置"""
    try:
        with open(path_manager.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        import logging
        logging.error(f"加载应用配置失败：{str(e)}")
        return {}

theme_config = load_theme()
app_config = load_app_config()

__all__ = ['theme_config', 'app_config', 'load_theme', 'load_app_config'] 