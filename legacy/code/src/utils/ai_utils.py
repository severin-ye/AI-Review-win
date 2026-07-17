# 共用的模块
import json
import sys
import os
import openai
from openai import OpenAI  # 导入新版本的 OpenAI 客户端
import time
import logging
import httpx  # OpenAI 使用 httpx 作为 HTTP 客户端
from typing import Dict, Any, Optional

# 控制变量
SHOW_MODEL_INFO = False  # 控制是否显示模型类型和HTTP请求信息
SHOW_HTTP_LOG = False   # 控制是否显示 HTTP 请求日志

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 设置各个模块的日志级别
if not SHOW_HTTP_LOG:
    logging.getLogger("openai").setLevel(logging.WARNING)  # OpenAI 的日志
    logging.getLogger("httpx").setLevel(logging.WARNING)   # HTTPX 的日志
    logging.getLogger("httpcore").setLevel(logging.WARNING)  # HTTPCore 的日志

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

# 通义千问模块
from http import HTTPStatus
import dashscope

# 初始化变量
question = ""  # 在auto_answer.py中动态赋值

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

# 定义function calling的schema
FUNCTION_SCHEMAS = {
    "analyze_paragraphs": {
        "name": "analyze_paragraphs",
        "description": "分析段落间的语义关联性",
        "parameters": {
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "array",
                    "description": "每个段落的分析结果",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "段落的主题概述"
                            },
                            "relation_score": {
                                "type": "number",
                                "description": "与上一段落的关联度（0-1）",
                                "minimum": 0,
                                "maximum": 1
                            },
                            "should_merge": {
                                "type": "boolean",
                                "description": "是否建议与上一段落合并"
                            }
                        },
                        "required": ["topic", "relation_score", "should_merge"]
                    }
                }
            },
            "required": ["analysis"]
        }
    }
}

# GPT调用函数
def gpt_answer(gpt_question, gpt_api_key, gpt_module_type, gpt_prompt):
    try:
        # 创建OpenAI客户端
        client = OpenAI(api_key=gpt_api_key)
        
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

def ai_answer(text: str) -> Optional[Dict[str, Any]]:
    """调用AI接口获取审校结果
    
    Args:
        text: 待审校的文本
        
    Returns:
        包含审校结果的字典，如果出错则返回None
    """
    try:
        # 创建OpenAI客户端
        client = OpenAI(api_key=openai_api_key)
        
        # 构建提示
        current_prompt = f"请审校以下文本，找出其中可能存在的问题并给出修改建议：\n\n{text}"
        
        # 调用API（新版本的调用方式）
        response = client.chat.completions.create(
            model=module_type,  # 使用从config导入的模型类型
            messages=[
                {"role": "system", "content": prompt},  # 使用从config导入的系统提示
                {"role": "user", "content": current_prompt}
            ],
            tools=[TEXT_REVIEW_TOOL],
            tool_choice={"type": "function", "function": {"name": "report_text_issues"}}
        )
        
        # 仅在SHOW_MODEL_INFO为True时显示模型信息
        if SHOW_MODEL_INFO:
            logging.info(f"模型类型为： {response.model}")
            logging.info(f"HTTP请求信息： {response.system_fingerprint}")
        
        # 处理返回内容
        response_message = response.choices[0].message
        
        # 如果有工具调用结果
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            if tool_call.function.name == "report_text_issues":
                # 解析JSON结果
                try:
                    corrections_data = json.loads(tool_call.function.arguments)
                    return corrections_data
                except json.JSONDecodeError as e:
                    logging.error(f"JSON解析错误: {e}")
                    return {"corrections": []}
        
        # 如果没有工具调用结果，返回普通文本
        return {"content": response_message.content}
        
    except Exception as e:
        logging.error(f"AI接口调用出错: {str(e)}")
        return None

# 测试
if __name__ == '__main__':
    question = "你能做些什么？"
    a = ai_answer(question)
    print(a)
