import os
import sys
import json

def get_config_file_path():
    """获取配置文件的路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        application_path = os.path.dirname(sys.executable)
    else:
        # 如果是开发环境
        application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(application_path, "hide_file", "配置文件", "config.json")

try:
    # 获取 JSON 文件的路径
    config_file_path = get_config_file_path()

    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_file_path):
        default_config = {
            "api_keys": {
                "openai": "",
                "tyqw": ""
            },
            "module_type": "gpt-4o",
            "has_review_table": True,
            "prompt": "你是一个专业的文档审校助手。请仔细审查以下文本，并提供修改建议。"
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
        
        # 写入默认配置
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

    # 读取并解析 JSON 数据
    with open(config_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 提取并保存所需的变量
    openai_api_key = data["api_keys"]["openai"]
    tyqw_api_key = data["api_keys"]["tyqw"]
    module_type = data["module_type"]
    prompt = data["prompt"]
    has_review_table = 'Y' if data["has_review_table"] else 'N'

except Exception as e:
    print(f"加载配置文件时出错：{str(e)}")
    # 设置默认值
    openai_api_key = ""
    tyqw_api_key = ""
    module_type = "gpt-4o"
    prompt = "你是一个专业的文档审校助手。请仔细审查以下文本，并提供修改建议。"
    has_review_table = 'Y'

# 以下代码用于测试
if __name__ == '__main__':
    print(f"配置文件路径: {config_file_path}")
    print(f"openai_api_key: {openai_api_key}")
    print(f"tyqw_api_key: {tyqw_api_key}")
    print(f"module_type: {module_type}")
    print(f"prompt: {prompt}")
    print(f"has_review_table: {has_review_table}")


