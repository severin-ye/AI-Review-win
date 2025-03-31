# 共用的模块
import json
import sys
import os

# 添加项目根目录到Python路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import (
    prompt,
    module_type,
    openai_api_key,
    tyqw_api_key,
    MODULE_LIST as module_list
)

# openai模块
from openai import OpenAI
# 通义千问模块
from http import HTTPStatus
import dashscope

# 初始化变量
question = ""  # 在auto_answer.py中动态赋值

# openai 配置
client = OpenAI(api_key=openai_api_key)
# 通义千问 配置
dashscope.api_key = tyqw_api_key

# 定义文本审校工具函数Schema
TEXT_REVIEW_TOOL = {
    "type": "function",
    "function": {
        "name": "report_text_issues",
        "description": "识别文本中的错误句子并提出修改建议",
        "parameters": {
            "type": "object",
            "properties": {
                "corrections": {
                    "type": "array",
                    "description": "每项为错误句和修改建议的对应关系",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original": {
                                "type": "string",
                                "description": "原始有错误的句子"
                            },
                            "suggestion": {
                                "type": "string",
                                "description": "修改后的句子"
                            }
                        },
                        "required": ["original", "suggestion"]
                    }
                }
            },
            "required": ["corrections"]
        }
    }
}

# GPT调用函数
def gpt_answer(gpt_question, gpt_api_key, gpt_module_type, gpt_prompt):
    try:
        # 创建并发送请求
        completion = client.chat.completions.create(
            model=gpt_module_type,
            messages=[
                {"role": "system", "content": gpt_prompt},
                {"role": "user", "content": gpt_question}
            ],
            tools=[TEXT_REVIEW_TOOL],
            tool_choice={"type": "function", "function": {"name": "report_text_issues"}}
        )

        # 处理返回内容
        response = completion.choices[0].message
        
        # 如果有工具调用结果
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            if tool_call.function.name == "report_text_issues":
                # 解析JSON结果
                try:
                    corrections_data = json.loads(tool_call.function.arguments)
                    return corrections_data
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    return {"corrections": []}
        
        # 如果没有工具调用结果，返回普通文本
        return {"content": response.content}
    except Exception as e:
        print(f"GPT调用出错：{e}")
        return {"error": "GPT调用出错"}

# 通义千问调用函数
def tyqw_answer(tyqw_question, tyqw_prompt):
    messages = [{'role': 'system', 'content': tyqw_prompt},
                {'role': 'user', 'content': tyqw_question}]

    try:
        response = dashscope.Generation.call(
            dashscope.Generation.Models.qwen_turbo,  # 指定的模型种类
            messages=messages,
            result_format='message',  # set the result to be "message" format.
        )
        if response.status_code == HTTPStatus.OK:
            content = response["output"]["choices"][0]["message"]["content"]
            # 尝试解析通义千问的输出为JSON格式
            try:
                # 查找JSON格式的输出
                json_str = content
                if "```json" in content:
                    # 提取JSON字符串
                    json_str = content.split("```json")[1].split("```")[0].strip()
                
                corrections_data = json.loads(json_str)
                return corrections_data
            except (json.JSONDecodeError, IndexError):
                # 如果无法解析为JSON，返回普通文本
                return {"content": content}
        else:
            print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
            ))
            return {"error": "通义千问模型调用错误"}
    except Exception as e:
        print(f"通义千问调用出错：{e}")
        return {"error": "通义千问调用出错"}

# 添加占位符函数
def add_first_line_indent(text):
    return "[first_line_indent]" + text

# 更新后的总调用函数
def ai_answer(question):
    print("模型类型为：", module_type)
    
    try:
        if module_type == '通义千问':
            # 为通义千问添加特殊提示，要求返回JSON格式
            special_prompt = prompt + "\n\n请以JSON格式返回结果，格式如下：\n```json\n{\n  \"corrections\": [\n    {\n      \"original\": \"原始句子\",\n      \"suggestion\": \"修改建议\"\n    }\n  ]\n}\n```\n如果没有发现错误，请返回空的corrections数组。"
            result = tyqw_answer(question, special_prompt)
        elif module_type in module_list:
            result = gpt_answer(question, openai_api_key, module_type, prompt)
        elif module_type.startswith('gemini'):
            # 未实现
            result = {"error": "Gemini模型尚未实现"}
        else:
            print("模型类型错误")
            result = {"error": "模型类型错误"}
    except Exception as e:
        print(f"AI调用出错：{e}")
        result = {"error": f"AI调用出错: {str(e)}"}

    return result

# 测试
if __name__ == '__main__':
    question = "你能做些什么？"
    a = ai_answer(question)
    print(a)
