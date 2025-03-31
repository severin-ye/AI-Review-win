# 导入必要的模块
import os  # 操作系统相关功能模块
import time  # 时间相关功能模块
import re  # 正则表达式模块，用于字符串匹配和替换
import sys  # 系统特定参数和功能模块
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
from src.utils.ai_utils import ai_answer
from src.utils.similarity_utils import find_diff_sentences
from src.utils.rag_utils import initialize_rag, get_medical_verification  # 导入RAG系统

class AIReviewer:
    """AI审校类，用于处理文本审校功能"""
    
    def __init__(self, use_medical_rag=False):
        """初始化AI审校器
        
        Args:
            use_medical_rag: 是否使用医学RAG系统
        """
        self.use_medical_rag = use_medical_rag
        # 如果启用医学RAG，初始化RAG系统
        if self.use_medical_rag:
            initialize_rag()
    
    def review_text(self, text):
        """审校单个文本
        
        Args:
            text (str): 待审校的文本
            
        Returns:
            str: 审校结果
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
            return result
        except Exception as e:
            print(f"处理文本时出错: {e}")
            return None
    
    def batch_review(self, texts):
        """批量审校文本
        
        Args:
            texts (list): 待审校的文本列表
            
        Returns:
            list: 审校结果列表
        """
        results = []
        for text in texts:
            try:
                result = self.review_text(text)
                if result is None:
                    raise Exception("AI审校返回空结果")
                results.append(result)
            except Exception as e:
                print(f"处理文本时出错: {e}")
                results.append(None)
        return results

# 定义处理文件的函数
def process_file(file_name, file_type, progress_callback=None):
    print(f"File Name: {file_name}, File Type: {file_type}")  # 输出文件名和文件类型
    
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

    # 初始化审校器，并根据配置决定是否启用医学RAG
    reviewer = AIReviewer(use_medical_rag=enable_medical_rag)

    try:
        print(f"{file_name} 处理开始...")  # 输出处理开始信息
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

        # 分割文本
        input_list = divide_text_with_indent(md_path)

        # 打开AI结果文件写入模式
        with open(ai_path, 'w', encoding='utf-8') as f:
            paragraph_num = 0  # 初始化段落编号
            total_paragraphs = len(input_list)  # 获取总段落数
            
            for question in input_list:  # 遍历分割后的文本
                try:
                    output = reviewer.review_text(question)  # 使用审校器处理文本
                except Exception as ai_error:
                    print(f"处理问题时出现错误: {ai_error}")  # 输出错误信息
                    output = "GPT处理时出错"  # 错误时的默认输出

                print(question)  # 打印问题
                print(output)  # 打印AI输出
                print('------------------')  # 分隔线

                paragraph_num += 1  # 段落编号递增
                # 写入原文和AI审校结果
                f.write(f"\n**原文{paragraph_num}**:\n\n{question}\n\n")
                f.write(f"**GPT审校{paragraph_num}**:\n\n{output}\n\n")
                
                differences = find_diff_sentences(question, output)  # 查找不同句子
                f.write(f"**差异对比如下**:\n\n")  # 写入差异对比
                for num, diff in enumerate(differences, 1):
                    f.write(f'原文段{num}: {diff[0]}\n\n修订段{num}: {diff[1]}\n\n')
                
                # 更新进度
                if progress_callback:
                    progress_callback(paragraph_num / total_paragraphs)

        print(f"{file_name} 已完成AI校对")  # 完成处理提示
    except Exception as e:
        print(f"处理 {file_name} 时出现错误：{e}")  # 输出错误信息

    return 0  # 返回0表示成功

# 主程序入口
if __name__ == "__main__":
    # 使用path_manager获取正确的原始文件目录
    # 遍历文件夹，获取文件名和文件类型列表
    file_name_list, file_type_list = traverse_folder(path_manager.original_files_dir)
    print(file_name_list)  # 打印文件名列表
    
    for file_name, file_type in zip(file_name_list, file_type_list):  # 遍历文件名和文件类型
        try:
            process_file(file_name, file_type)  # 处理每个文件
        except Exception as e:
            print(f"处理文件 {file_name} 失败: {e}")
            continue

    time_now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))  # 获取当前时间
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("完成", f"AI程序执行完毕, 当前时间: {time_now}")
    sys.exit(0)
