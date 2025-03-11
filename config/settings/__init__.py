"""
配置文件模块
"""

import os
import json
from ..managers import path_manager

def load_theme():
    """加载主题配置"""
    try:
        with open(path_manager.theme_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        import logging
        logging.error(f"加载主题配置失败：{str(e)}")
        return {}

theme_config = load_theme()

__all__ = ['theme_config'] 