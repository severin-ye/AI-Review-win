"""
配置管理模块
"""

import os
import sys
import json
import logging
from .core import config_manager, path_manager
from .constants import MODULE_LIST, DEFAULT_PROMPT
from .settings import theme_config

# 加载配置
try:
    config_data = config_manager.load_config()
    has_review_table = config_data.get('has_review_table', True)
    module_type = config_data.get('module_type', MODULE_LIST[0])
    openai_api_key = config_data.get('api_keys', {}).get('openai', '')
    tyqw_api_key = config_data.get('api_keys', {}).get('tyqw', '')
    prompt = config_data.get('prompt', DEFAULT_PROMPT)
except Exception as e:
    logging.error(f"加载配置失败：{str(e)}")
    has_review_table = True
    module_type = MODULE_LIST[0]
    openai_api_key = ''
    tyqw_api_key = ''
    prompt = DEFAULT_PROMPT

__all__ = [
    'path_manager',
    'config_manager',
    'theme_config',
    'has_review_table',
    'module_type',
    'openai_api_key',
    'tyqw_api_key',
    'prompt',
    'MODULE_LIST'
]

def get_config_file_path():
    """获取配置文件的路径"""
    return path_manager.config_file

# 加载配置文件
try:
    config_path = get_config_file_path()
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            has_review_table = config.get('has_review_table', True)
            module_type = config.get('module_type', 'gpt-4o')
            openai_api_key = config.get('api_keys', {}).get('openai', '')
            tyqw_api_key = config.get('api_keys', {}).get('tyqw', '')
            prompt = config.get('prompt', prompt)
except Exception as e:
    print(f"加载配置文件时出错：{e}") 