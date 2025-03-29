"""
全局常量配置
"""

# ====================================================
# AI模型配置
# ====================================================
MODULE_LIST = ['gpt-4o', 'gpt-4o-mini', '通义千问']

# ====================================================
# UI配置
# ====================================================
LABEL_NAMES = {
    "openai_api_key": "OpenAI API Key",
    "tyqw_api_key": "通义千问 API Key",
    "module_type": "Module Type",
    "prompt": "Prompt",
    "has_review_table": "有无审校表格",
    "output_dir": "输出目录"
}

LABEL_WIDTH = 20
ENTRY_WIDTH = 30
PROMPT_TEXT_HEIGHT = 10
PROMPT_TEXT_WIDTH = 50
BUTTON_PAD_Y = 30

# ====================================================
# 默认值
# ====================================================
DEFAULT_PROMPT = "你是一个专业的文档审校助手。请仔细审查以下文本，并提供修改建议。"

# ====================================================
# 版本信息
# ====================================================
VERSION = "1.0.0"

__all__ = [
    'MODULE_LIST',
    'LABEL_NAMES',
    'LABEL_WIDTH',
    'ENTRY_WIDTH',
    'PROMPT_TEXT_HEIGHT',
    'PROMPT_TEXT_WIDTH',
    'BUTTON_PAD_Y',
    'DEFAULT_PROMPT',
    'VERSION'
] 