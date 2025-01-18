# 导入必要的模块
import os  # 操作系统相关功能模块
import time  # 时间相关功能模块
import re  # 正则表达式模块，用于字符串匹配和替换
import sys  # 系统特定参数和功能模块
from docx import Document  # 处理Word文档的模块
from lxml import etree  # 用于处理XML和HTML的模块
from time_lock import check_date  # 自定义模块，用于检查日期
from config import has_review_table  # 配置模块，导入是否有审查表的配置项

from w0_file_path import traverse_folder, generate_path, remove_middle_folder  # 自定义模块，文件路径相关功能
from w1_table_about import extract_tables_from_word, replace_tables, replace_placeholders_with_tables, remove_first_table  # 自定义模块，处理Word文档中的表格
from w2_docx_to_md import convert_file_md # 自定义模块，处理Word文档和Markdown文档
from w3_smart_divide import divide_text_with_indent  # 自定义模块，分割文本
from w4_ai_answer import ai_answer  # 自定义模块，AI回答功能
from w5_same_find import find_diff_sentences  # 自定义模块，查找不同句子

# 定义处理文件的函数
def process_file(file_name, file_type):
    print(f"File Name: {file_name}, File Type: {file_type}")  # 输出文件名和文件类型
    # 生成各路径变量
    begin_path, no_table, path_extract, md_path, ai_path, word_path_1, word_path_2, final_path_1, final_path_2, select_path_1, select_path_2 = generate_path(file_name)

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
            for question in input_list:  # 遍历分割后的文本
                try:
                    output = ai_answer(question)  # 获取AI回答
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

        print(f"{file_name} 已完成AI校对")  # 完成处理提示
    except Exception as e:
        print(f"处理 {file_name} 时出现错误：{e}")  # 输出错误信息

    return 0  # 返回0表示成功

# 主程序入口
if __name__ == "__main__":
    # 遍历文件夹，获取文件名和文件类型列表
    file_name_list, file_type_list = traverse_folder(os.path.join(os.getcwd(), "_1_原文件"))
    print(file_name_list)  # 打印文件名列表

    for file_name, file_type in zip(file_name_list, file_type_list):  # 遍历文件名和文件类型
        process_file(file_name, file_type)  # 处理每个文件

    time_now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))  # 获取当前时间
    end = input(f"AI程序执行完毕, 当前时间: {time_now}, 输入'e'退出程序: ")  # 提示程序执行完毕并输入'e'退出
    while True:  # 循环等待用户输入
        if end == 'e' or end == 'E':  # 如果输入'e'或'E'
            # 退出程序
            print("程序退出")
            sys.exit(0)
        else:
            pass  # 继续等待输入
