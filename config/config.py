import os
import sys
import json

def get_config_file_path():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    else:
        application_path = os.getcwd()  # 作为默认路径

    return os.path.join(application_path, "hide_file", "配置文件", "config.json")

# 获取 JSON 文件的路径
config_file_path = get_config_file_path()

# 读取并解析 JSON 数据
with open(config_file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# 提取并保存所需的变量
openai_api_key = data["api_keys"]["openai"]
tyqw_api_key = data["api_keys"]["tyqw"]
module_type = data["module_type"]
prompt = data["prompt"]
has_review_table = 'Y' if data["has_review_table"] else 'N'

# 以下代码用于测试
if __name__ == '__main__':
    print(f"openai_api_key: {openai_api_key}")
    print(f"tyqw_api_key: {tyqw_api_key}")
    print(f"module_type: {module_type}")
    print(f"prompt: {prompt}")
    print(f"has_review_table: {has_review_table}")


