# 共用的模块
import json
from config import prompt, module_type

# openai模块
from openai import OpenAI
from config import openai_api_key
# 通义千问模块
from http import HTTPStatus
import dashscope
from config import tyqw_api_key

# 从s_config_use.py中导入模型列表
from s_config_use import module_list

# 共用的配置
prompt = prompt
module_type = module_type
question = ""  # 在auto_answer.py中动态赋值

# openai 配置
gpt_api_key = openai_api_key
# 通义千问 配置
dashscope.api_key = tyqw_api_key

# GPT调用函数
def gpt_answer(gpt_question, gpt_api_key, gpt_module_type, gpt_prompt):
    # 创建 OpenAI 客户端实例
    client = OpenAI(api_key=gpt_api_key)

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

# 通义千问调用函数
def tyqw_answer(tyqw_question, tyqw_prompt):
    messages = [{'role': 'system', 'content': tyqw_prompt},
                {'role': 'user', 'content': tyqw_question}]

    response = dashscope.Generation.call(
        dashscope.Generation.Models.qwen_turbo,  # 指定的模型种类
        messages=messages,
        result_format='message',  # set the result to be "message" format.
    )
    if response.status_code == HTTPStatus.OK:
        content = response["output"]["choices"][0]["message"]["content"]
        # print(content)
    else:
        print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))
        content = "通义千问模型调用错误, 可能是有敏感词汇"

    return content

# 更新后的总调用函数
def ai_answer(question):
    print("模型类型为：", module_type)
    answer = "模型类型错误"  # 添加默认值
    if module_type in module_list:
        answer = gpt_answer(question, gpt_api_key, module_type, prompt)
    elif module_type == '通义千问':
        answer = tyqw_answer(question, prompt)
    elif module_type.startswith('gemini'):
        # answer = gemini_pro_answer(question)
        pass
    else:
        print("模型类型错误")

    return answer

# 测试
if __name__ == '__main__':
    question = "你能做些什么？"
    a = ai_answer(question)
    print(a)
