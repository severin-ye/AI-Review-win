

import os
import time
import re
import sys


from w0_file_path import traverse_folder, generate_path, remove_middle_folder
from w1_table_about import extract_tables_from_word, replace_tables, replace_placeholders_with_tables, remove_first_table
from w2_docx_to_md import convert_file_md, convert_md_to_docx
from w3_smart_divide import divide_text
from w4_ai_answer import ai_answer
from w5_same_find import find_diff_sentences
from docx import Document
from lxml import etree
from time_lock import check_date

from config import max_length, has_review_table




check_date()






'''
1. 生成单文件处理时的路径
2. 识别文件类型(1: docx, 2: markdown)
3. 移除第一个表格
4. 提取表格-->生成表格文件
5. 移除表格-->生成无表格文件
6. docx转md-->用无表格文件生成md文件
7. 使用正则表达式移除可能影响乱码的字符
8. 分割文本
9. 每段文本使用GPT审校
10. 将每段结果写入文件
11. md转docx-->用审校后md文件生成word文件
12. 替换表格-->合并表格文件和审校后文件
13. 高亮差异
14. 删除中间文件夹
'''
# 操作文件
def process_file(file_name, file_type):

    
    print(f"File Name: {file_name}, File Type: {file_type}")
    # 生成单文件处理时的路径
    begin_path, no_table, path_extract, md_path, ai_path, word_path_1, word_path_2, final_path_1, final_path_2, select_path_1, select_path_2 = generate_path(file_name)

    try:
        print(f"{file_name} 处理开始...")
        # 识别文件类型(1: docx, 2: markdown)
        if file_type == 'docx':
            if has_review_table == 'Y':
                # 移除第一个表格
                remove_first_table(begin_path)
            elif has_review_table == 'N':
                pass
            else:
                print(f"has_review_table配置错误: {has_review_table}")
            # 提取表格
            extract_tables_from_word(begin_path, path_extract)
            # 移除表格
            replace_tables(begin_path, no_table)
            # docx转md
            convert_file_md(no_table, md_path)
        elif file_type == 'md':
            pass
        else:
            print(f"文件类型错误: {file_type}")

        
        # 使用正则表达式移除‘**’和‘^’
        with open(md_path, 'r', encoding='utf-8') as file:
            text = file.read()
            modified_text = re.sub(r'\*\*', '', text)
            modified_text = re.sub(r'\*', '', modified_text)
            modified_text = re.sub(r'\^', '', modified_text)
            modified_text = re.sub(r'\$', '', modified_text)
            # 替换\<和\>为<和>
            modified_text = re.sub(r'\\<', r'<', modified_text)
            modified_text = re.sub(r'\\>', r'>', modified_text)
    
            # 替换\[数字\]为[数字]
            modified_text = re.sub(r'\\\[(\d+)\\\]', r'[\1]', modified_text)
            # 替换\[\]为[]
            modified_text = re.sub(r'\\\[\]', r'[]', modified_text)

            
            file.close()
        with open(md_path, 'w', encoding='utf-8') as file:
            file.write(modified_text)
            file.close()
        
        # 分割文本
        input_list=divide_text(md_path, max_length)   # 自定义max_length
        
        
        with open(ai_path, 'w', encoding='utf-8') as f:
            paragraph_num = 0
            # 每段文本使用GPT审校
            for question in  input_list:             # 每段处理开始

                output=ai_answer(question)   # GPT审校输出

                # shell输出(提示用户程序正在运行)
                print(question)
                print(output)
                print('------------------')
                
                
                # 将原文和AI返回结果写入文件(真正的输出)

                # 原文
                paragraph_num += 1
                f.write('\n')
                f.write(f"**原文{paragraph_num}**:")
                f.write('\n')

                f.write('\n')
                f.write(question)  # 原文
                f.write('\n')
                # f.write('』')
                # f.write('\n')

                 # GPT审校输出
                f.write('\n')
                f.write(f'**GPT审校{paragraph_num}**:')
                f.write('\n')
               
                f.write('\n')
                f.write(output)
                f.write('\n')


                # 差异对比
                differences = find_diff_sentences(question, output)  # 生成每一段的差异对比

                f.write('\n')
                f.write(f'**差异对比如下**:')
                f.write('\n')

                f.write('\n')
                num=0
                for diff in differences:
                    num += 1
                    f.write(f'原文段{num}: {diff[0]}')
                    f.write('\n')
                    f.write('\n')
                    f.write(f'修订段{num}: {diff[1]}')
                    f.write('\n')
                    f.write('\n')
                f.write('\n')

            
        f.close()

                
       # 老版本
        # # md转docx
        # convert_md_to_docx(ai_path, word_path)
        # # 替换表格
        # replace_placeholders_with_tables(word_path, path_extract, final_path)
        # print(f"{file_name} 已经转换为word文档")

        # # 删除中间文件夹
        # remove_middle_folder(file_name)
        # print(f"{file_name} 中间文件已删除")

        print(f"{file_name} 已完成AI校对")
    except Exception as e:
        print(f"处理 {file_name} 时出现错误：{e}")

    return 0






# 使用
file_name_list=traverse_folder(os.path.join(os.getcwd(), "_1_原文件"))[0]
file_type_list=traverse_folder(os.path.join(os.getcwd(), "_1_原文件"))[1]
print(file_name_list)

for file_name, file_type in zip(file_name_list, file_type_list):
    process_file(file_name, file_type)



# 执行完毕, 打印当前时间
time_now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
end = input(f"AI程序执行完毕, 当前时间: {time_now}, 输入'e'退出程序: ")
while True:
    if end == 'e':
        quit()
    else:
        pass

