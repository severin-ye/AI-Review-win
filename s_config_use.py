import tkinter as tk
from tkinter import messagebox, scrolledtext
import os
import importlib.util
import sys
import json

def load_config(json_path):
    """加载配置文件并更新GUI"""
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            config_data = json.load(file)

        # 加载 API 密钥
        api_keys = config_data.get('api_keys', {})
        config_vars['openai_api_key'].set(api_keys.get('openai', ''))
        config_vars['tyqw_api_key'].set(api_keys.get('tyqw', ''))

        # 加载其他配置
        config_vars['module_type'].set(config_data.get('module_type', ''))
        config_vars['max_length'].set(str(config_data.get('max_length', '')))
        config_vars['has_review_table'].set('Y' if config_data.get('has_review_table', False) else 'N')
        
        # 加载 prompt
        prompt_text.delete('1.0', tk.END)
        prompt_text.insert('1.0', config_data.get('prompt', ''))

    except Exception as e:
        messagebox.showerror("Error", f"Unable to load configuration: {e}")


def get_config_file_path():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    else:
        application_path = os.getcwd()  # 作为默认路径

    return os.path.join(application_path, "hide_file", "配置文件", "config.json")




def save_config(json_path):
    """保存更改回配置文件"""
    try:
        config_data = {
            "api_keys": {
                "openai": config_vars["openai_api_key"].get(),
                "tyqw": config_vars["tyqw_api_key"].get()
            },
            "module_type": config_vars["module_type"].get(),
            "prompt": prompt_text.get('1.0', tk.END).strip(),
            "max_length": int(config_vars["max_length"].get()),
            "has_review_table": config_vars["has_review_table"].get() == 'Y'
        }

        with open(json_path, 'w', encoding='utf-8') as file:
            json.dump(config_data, file, indent=4)

        messagebox.showinfo("Information", "Configuration Saved Successfully")
    except IOError as e:
        messagebox.showerror("Error", f"Unable to save file: {os.path.basename(json_path)}\n{e}")






# 界面布局和大小参数
label_width = 20            # 标签控件的宽度（例如"OpenAI API Key"标签的宽度）
entry_width = 30            # 文本输入框的宽度，用于API密钥等单行文本输入
prompt_text_height = 10     # 多行文本输入框（如用于"Prompt"）的高度
prompt_text_width = 50      # 多行文本输入框的宽度
button_pad_y = 30           # 保存按钮周围的垂直内边距，决定按钮与其他元素的空间间隔
option_menu_width = entry_width      # 下拉选项菜单的宽度，例如"Module Type"和"Has Review Table"的选择菜单


# 标签名称
label_names = {
    "openai_api_key": "OpenAI API Key",
    "tyqw_api_key": "通义千问 API Key",
    "module_type": "Module Type",
    "prompt": "Prompt",
    "max_length": "单次审校最大字数",
    "has_review_table": "有无审校表格"
}

# 主窗口设置
root = tk.Tk()
root.title("Config Editor")

# # 文件路径设置
# current_dir = os.path.dirname(os.path.abspath(__file__))
# config_file_path = os.path.join(current_dir, "hide_file", "配置文件", "config.json")  # 注意这里改为 config.json

# 配置项定义
config_keys = list(label_names.keys())
config_vars = {key: tk.StringVar() for key in config_keys}

# 配置项输入界面
for i, key in enumerate(config_keys):
    tk.Label(root, text=f"{label_names[key]}:", width=label_width).grid(row=i, column=0, sticky='w')

    if key == "module_type":
        options = ["gpt-4-0125-preview", "gpt-3.5-turbo-16k", "gpt-3.5-turbo", "通义千问"]
        config_vars[key].set(options[0])
        option_menu = tk.OptionMenu(root, config_vars[key], *options)
        option_menu.config(width=option_menu_width)
        option_menu.grid(row=i, column=1, sticky='ew')
    elif key == "has_review_table":
        options = ["Y", "N"]
        config_vars[key].set(options[0])
        option_menu = tk.OptionMenu(root, config_vars[key], *options)
        option_menu.config(width=option_menu_width)
        option_menu.grid(row=i, column=1, sticky='ew')
    elif key != "prompt":
        tk.Entry(root, textvariable=config_vars[key], width=entry_width).grid(row=i, column=1, sticky='ew')

# 多行文本字段处理
prompt_label = tk.Label(root, text=f"{label_names['prompt']}:", width=label_width) # 标签
prompt_text = scrolledtext.ScrolledText(root, height=prompt_text_height, width=prompt_text_width) # 多行文本输入框
prompt_text.grid(row=config_keys.index("prompt"), column=1, sticky='ew')  # 前

# 保存按钮
save_button = tk.Button(root, text="Save Configuration", command=lambda: save_config(config_file_path))
save_button.grid(row=len(config_keys) + 1, column=0, columnspan=2, pady=button_pad_y)

# 加载配置文件
config_file_path = get_config_file_path()
load_config(config_file_path)

# 主循环
root.mainloop()

