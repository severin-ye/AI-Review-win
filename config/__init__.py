"""
配置管理模块
"""

import json
import os
import sys

def get_config_file_path():
    """获取配置文件的路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        application_path = os.path.dirname(sys.executable)
    else:
        # 如果是开发环境
        application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    config_dir = os.path.join(application_path, "hide_file", "配置文件")
    return os.path.join(config_dir, "config.json")

# 初始化默认配置
has_review_table = True
module_type = 'gpt-4o'
openai_api_key = ''
tyqw_api_key = ''
prompt = '你是一个专业的文档审校助手。请仔细审查以下文本，并提供修改建议。'

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