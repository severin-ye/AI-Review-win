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
    "output_dir": "输出目录",
    "enable_medical_rag": "启用医学RAG系统"
}

LABEL_WIDTH = 20
ENTRY_WIDTH = 30
PROMPT_TEXT_HEIGHT = 10
PROMPT_TEXT_WIDTH = 50
BUTTON_PAD_Y = 30

# ====================================================
# 默认值
# ====================================================
DEFAULT_PROMPT = """你是一个文本审校助手。用户会提供一段中文文本，该文本中可能包含如下几类问题：

1. 事实性错误：比如地理、历史、常识不准确
2. 语法错误：病句、语序、搭配、标点等语法问题
3. 格式错误：用词重复、不合逻辑、表达混乱等非标准写法

请逐句检查文本内容是否存在上述错误。如果发现问题，返回每一句有错误的句子及其修改建议。如果完全没有错误，请返回空的corrections列表。

务必按照以下JSON格式输出结果：
{
  "corrections": [
    {
      "original": "（原始有问题的句子）",
      "suggestion": "（你建议修改后的版本）"
    }
    // 可包含多个句子对
  ]
}

如没有发现任何错误，返回：{"corrections": []}
"""

DEFAULT_MEDICAL_PROMPT = """你是一个专业的医学文档审校助手。请仔细审查以下文本，并根据医学参考信息进行事实性判断，提供准确的修改建议。

请关注以下几类问题：
1. 医学事实性错误：比如疾病描述、药物用量、治疗方法等专业信息是否准确
2. 医学术语使用错误：术语是否规范，是否存在过时或不准确的表述
3. 语法和格式问题：是否存在表达不清、逻辑混乱等影响理解的问题

请逐句检查文本内容是否存在上述错误。如果发现问题，返回每一句有错误的句子及其修改建议。如果完全没有错误，请返回空的corrections列表。

务必按照以下JSON格式输出结果：
{
  "corrections": [
    {
      "original": "（原始有问题的句子）",
      "suggestion": "（你建议修改后的版本）"
    }
    // 可包含多个句子对
  ]
}

如没有发现任何错误，返回：{"corrections": []}
"""

# ====================================================
# RAG系统配置
# ====================================================
DEFAULT_ENABLE_MEDICAL_RAG = False
MEDICAL_EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"

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
    'DEFAULT_MEDICAL_PROMPT',
    'DEFAULT_ENABLE_MEDICAL_RAG',
    'MEDICAL_EMBEDDING_MODEL',
    'VERSION'
] 