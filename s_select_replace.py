import glob
import os
import sys
import re
import json
import time
import platform
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from time_lock import check_date

from w2_docx_to_md import convert_md_to_docx
from w1_table_about import replace_placeholders_with_tables
from w0_file_path import generate_path
from w6_2_key_verifier import main as key_verifier_main

check_date()

# 验证密钥
key_verifier_main()

# 找到文件夹中的所有审校后的md文件
def find_reviewed_md_files_recursive(folder_path):
    pattern = os.path.join(folder_path, "**/*_审校后_.md")
    return glob.glob(pattern, recursive=True)

# 阅读文件内容
def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    
# 添加缩进
def add_tab_indent_to_paragraphs(doc_path, new_doc_path):
    # 加载Word文档
    doc = Document(doc_path)
    
    # 遍历文档中的每个自然段
    for paragraph in doc.paragraphs:
        # 设置段落首行缩进为半英寸（一个Tab键的默认长度）
        paragraph.paragraph_format.first_line_indent = Inches(0.5)
    
    # 保存修改后的文档
    doc.save(new_doc_path)

# 从文档中提取审校内容, 并格式化为3组1段    
def split_document(doc_text):
    pattern = r"(\*\*原文\d+\*\*:\n.*?\*\*GPT审校\d+\*\*:\n.*?\*\*差异对比如下\*\*:\n.*?)(?=\*\*原文\d+\*\*|\Z)"
    return re.findall(pattern, doc_text, re.DOTALL)
# 从给定的1段文本段落中提取  原文, 修订后的文本, 差异对比
def get_match_groups(section):
    pattern = r"\*\*原文(\d+)\*\*:\n(.*?)\n\*\*GPT审校\1\*\*:\n(.*?)\n\*\*差异对比如下\*\*:\n(.*?)(?=\*\*原文\d+\*\*|\Z)"
    match = re.search(pattern, section, re.DOTALL)
    if match:
        return match.groups()
    else:
        return None

# 从给定的差异文本中提取原文和修订后的文本的差异，并将这些差异存储在一个列表中。
def get_diff_list(diff_text):
    diff_matches = re.findall(r"原文段(\d+): (.*?)修订段\1: (.*?)\n", diff_text, re.DOTALL)
    return [[{"原文段" + num: orig.strip()}, {"修订段" + num: rev.strip()}] for num, orig, rev in diff_matches]
# 这个函数将原文标题、原文、修订后的文本和差异列表组合成一个字典，并将这个字典存储在一个列表中。
def get_list_of_final(original_title, original_text, gpt_text, diff_list):
    return [{
        "原文" + original_title: original_text.strip(),
        "GPT审校" + original_title: gpt_text.strip(),
        "差异对比": diff_list
    }]
# 从给定的文本段落中提取所有的原文
def get_text_change(section):
    original_texts = re.findall(r"\*\*原文\d+\*\*:\n(.*?)(?=\n\*\*原文\d+\*\*|\n\*\*GPT审校\d+\*\*|\Z)", section, re.DOTALL)
    return '\n'.join(original_texts)

# 将原文中标记 AI认为需要修改的部分 (命令行交互)
def wrap_text_segment(a: str, b: str) -> str:
    # 定义排除的字符和模式
    excluded_characters = [' ', '\n', '*', '_', '#', '`', '~', '>', '+', '-', '=', '|', '{', '}', '.', '!', '(', ')', '[', ']', '<', '>', '&', '$', '%', '@', '?', '/', '\\', "'", '"', ':', ';', ',']
    excluded_patterns = [r'<表格不予审校_\d+>']
    temp_replacement_1 = '      {===['  # 命令行交互的标记
    temp_replacement_2 = ']===}      '
    
    # 检查b是否仅包含排除字符或匹配排除模式
    if b == "" or any(char in b for char in excluded_characters) or any(re.search(pattern, b) for pattern in excluded_patterns):
        # 直接将a赋值给c，不进行任何操作
        c = a
    else:
        # 在a文本中用{$和$}包裹其中b的部分，储存为c
        c = a.replace(b, temp_replacement_1 + b + temp_replacement_2)
    return c

# 将原文中的指定部分替换为修订后的文本
def update_text_change(original_part, revised_part, text_change): # 直接替换
    marked_revised_part = f'｛～{revised_part}～｝'
    return text_change.replace(original_part, marked_revised_part, 1)

def update_text_change_both(original_part, revised_part, text_change): # 保留原文和AI修订
    marked_revised_part = f'｛～原文:{original_part} AI:{revised_part}～｝'
    return text_change.replace(original_part, marked_revised_part, 1)

def update_text_change_self_define(original_part, revised_part, text_change): # 保留原文和用户自定义修订
    marked_revised_part = f'｛～原文:{original_part} 用户:{revised_part}～｝'
    return text_change.replace(original_part, marked_revised_part, 1)


def clear_screen():
    """清除命令行屏幕。"""
    os_name = platform.system()
    if os_name == 'Windows':
        os.system('cls')
    else:
        os.system('clear')
'''
调用上述所有的函数来处理文本修订。
它首先从给定的文本段落中提取原文、修订后的文本和差异对比，
接下来，它找出原文和修订文本之间的差异，并将这些差异存储在一个列表中。
然后，它将这些差异应用到原文上，生成修订后的文本。
如果在文本段落中找不到匹配的内容，它会返回一个错误消息。
'''
def apply_revisions(section):
    data = {}     # 创建一个字典来存储4个变量的值  original_text：原始文本  gpt_text：GPT生成的文本 original_part：原始部分  revised_part：修订部分
    adopt_count_add = 0 # 添加计数器为本段的修订数

    # 从给定的文本段落中提取原文, 修订后的文本, 差异对比
    match_groups = get_match_groups(section)
    
    if match_groups: # 如果找到3节1组
        original_title, original_text, gpt_text, diff_text = match_groups
        data['original_text'] = original_text
        data['gpt_text'] = gpt_text
   

        diff_list = get_diff_list(diff_text)
        if diff_list == []:
            return 1, original_text, original_text,adopt_count_add   # 如果找不到差异对比, 则返回原文
        
        list_of_final = get_list_of_final(original_title, original_text, gpt_text, diff_list)
        # text_change = get_text_change(section) # 从给定的文本段落中提取所有的原文
        # print(f'原文1: \n{text_change}\n')

        for item in list_of_final:
            original_key = "原文" + list(item.keys())[0].replace("原文", "") 
            original_text = item[original_key] # 本段原文
            # print(f'原文2: \n{original_text}\n')

            # 初始化, 以防全部选择保留原文
            text_change_1 = original_text
            text_change_2 = original_text

            for diff in item["差异对比"]:
                original_part = list(diff[0].values())[0]
                revised_part = list(diff[1].values())[0]
                data['original_part'] = original_part
                data['revised_part'] = revised_part

                text_mark = wrap_text_segment(original_text, original_part) # 将原文中标记 AI认为需要修改的部分(命令行交互)
                print(f'本段原文: \n{text_mark}\n')
                print("----------------------------")
                print(f'原文段: \n{original_part}\n')
                print(f'修订段: \n{revised_part}')

                while True:
                    print("--------------")
                    choice = input("\n请选择:(1: 保留原文 2: 采纳修订 3: 自定义) ")
                    if choice in ['1', '2', '3']:
                        break
                    print('无效输入，请重新输入。')

                if choice == '2': 
                    text_change_1 = update_text_change(original_part, revised_part, text_change_1)
                    text_change_2 = update_text_change_both(original_part, revised_part, text_change_2)
                    adopt_count_add += 1 # 本段采用修订数量的计数器+1


                elif choice == '1':
                    pass # 保留原文

                elif choice == '3':
                    while True:
                        self_define = input("请输入自定义文本: ")
                        if self_define != "":
                            break
                        print('无效输入，请重新输入。')
                    text_change_1 = update_text_change(original_part, self_define, text_change_1) # 将原文中的指定部分替换为修订后的文本
                    text_change_2 = update_text_change_self_define(original_part, self_define, text_change_2) # 将原文中的指定部分替换为修订后的文本


                
                    
                clear_screen()

        return 1, text_change_1, text_change_2, adopt_count_add  
    else:  # 如果找不到3节1组
        return 0, "", "", 0  # 这样即使没有找到匹配组，也返回了统一格式的数据




# 将文本写入新文件, revision_use()函数的子功能
def write_to_new_file(new_file_path, updated_texts):
    # 将更新后的文本写入新文件
    with open(new_file_path, 'w', encoding='utf-8') as file:
        for text in updated_texts:
            file.write(text + '\n')  # 添加一个换行符作为段落间的分隔


def revision_use():
    # 从文件列表中一一读取文件
    for file_path in find_reviewed_md_files_recursive(r'.\hide_file\中间文件'): # 开始处理单一文件

        # 文件名
        file_name = os.path.basename(file_path)
        file_name_original = file_name.replace("_审校后_.md", "")
        begin_path, no_table, path_extract, md_path, ai_path, word_path_1, word_path_2, final_path_1, final_path_2, select_path_1, select_path_2 = generate_path(file_name_original)


        # print(f"本文档审校开始: {file_name}\n\n")
        while True:
            do_it = input(f"本文档审校开始: {file_name}\n\n输入任意值开始:  ")
            break  # 不管输入什么值，都直接跳出循环
        clear_screen()

        # 添加采用修订数量的计数器
        adopt_count = 0 # 修订总数

        
        doc_text = read_file(file_path)
        # 从文档中提取审校内容, 并格式化为3组1段
        sections = split_document(doc_text)
        updated_texts_1 = []  # 存储更新后的所有段落
        updated_texts_2 = []  # 存储更新后的所有段落

        
        # 将3组1段, 进行人工选择, 并应用修订
        for section in sections:
            # print 原文, GPT审校
            
            # print("本段审校开始:")
            updated_text = apply_revisions(section)  # 应用每段修订(是个元组, 第一个元素是状态码, 第二个元素是更新后的文段, 第三个元素是更新后的文段, 第四个元素是采用修订数量)
            
            
            # 如果undated_text为空, 则说明没有匹配的内容
            if updated_text[0] == 0:
                print("上一段无差异, 已经跳过\n") # 保留原文的逻辑, 在上面写过了, (初始化, 以防全部选择保留原文)
            elif updated_text[0] == 1:
                updated_texts_1.append(updated_text[1] + '\n')  # 添加更新后的文段到列表
                updated_texts_2.append(updated_text[2] + '\n')
                adopt_count += updated_text[3]  # 采用修订数量的计数器,将每一段的修订数加到总数里面。
            # print("----------------------------") # 用于分割 上一段和下一段

        # 写入更新后的文本到新文件
        write_to_new_file(select_path_1, updated_texts_1)
        write_to_new_file(select_path_2, updated_texts_2)
        

        print("本文档审校结束")
        # md转docx
        convert_md_to_docx(select_path_1, word_path_1)
        convert_md_to_docx(select_path_2, word_path_2)

        # 替换表格
        replace_placeholders_with_tables(word_path_1, path_extract, final_path_1)
        replace_placeholders_with_tables(word_path_2, path_extract, final_path_2)
        print(f"{file_name} 已经转换为word文档")
        # 添加缩进
        add_tab_indent_to_paragraphs(final_path_1, final_path_1)
        add_tab_indent_to_paragraphs(final_path_2, final_path_2)


        # 打印采用修订数量
        print(f"采用修订数量: {adopt_count}\n\n")
        input("按任意键继续...")



    print("所有文档审校结束")
    time.sleep(5)







if __name__ == '__main__':
    revision_use()