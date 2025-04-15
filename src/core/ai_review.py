# 导入必要的模块
import os  # 操作系统相关功能模块
import time  # 时间相关功能模块
import re  # 正则表达式模块，用于字符串匹配和替换
import sys  # 系统特定参数和功能模块
import json  # JSON处理模块
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from docx import Document  # 处理Word文档的模块
from lxml import etree  # 用于处理XML和HTML的模块
from config import has_review_table, enable_medical_rag, path_manager  # 导入配置项

# 导入工具模块
from src.utils.file_utils import traverse_folder, generate_path, remove_middle_folder
from src.utils.table_utils import extract_tables_from_word, replace_tables, replace_placeholders_with_tables, remove_first_table
from src.utils.docx_utils import convert_file_md
from src.utils.text_utils import divide_text_with_indent
from src.utils.semantic_divider import divide_text_semantically  # 导入新的语义分割器
from src.utils.ai_utils import ai_answer
from src.utils.rag_utils import initialize_rag, get_medical_verification  # 导入RAG系统
from src.core.r2_framework import R2Framework  # 导入 R² 框架

# 添加彩色输出的ANSI转义序列
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

class AIReviewer:
    """AI审校类，用于处理文本审校功能"""
    
    def __init__(self, use_medical_rag=False, llm_client=None):
        """初始化AI审校器
        
        Args:
            use_medical_rag: 是否使用医学RAG系统
            llm_client: OpenAI客户端实例
        """
        self.use_medical_rag = use_medical_rag
        self.llm_client = llm_client
        # 如果启用医学RAG，初始化RAG系统
        if self.use_medical_rag:
            initialize_rag()
        # 初始化 R² 框架
        if self.llm_client:
            self.r2_framework = R2Framework(self.llm_client)
        else:
            self.r2_framework = None
    
    def review_text(self, text):
        """审校单个文本
        
        Args:
            text (str): 待审校的文本
            
        Returns:
            dict: 审校结果，包含corrections列表或content/error字段
        """
        try:
            # 如果启用医学RAG，获取医学上下文信息
            medical_context = ""
            if self.use_medical_rag:
                medical_context = get_medical_verification(text)
                if medical_context and medical_context != "未找到相关医学参考信息。":
                    # 将医学上下文添加到提示中
                    augmented_text = f"请审校以下文本，并参考提供的医学参考信息进行医学事实性判断。\n\n{medical_context}\n\n待审校文本:\n{text}"
                    result = ai_answer(augmented_text)
                else:
                    result = ai_answer(text)
            else:
                result = ai_answer(text)
                
            if result is None:
                raise Exception("AI审校返回空结果")
                
            # 添加处理方式标识
            result['processing_method'] = '传统方式'
            return result
        except Exception as e:
            print(f"处理文本时出错: {e}")
            return {"error": f"处理文本时出错: {str(e)}", "processing_method": "传统方式"}
    
    def process_with_r2(self, text, support_text=None):
        """使用 R² 框架处理文本
        
        Args:
            text (str): 待处理的文本
            support_text (str, optional): 支持文本
            
        Returns:
            dict: 处理结果
        """
        if not self.r2_framework:
            return {"error": "R² 框架未初始化，请确保提供了 OpenAI 客户端", "processing_method": "R² 框架（初始化失败）"}
            
        try:
            # 使用 R² 框架处理文本
            result = self.r2_framework.process(text, support_text)
            if not result:
                return {"error": "R² 框架处理返回空结果", "processing_method": "R² 框架"}
            
            # 导出结果为文本格式
            try:
                formatted_result = self.r2_framework.export_results(result, "text")
                if not formatted_result:
                    print("警告：导出结果为空")
                    formatted_result = "结果导出为空"
            except Exception as e:
                print(f"导出结果时出错: {str(e)}")
                formatted_result = f"结果导出失败: {str(e)}"
            
            # 构建审校结果
            corrections = []
            try:
                if hasattr(result, 'refined_scenes') and result.refined_scenes:
                    for scene in result.refined_scenes:
                        if hasattr(scene, 'suggestions') and scene.suggestions:
                            for suggestion in scene.suggestions:
                                try:
                                    corrections.append({
                                        "original": getattr(scene.original, 'content', '未知原文'),
                                        "suggestion": getattr(scene, 'refined_content', '未知修改建议'),
                                        "category": getattr(suggestion, 'category', '未分类'),
                                        "importance": float(getattr(suggestion, 'importance', 1.0))
                                    })
                                except Exception as e:
                                    print(f"处理单个修改建议时出错: {str(e)}")
                                    continue
            except Exception as e:
                print(f"处理修改建议时出错: {str(e)}")
            
            # 如果没有任何修改建议，添加一个默认的"无需修改"建议
            if not corrections:
                corrections.append({
                    "original": text,
                    "suggestion": text,
                    "category": "无需修改",
                    "importance": 1.0
                })
            
            return {
                "corrections": corrections,
                "r2_result": formatted_result,
                "confidence": float(getattr(result, 'confidence', 0.0)),
                "processing_method": "R² 框架"
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"R² 框架处理文本时出错: {error_msg}")
            # 如果是JSON相关错误，尝试使用传统方式处理
            if "JSON" in error_msg or "events" in error_msg:
                try:
                    result = self.review_text(text)
                    result['processing_method'] = 'R² 框架（回退到传统方式）'
                    return result
                except Exception as fallback_error:
                    return {
                        "error": f"R² 框架处理失败，回退处理也失败: {str(fallback_error)}", 
                        "processing_method": "R² 框架（回退失败）"
                    }
            return {
                "error": f"R² 框架处理失败: {error_msg}",
                "processing_method": "R² 框架（处理失败）"
            }
    
    def format_review_result(self, result, original_text):
        """格式化审校结果为易读形式
        
        Args:
            result (dict): 审校结果
            original_text (str): 原始文本
            
        Returns:
            str: 格式化后的结果文本
        """
        formatted_output = ""
        
        # 处理错误情况
        if "error" in result:
            return f"[first_line_indent]处理出错: {result['error']}"
        
        # 处理 R² 框架的结果
        if "r2_result" in result:
            return f"[first_line_indent]{result['r2_result']}"
        
        # 处理结构化修改建议
        if "corrections" in result and isinstance(result["corrections"], list):
            corrections = result["corrections"]
            
            if not corrections:  # 空列表表示无需修改
                return f"[first_line_indent]文本无需修改，未发现问题。"
            
            formatted_output = "\n"
            for i, correction in enumerate(corrections, 1):
                formatted_output += f"{i}. 原文：{correction['original']}\n"
                formatted_output += f"   修改：{correction['suggestion']}\n"
                if "category" in correction:
                    formatted_output += f"   类型：{correction['category']}\n"
                formatted_output += "\n"
            
            return formatted_output
        
        # 如果没有结构化的修改建议，返回错误信息
        return f"[first_line_indent]无法处理的结果格式: {json.dumps(result, ensure_ascii=False)}"

# 定义处理文件的函数
def process_file(file_name, file_type, progress_callback=None, llm_client=None):
    # 添加彩色输出的ANSI转义序列
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    print(f"\n{BLUE}{BOLD}开始处理文件{RESET}")
    print(f"{BLUE}文件名: {RESET}{file_name}")
    print(f"{BLUE}文件类型: {RESET}{file_type}")
    print(f"{BLUE}处理方式: {RESET}{'R² 框架' if llm_client else '传统方式'}")
    print(f"{BLUE}{'='*50}{RESET}\n")  # 添加分隔线

    # 生成各路径变量
    paths = generate_path(file_name)
    begin_path = paths['begin_path']
    no_table = paths['no_table']
    path_extract = paths['path_extract']
    md_path = paths['md_path'] 
    ai_path = paths['ai_path']
    word_path_1 = paths['word_path_1']
    word_path_2 = paths['word_path_2']
    final_path_1 = paths['final_path_1']
    final_path_2 = paths['final_path_2']
    select_path_1 = paths['select_path_1']
    select_path_2 = paths['select_path_2']

    # 检查原始文件是否存在
    if not os.path.exists(begin_path):
        raise FileNotFoundError(f"找不到文件: {begin_path}")

    # 初始化审校器，并根据配置决定是否启用医学RAG和R²框架
    reviewer = AIReviewer(use_medical_rag=enable_medical_rag, llm_client=llm_client)

    try:
        print(f"{GREEN}{BOLD}[处理进度]{RESET} 文件处理开始...")
        if file_type == 'docx':  # 如果文件类型是docx
            if has_review_table == 'Y':  # 如果配置有审查表
                remove_first_table(begin_path)  # 移除第一个表格
            elif has_review_table == 'N':  # 如果配置没有审查表
                pass  # 不做任何处理
            else:
                print(f"has_review_table配置错误: {has_review_table}")  # 配置错误提示
            extract_tables_from_word(begin_path, path_extract)  # 从Word中提取表格
            replace_tables(begin_path, no_table)  # 替换表格
            # 转换DOCX文件为MD文件
            convert_file_md(no_table, md_path)  # 转换文件为md格式

        elif file_type == 'md':  # 如果文件类型是md
            pass  # 不做任何处理
        else:
            print(f"文件类型错误: {file_type}")  # 文件类型错误提示

        # 读取md文件内容
        with open(md_path, 'r', encoding='utf-8') as file:
            text = file.read()  # 读取文件内容
            # 使用正则表达式去除特定字符
            modified_text = re.sub(r'\*\*|\*|\^|\$', '', text)
            modified_text = re.sub(r'\\<', '<', modified_text)
            modified_text = re.sub(r'\\>', '>', modified_text)
            modified_text = re.sub(r'\\\[(\d+)\\\]', r'[\1]', modified_text)
            modified_text = re.sub(r'\\\[\]', '[]', modified_text)
        # 写入修改后的内容到md文件
        with open(md_path, 'w', encoding='utf-8') as file:
            file.write(modified_text)

        # 使用语义分割器替代原有的分割方法
        input_list = divide_text_semantically(modified_text)

        # 打开AI结果文件写入模式
        with open(ai_path, 'w', encoding='utf-8') as f:
            total_paragraphs = len(input_list)  # 获取总段落数
            paragraph_num = 0  # 初始化段落编号
            
            for question in input_list:  # 遍历分割后的文本
                paragraph_num += 1  # 段落编号递增
                
                # 跳过图片和作者信息的AI审校，但保留原文输出
                if question.startswith('![') or ('[first_line_indent]' in question and ('[1]' in question or '作者' in question or '医师' in question)):
                    print(f"\n{YELLOW}{BOLD}[段落 {paragraph_num}/{total_paragraphs}]{RESET}")
                    print(f"{YELLOW}{'─'*50}{RESET}")  # 添加分隔线
                    print(f"{YELLOW}原文:{RESET}\n{question}\n")
                    print(f"{GREEN}审校结果:{RESET}\n[跳过审校]\n")
                    
                    # 写入原文和空的审校结果
                    f.write(f"\n**原文{paragraph_num}**:\n\n{question}\n\n")
                    f.write(f"**GPT审校{paragraph_num}**:\n\n[first_line_indent]此内容无需审校。\n\n")
                    f.write(f"**差异对比如下**:\n\n无需修改。\n\n")
                    
                    # 更新进度
                    if progress_callback:
                        progress_callback(paragraph_num / total_paragraphs)
                    continue
                    
                try:
                    print(f"\n{YELLOW}{BOLD}[段落 {paragraph_num}/{total_paragraphs}]{RESET}")
                    print(f"{YELLOW}{'─'*50}{RESET}")  # 添加分隔线
                    print(f"{YELLOW}原文:{RESET}\n{question}\n")
                    
                    # 根据是否有 llm_client 决定使用哪种处理方式
                    if llm_client:
                        # 使用 R² 框架处理
                        result = reviewer.process_with_r2(question)
                    else:
                        # 使用传统方式处理
                        result = reviewer.review_text(question)
                    
                    # 将结果格式化为易读形式
                    formatted_output = reviewer.format_review_result(result, question)
                    # 在命令行输出时移除[first_line_indent]标记
                    print(f"{GREEN}审校结果:{RESET}\n{formatted_output.replace('[first_line_indent]', '')}\n")
                    
                except Exception as ai_error:
                    print(f"处理问题时出现错误: {ai_error}")  # 输出错误信息
                    formatted_output = "[first_line_indent]GPT处理时出错"  # 错误时的默认输出

                # 写入原文和AI审校结果（保留[first_line_indent]标记以便后续处理）
                f.write(f"\n**原文{paragraph_num}**:\n\n{question}\n\n")
                f.write(f"**GPT审校{paragraph_num}**:\n\n{formatted_output}\n\n")
                
                # 提取修改建议并写入差异对比
                f.write(f"**差异对比如下**:\n\n")
                
                # 检查是否有结构化的修改建议
                if "corrections" in result and isinstance(result["corrections"], list) and result["corrections"]:
                    for num, correction in enumerate(result["corrections"], 1):
                        f.write(f'原文段{num}: {correction["original"]}\n\n修订段{num}: {correction["suggestion"]}\n\n')
                        if "category" in correction:
                            f.write(f'修改类型: {correction["category"]}\n\n')
                else:
                    f.write("没有发现需要修改的内容。\n\n")
                
                # 更新进度
                if progress_callback:
                    progress_callback(paragraph_num / total_paragraphs)

        print(f"\n{GREEN}{BOLD}[完成]{RESET} {file_name} 已完成AI校对")
        print(f"{GREEN}{'='*50}{RESET}\n")  # 添加结束分隔线
    except Exception as e:
        print(f"\n{YELLOW}{BOLD}[错误]{RESET} 处理 {file_name} 时出现错误：{e}")

    return 0  # 返回0表示成功

# 主程序入口
if __name__ == "__main__":
    # 使用path_manager获取正确的原始文件目录
    # 遍历文件夹，获取文件名和文件类型列表
    file_name_list, file_type_list = traverse_folder(path_manager.original_files_dir)
    print(f"\n{BLUE}{BOLD}待处理文件列表:{RESET}")
    for name in file_name_list:
        print(f"{BLUE}• {name}{RESET}")
    print(f"{BLUE}{'='*50}{RESET}\n")
    
    # 初始化 OpenAI 客户端（如果环境变量中有API密钥）
    llm_client = None
    try:
        # 首先检查环境变量
        api_key = os.environ.get("OPENAI_API_KEY")
        
        # 如果环境变量中没有，则从配置文件读取
        if not api_key:
            config_path = "hide_file/config_files/config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    api_key = config.get("openai_api_key")
        
        # 如果获取到了 API 密钥
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key  # 设置环境变量
            from openai import OpenAI
            llm_client = OpenAI()
            print(f"{GREEN}{BOLD}[初始化]{RESET} 成功初始化 OpenAI 客户端，将使用 R² 框架进行处理")
        else:
            print(f"{YELLOW}{BOLD}[提示]{RESET} 未找到 OpenAI API 密钥，将使用传统方式进行处理")
            
    except Exception as e:
        print(f"{YELLOW}{BOLD}[警告]{RESET} 初始化 OpenAI 客户端失败: {e}")
        print(f"{YELLOW}将使用传统方式进行处理{RESET}")
    
    for file_name, file_type in zip(file_name_list, file_type_list):  # 遍历文件名和文件类型
        try:
            process_file(file_name, file_type, llm_client=llm_client)  # 处理每个文件
        except Exception as e:
            print(f"\n{YELLOW}{BOLD}[错误]{RESET} 处理文件 {file_name} 失败: {e}")
            continue

    time_now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    
    # 检查是否为直接运行（不是被其他模块导入）
    if sys.argv[0].endswith('ai_review.py'):
        # 直接运行时使用命令行输出
        print(f"\n{GREEN}{BOLD}[程序完成]{RESET}")
        print(f"{GREEN}完成时间: {time_now}{RESET}")
        print(f"{GREEN}{'='*50}{RESET}\n")
    else:
        # 被其他模块调用时使用弹窗
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("完成", f"AI程序执行完毕, 当前时间: {time_now}")
    
    sys.exit(0)
