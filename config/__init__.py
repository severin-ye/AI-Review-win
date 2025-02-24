"""
配置管理模块
"""

from .config_manager import config_manager

# 导出配置变量
has_review_table = False
module_type = 'gpt-4o'
openai_api_key = ''
tyqw_api_key = ''
prompt = ''

def load_config():
    """加载配置并更新全局变量"""
    global has_review_table, module_type, openai_api_key, tyqw_api_key, prompt
    
    # 从配置文件中加载配置
    config_manager.load_config()
    
    # 更新全局变量
    has_review_table = config_manager.config_vars.get('has_review_table', 'Y') == 'Y'
    module_type = config_manager.config_vars.get('module_type', 'gpt-4o')
    openai_api_key = config_manager.config_vars.get('openai_api_key', '')
    tyqw_api_key = config_manager.config_vars.get('tyqw_api_key', '')
    if config_manager.prompt_text:
        prompt = config_manager.prompt_text.get('1.0', 'end-1c')

# 初始加载配置
load_config() 