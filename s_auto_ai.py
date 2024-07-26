import os
import time
import re
import sys
from docx import Document
from lxml import etree
from time_lock import check_date
from config import max_length, has_review_table

from w0_file_path import traverse_folder, generate_path, remove_middle_folder
from w1_table_about import extract_tables_from_word, replace_tables, replace_placeholders_with_tables, remove_first_table
from w2_docx_to_md import convert_file_md, convert_md_to_docx
from w3_smart_divide import divide_text
from w4_ai_answer import ai_answer
from w5_same_find import find_diff_sentences
from w6_2_key_verifier import main as key_verifier_main



# 操作文件
def process_file(file_name, file_type):
    print(f"File Name: {file_name}, File Type: {file_type}")
    begin_path, no_table, path_extract, md_path, ai_path, word_path_1, word_path_2, final_path_1, final_path_2, select_path_1, select_path_2 = generate_path(file_name)

    try:
        print(f"{file_name} 处理开始...")
        if file_type == 'docx':
            if has_review_table == 'Y':
                remove_first_table(begin_path)
            elif has_review_table == 'N':
                pass
            else:
                print(f"has_review_table配置错误: {has_review_table}")
            extract_tables_from_word(begin_path, path_extract)
            replace_tables(begin_path, no_table)
            convert_file_md(no_table, md_path)
        elif file_type == 'md':
            pass
        else:
            print(f"文件类型错误: {file_type}")

        with open(md_path, 'r', encoding='utf-8') as file:
            text = file.read()
            modified_text = re.sub(r'\*\*|\*|\^|\$', '', text)
            modified_text = re.sub(r'\\<', '<', modified_text)
            modified_text = re.sub(r'\\>', '>', modified_text)
            modified_text = re.sub(r'\\\[(\d+)\\\]', r'[\1]', modified_text)
            modified_text = re.sub(r'\\\[\]', '[]', modified_text)
        with open(md_path, 'w', encoding='utf-8') as file:
            file.write(modified_text)

        input_list = divide_text(md_path, max_length)

        with open(ai_path, 'w', encoding='utf-8') as f:
            paragraph_num = 0
            for question in input_list:
                try:
                    output = ai_answer(question)
                except Exception as ai_error:
                    print(f"处理问题时出现错误: {ai_error}")
                    output = "GPT处理时出错"

                print(question)
                print(output)
                print('------------------')

                paragraph_num += 1
                f.write(f"\n**原文{paragraph_num}**:\n\n{question}\n\n")
                f.write(f"**GPT审校{paragraph_num}**:\n\n{output}\n\n")

                differences = find_diff_sentences(question, output)
                f.write(f"**差异对比如下**:\n\n")
                for num, diff in enumerate(differences, 1):
                    f.write(f'原文段{num}: {diff[0]}\n\n修订段{num}: {diff[1]}\n\n')

        print(f"{file_name} 已完成AI校对")
    except Exception as e:
        print(f"处理 {file_name} 时出现错误：{e}")

    return 0


if __name__ == "__main__":
    check_date()

    # 验证密钥
    key_verifier_main()
    # 使用
    file_name_list, file_type_list = traverse_folder(os.path.join(os.getcwd(), "_1_原文件"))
    print(file_name_list)

    for file_name, file_type in zip(file_name_list, file_type_list):
        process_file(file_name, file_type)

    time_now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    end = input(f"AI程序执行完毕, 当前时间: {time_now}, 输入'e'退出程序: ")
    while True:
        if end == 'e' or end == 'E':
            quit()
        else:
            pass
