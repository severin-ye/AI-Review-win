import glob
import os
import sys
import re
import json
import time
import platform
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT # 这个是设置段落对齐方式的
import tkinter as tk
from tkinter import messagebox, ttk

from w2_docx_to_md import convert_md_to_docx
from w1_table_about import replace_placeholders_with_tables
from w0_file_path import generate_path



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

        for item in list_of_final:
            original_key = "原文" + list(item.keys())[0].replace("原文", "") 
            original_text = item[original_key] # 本段原文

            # 初始化, 以防全部选择保留原文
            text_change_1 = original_text
            text_change_2 = original_text

            for diff in item["差异对比"]:
                original_part = list(diff[0].values())[0]
                revised_part = list(diff[1].values())[0]
                data['original_part'] = original_part
                data['revised_part'] = revised_part

                text_mark = wrap_text_segment(original_text, original_part)
                
                # 创建选择对话框
                dialog = tk.Toplevel()
                dialog.title("审校选择")
                dialog.geometry("800x600")
                
                # 显示原文和修订内容
                text_display = tk.Text(dialog, height=20, width=80)
                text_display.insert(tk.END, f'本段原文:\n{text_mark}\n\n')
                text_display.insert(tk.END, f'----------------------------\n')
                text_display.insert(tk.END, f'原文段:\n{original_part}\n\n')
                text_display.insert(tk.END, f'修订段:\n{revised_part}')
                text_display.pack(pady=10)
                text_display.config(state='disabled')
                
                choice_var = tk.StringVar()
                self_define_text = tk.StringVar()
                
                def on_choice():
                    if choice_var.get() == '3':
                        self_define_entry.config(state='normal')
                    else:
                        self_define_entry.config(state='disabled')
                        dialog.quit()
                
                # 选择按钮
                tk.Radiobutton(dialog, text="保留原文", variable=choice_var, value='1', command=on_choice).pack()
                tk.Radiobutton(dialog, text="采纳修订", variable=choice_var, value='2', command=on_choice).pack()
                tk.Radiobutton(dialog, text="自定义", variable=choice_var, value='3', command=on_choice).pack()
                
                # 自定义输入框
                self_define_entry = tk.Entry(dialog, textvariable=self_define_text, width=60, state='disabled')
                self_define_entry.pack(pady=10)
                
                # 确认按钮
                def on_confirm():
                    if choice_var.get() == '3' and not self_define_text.get():
                        messagebox.showerror("错误", "请输入自定义文本")
                        return
                    dialog.quit()
                
                tk.Button(dialog, text="确认", command=on_confirm).pack(pady=10)
                
                dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # 禁用关闭按钮
                dialog.transient(dialog.master)
                dialog.grab_set()
                dialog.mainloop()
                
                choice = choice_var.get()
                
                if choice == '2': 
                    text_change_1 = update_text_change(original_part, revised_part, text_change_1)
                    text_change_2 = update_text_change_both(original_part, revised_part, text_change_2)
                    adopt_count_add += 1
                elif choice == '1':
                    pass
                elif choice == '3':
                    self_define = self_define_text.get()
                    text_change_1 = update_text_change(original_part, self_define, text_change_1)
                    text_change_2 = update_text_change_self_define(original_part, self_define, text_change_2)
                
                dialog.destroy()

        return 1, text_change_1, text_change_2, adopt_count_add  
    else:  # 如果找不到3节1组
        return 0, "", "", 0




# 将文本写入新文件, revision_use()函数的子功能
def write_to_new_file(new_file_path, updated_texts):
    # 将更新后的文本写入新文件
    with open(new_file_path, 'w', encoding='utf-8') as file:
        for text in updated_texts:
            file.write(text + '\n')  # 添加一个换行符作为段落间的分隔


def revision_use():
    # 创建主窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    for file_path in find_reviewed_md_files_recursive(r'.\hide_file\中间文件'):
        file_name = os.path.basename(file_path)
        file_name_original = file_name.replace("_审校后_.md", "")
        begin_path, no_table, path_extract, md_path, ai_path, word_path_1, word_path_2, final_path_1, final_path_2, select_path_1, select_path_2 = generate_path(file_name_original)

        if not messagebox.askyesno("开始审校", f"是否开始审校文档: {file_name}?"):
            continue

        adopt_count = 0
        doc_text = read_file(file_path)
        sections = split_document(doc_text)
        updated_texts_1 = []
        updated_texts_2 = []

        for section in sections:
            updated_text = apply_revisions(section)
            
            if updated_text[0] == 0:
                messagebox.showinfo("提示", "上一段无差异，已经跳过")
            elif updated_text[0] == 1:
                updated_texts_1.append(updated_text[1] + '\n')
                updated_texts_2.append(updated_text[2] + '\n')
                adopt_count += updated_text[3]

        write_to_new_file(select_path_1, updated_texts_1)
        write_to_new_file(select_path_2, updated_texts_2)

        messagebox.showinfo("处理完成", "本文档审校结束")
        
        convert_md_to_docx(select_path_1, word_path_1)
        convert_md_to_docx(select_path_2, word_path_2)

        replace_placeholders_with_tables(word_path_1, path_extract, final_path_1)
        replace_placeholders_with_tables(word_path_2, path_extract, final_path_2)
        messagebox.showinfo("转换完成", f"{file_name} 已经转换为word文档")
        
        add_tab_indent_to_paragraphs(final_path_1, final_path_1)
        add_tab_indent_to_paragraphs(final_path_2, final_path_2)

        messagebox.showinfo("修订统计", f"采用修订数量: {adopt_count}")

    messagebox.showinfo("完成", "所有文档审校结束")
    root.destroy()







if __name__ == '__main__':
    revision_use()