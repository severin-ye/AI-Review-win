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

# GPT调用函数
def gpt_answer(gpt_question, gpt_api_key, gpt_module_type, gpt_prompt):
    try:
        # 创建并发送请求
        completion = client.chat.completions.create(
            model=gpt_module_type,
            messages=[
                {"role": "system", "content": gpt_prompt},
                {"role": "user", "content": gpt_question}
            ]
        )

        # 返回回复内容
        return completion.choices[0].message.content
    except Exception as e:
        print(f"GPT调用出错：{e}")
        return "GPT调用出错"

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
            return content
        else:
            print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
            ))
            return "通义千问模型调用错误"
    except Exception as e:
        print(f"通义千问调用出错：{e}")
        return "通义千问调用出错"

# 添加占位符函数
def add_first_line_indent(text):
    return "[first_line_indent]" + text

# 更新后的总调用函数
def ai_answer(question):
    print("模型类型为：", module_type)
    answer = "模型类型错误"  # 添加默认值
    
    try:
        if module_type == '通义千问':
            answer = tyqw_answer(question, prompt)
        elif module_type in module_list:
            answer = gpt_answer(question, openai_api_key, module_type, prompt)
        elif module_type.startswith('gemini'):
            # answer = gemini_pro_answer(question)
            pass
        else:
            print("模型类型错误")
    except Exception as e:
        print(f"AI调用出错：{e}")
        return add_first_line_indent("AI调用出错")

    return add_first_line_indent(answer)

# 测试
if __name__ == '__main__':
    question = "你能做些什么？"
    a = ai_answer(question)
    print(a)
