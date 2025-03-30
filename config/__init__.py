"""
全局配置模块

提供所有配置相关功能、常量和实例
"""

import os
import sys
from .managers import path_manager, config_manager

try:
    # 加载配置
    config = config_manager.load_config()
    
    # 导出API密钥
    openai_api_key = config.get("openai_api_key", "")
    tyqw_api_key = config.get("tyqw_api_key", "")
    
    # 导出其他配置
    module_type = config.get("module_type", "gpt-4o")
    has_review_table = config.get("has_review_table", "Y")
    prompt = config.get("prompt", "")
    output_dir = config.get("output_dir", "")
    
    # 医学RAG系统配置
    enable_medical_rag = config.get("enable_medical_rag", False)
    
    # 创建示例参考文档目录
    medical_docs_dir = os.path.join(os.getcwd(), "_4_医学参考文档")
    if not os.path.exists(medical_docs_dir):
        os.makedirs(medical_docs_dir)
        # 创建README文件
        readme_path = os.path.join(medical_docs_dir, "README.txt")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("医学参考文档目录\n\n")
            f.write("请将医学参考文档（PDF、TXT、CSV）放在此目录下\n")
            f.write("系统将自动索引这些文档并在审校医学文本时提供参考信息\n")
    
except Exception as e:
    print(f"加载配置时出错: {e}")
    # 设置默认值
    openai_api_key = ""
    tyqw_api_key = ""
    module_type = "gpt-4o"
    has_review_table = "Y"
    prompt = ""
    output_dir = ""
    enable_medical_rag = False

# 导出配置变量
__all__ = [
    'config_manager',
    'path_manager',
    'openai_api_key',
    'tyqw_api_key',
    'module_type',
    'has_review_table',
    'prompt',
    'output_dir',
    'enable_medical_rag'
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