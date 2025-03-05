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
from tkinter import font as tkfont

from src.utils.docx_utils import convert_md_to_docx
from src.utils.table_utils import replace_placeholders_with_tables
from src.utils.file_utils import generate_path



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

                # 添加按键绑定函数
                def handle_keypress(event):
                    if event.char in ['1', '2', '3']:
                        choice_var.set(event.char)
                        if event.char != '3':
                            dialog.quit()
                        else:
                            self_define_entry.config(state='normal')
                            self_define_entry.focus()
                    elif event.keysym == 'Return':  # 添加回车键绑定
                        on_confirm()

                # 绑定按键事件
                dialog.bind('<Key>', handle_keypress)
                
                # 显示原文和修订内容
                frame = tk.Frame(dialog)
                frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # 左侧文本框
                left_frame = tk.Frame(frame)
                left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                text_display = tk.Text(left_frame, height=20, width=80)
                text_display.pack(pady=10)
                
                # 右侧按钮
                right_frame = tk.Frame(frame)
                right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
                
                choice_var = tk.StringVar()
                self_define_text = tk.StringVar()
                dialog_done = tk.BooleanVar(value=False)
                
                def on_choice():
                    if choice_var.get() == '3':
                        self_define_entry.config(state='normal')
                    else:
                        self_define_entry.config(state='disabled')
                        dialog.quit()
                
                # 确认按钮函数
                def on_confirm():
                    if choice_var.get() == '3' and not self_define_text.get():
                        messagebox.showerror("错误", "请输入自定义文本")
                        return
                    dialog.quit()
                
                # 创建选项框架
                options_frame = tk.Frame(dialog)
                options_frame.pack(fill=tk.X, padx=10)
                
                # 使用grid布局来纵向排列选项
                tk.Radiobutton(options_frame, text="保留原文", variable=choice_var, value='1', command=on_choice).grid(row=0, column=0, sticky='w')
                tk.Radiobutton(options_frame, text="采纳修订", variable=choice_var, value='2', command=on_choice).grid(row=1, column=0, sticky='w')
                
                # 创建一个框架来容纳自定义选项、输入框和确认按钮
                custom_frame = tk.Frame(options_frame)
                custom_frame.grid(row=2, column=0, sticky='w')
                
                # 自定义选项按钮
                tk.Radiobutton(custom_frame, text="自定义", variable=choice_var, value='3', command=on_choice).pack(side=tk.LEFT)
                
                # 自定义输入框
                self_define_entry = tk.Entry(custom_frame, textvariable=self_define_text, width=40, state='disabled')
                self_define_entry.pack(side=tk.LEFT, padx=(10, 0))
                
                # 确认按钮
                tk.Button(custom_frame, text="确认", command=on_confirm).pack(side=tk.LEFT, padx=(10, 0))
                
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

    # 导入主题管理器
    try:
        from src.utils.theme_manager import theme_manager
    except ImportError:
        # 如果无法导入，创建一个简化版的主题管理器
        class SimpleThemeManager:
            def __init__(self):
                self.theme = {
                    'colors': {
                        'primary': '#2196F3',      # 主色调 - 蓝色
                        'secondary': '#FFC107',    # 次要色调 - 琥珀色
                        'background': '#F5F5F5',   # 背景色 - 浅灰
                        'text': '#333333',         # 文本色 - 深灰
                        'button': '#1976D2',       # 按钮色 - 深蓝
                        'button_hover': '#1565C0', # 按钮悬停色
                        'border': '#E0E0E0',       # 边框色 - 灰色
                    },
                    'fonts': {
                        'default': ('Microsoft YaHei UI', 10),
                        'title': ('Microsoft YaHei UI', 24, 'bold'),
                        'subtitle': ('Microsoft YaHei UI', 18, 'bold'),
                        'small': ('Microsoft YaHei UI', 9),
                        'button': ('Microsoft YaHei UI', 10),
                        'input': ('Microsoft YaHei UI', 10)
                    },
                    'padding': {
                        'button': (20, 10),
                        'frame': 20,
                        'input': 5
                    }
                }
            
            def get_color(self, color_name):
                return self.theme['colors'].get(color_name, self.theme['colors']['primary'])
            
            def get_font(self, font_name):
                return self.theme['fonts'].get(font_name, self.theme['fonts']['default'])
            
            def get_padding(self, padding_name):
                return self.theme['padding'].get(padding_name, self.theme['padding']['frame'])
            
            def apply_theme(self, root):
                # 设置窗口背景色
                root.configure(bg=self.get_color('background'))
                
                # 配置全局样式
                style = ttk.Style()
                
                # 配置按钮样式
                style.configure('Custom.TButton',
                               font=self.get_font('button'),
                               padding=self.get_padding('button'))
                
                # 配置单选按钮样式
                style.configure('Custom.TRadiobutton',
                               font=self.get_font('default'),
                               background=self.get_color('background'))
        
        theme_manager = SimpleThemeManager()

    def create_custom_style():
        # 应用主题
        theme_manager.apply_theme(root)
        
    # 创建自定义样式
    create_custom_style()
    
    for file_path in find_reviewed_md_files_recursive(r'.\hide_file\中间文件'):
        file_name = os.path.basename(file_path)
        file_name_original = file_name.replace("_审校后_.md", "")
        begin_path, no_table, path_extract, md_path, ai_path, word_path_1, word_path_2, final_path_1, final_path_2, select_path_1, select_path_2 = generate_path(file_name_original)

        if not messagebox.askyesno("开始审校", f"是否开始审校文档: {file_name}?"):
            continue

        # 创建一个可重用的对话框
        dialog = tk.Toplevel()
        dialog.title("文本审校系统")
        dialog.geometry("1000x700")
        dialog.configure(bg=theme_manager.get_color('background'))

        # 应用自定义样式
        create_custom_style()
        
        # 创建主框架
        main_frame = tk.Frame(dialog, bg=theme_manager.get_color('background'))
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建标题
        title_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(title_frame, 
                             text="文本审校系统",
                             font=theme_manager.get_font('title'),
                             bg=theme_manager.get_color('background'),
                             fg=theme_manager.get_color('primary'))
        title_label.pack()

        # 左侧文本显示区域
        left_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 创建带有自定义样式的文本显示区域
        text_display = tk.Text(left_frame,
                             height=20,
                             width=80,
                             font=theme_manager.get_font('default'),
                             wrap=tk.WORD,
                             bg='white',
                             fg=theme_manager.get_color('text'),
                             padx=10,
                             pady=10,
                             relief=tk.FLAT)
        text_display.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=text_display.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_display.configure(yscrollcommand=scrollbar.set)

        # 右侧控制面板
        right_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))

        # 选项变量
        choice_var = tk.StringVar()
        self_define_text = tk.StringVar()
        dialog_done = tk.BooleanVar(value=False)

        def on_choice():
            if choice_var.get() == '3':
                self_define_entry.config(state='normal')
                self_define_entry.focus()
            else:
                self_define_entry.config(state='disabled')
                dialog_done.set(True)

        def on_confirm():
            if choice_var.get() == '3' and not self_define_text.get():
                messagebox.showerror("错误", "请输入自定义文本")
                return
            dialog_done.set(True)

        # 选项框架
        options_frame = tk.Frame(right_frame, bg=theme_manager.get_color('background'))
        options_frame.pack(fill=tk.X, pady=20)

        # 使用自定义样式的单选按钮
        ttk.Radiobutton(options_frame,
                       text="保留原文 (1)",
                       variable=choice_var,
                       value='1',
                       command=on_choice,
                       style='Custom.TRadiobutton').pack(pady=10, anchor='w')

        ttk.Radiobutton(options_frame,
                       text="采纳修订 (2)",
                       variable=choice_var,
                       value='2',
                       command=on_choice,
                       style='Custom.TRadiobutton').pack(pady=10, anchor='w')

        # 自定义输入区域
        custom_frame = tk.Frame(options_frame, bg=theme_manager.get_color('background'))
        custom_frame.pack(fill=tk.X, pady=10)

        ttk.Radiobutton(custom_frame,
                       text="自定义 (3)",
                       variable=choice_var,
                       value='3',
                       command=on_choice,
                       style='Custom.TRadiobutton').pack(anchor='w')

        self_define_entry = tk.Entry(custom_frame,
                                   textvariable=self_define_text,
                                   width=30,
                                   font=theme_manager.get_font('input'),
                                   state='disabled',
                                   relief=tk.FLAT,
                                   bg='white')
        self_define_entry.pack(pady=(10, 0), fill=tk.X)

        # 确认按钮
        confirm_button = ttk.Button(options_frame,
                                  text="确认修改",
                                  command=on_confirm,
                                  style='Custom.TButton')
        confirm_button.pack(pady=20)

        # 添加按键绑定
        def handle_keypress(event):
            if event.char in ['1', '2', '3']:
                choice_var.set(event.char)
                if event.char != '3':
                    dialog_done.set(True)
                else:
                    self_define_entry.config(state='normal')
                    self_define_entry.focus()
            elif event.keysym == 'Return':
                on_confirm()

        dialog.bind('<Key>', handle_keypress)

        def wait_for_dialog():
            dialog_done.set(False)
            while not dialog_done.get():
                dialog.update()
                time.sleep(0.1)

        adopt_count = 0
        doc_text = read_file(file_path)
        sections = split_document(doc_text)
        updated_texts_1 = []
        updated_texts_2 = []

        for section in sections:
            match_groups = get_match_groups(section)
            if not match_groups:
                messagebox.showinfo("提示", "上一段无差异，已经跳过")
                continue
                
            original_title, original_text, gpt_text, diff_text = match_groups
            diff_list = get_diff_list(diff_text)
            if diff_list == []:
                updated_texts_1.append(original_text + '\n')
                updated_texts_2.append(original_text + '\n')
                continue

            text_change_1 = original_text
            text_change_2 = original_text

            for diff in diff_list:
                original_part = list(diff[0].values())[0]
                revised_part = list(diff[1].values())[0]
                
                text_mark = wrap_text_segment(original_text, original_part)
                
                # 更新对话框内容
                text_display.config(state='normal')
                text_display.delete('1.0', tk.END)
                text_display.insert(tk.END, f'本段原文:\n{text_mark}\n\n')
                text_display.insert(tk.END, f'----------------------------\n')
                text_display.insert(tk.END, f'原文段:\n{original_part}\n\n')
                text_display.insert(tk.END, f'修订段:\n{revised_part}\n\n')
                text_display.config(state='disabled')
                
                # 重置选项和输入框
                choice_var.set('')
                self_define_text.set('')
                self_define_entry.config(state='disabled')
                
                dialog.deiconify()  # 显示对话框
                dialog.focus_force()
                dialog.grab_set()
                
                wait_for_dialog()
                
                choice = choice_var.get()
                
                if choice == '2': 
                    text_change_1 = update_text_change(original_part, revised_part, text_change_1)
                    text_change_2 = update_text_change_both(original_part, revised_part, text_change_2)
                    adopt_count += 1
                elif choice == '1':
                    pass
                elif choice == '3':
                    self_define = self_define_text.get()
                    text_change_1 = update_text_change(original_part, self_define, text_change_1)
                    text_change_2 = update_text_change_self_define(original_part, self_define, text_change_2)
            
            updated_texts_1.append(text_change_1 + '\n')
            updated_texts_2.append(text_change_2 + '\n')

        dialog.destroy()

        write_to_new_file(select_path_1, updated_texts_1)
        write_to_new_file(select_path_2, updated_texts_2)

        convert_md_to_docx(select_path_1, word_path_1)
        convert_md_to_docx(select_path_2, word_path_2)

        replace_placeholders_with_tables(word_path_1, path_extract, final_path_1)
        replace_placeholders_with_tables(word_path_2, path_extract, final_path_2)
        
        add_tab_indent_to_paragraphs(final_path_1, final_path_1)
        add_tab_indent_to_paragraphs(final_path_2, final_path_2)

        # 合并所有信息到一个消息框
        summary_message = f"处理完成！\n\n" \
                         f"• 文档人工审校已结束\n" \
                         f"• {file_name} 已转换为Word文档\n" \
                         f"• 采用修订数量: {adopt_count}"
        messagebox.showinfo("处理结果汇总", summary_message)

    root.destroy()







if __name__ == '__main__':
    revision_use()