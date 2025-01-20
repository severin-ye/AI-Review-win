import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import os
import importlib.util
import sys
import json

# 模块列表
module_list =  ['gpt-4o', 'gpt-4o-mini', '通义千问']

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
        # config_vars['max_length'].set(str(config_data.get('max_length', '')))
        config_vars['has_review_table'].set('Y' if config_data.get('has_review_table', True) else 'N')
        
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
            # "max_length": int(config_vars["max_length"].get()),
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
    # "max_length": "单次审校最大字数",
    "has_review_table": "有无审校表格"
}


if __name__ == "__main__":
    # 主窗口设置
    root = tk.Tk()
    root.title("配置编辑器")
    root.geometry("800x600")
    
    # 定义颜色主题
    COLORS = {
        'primary': '#2196F3',    # 主色调 - 蓝色
        'secondary': '#FFC107',  # 次要色调 - 琥珀色
        'background': '#F5F5F5', # 背景色 - 浅灰
        'text': '#333333',       # 文本色 - 深灰
        'button': '#1976D2',     # 按钮色 - 深蓝
        'button_hover': '#1565C0', # 按钮悬停色
        'border': '#E0E0E0'      # 边框色 - 灰色
    }
    
    # 设置窗口背景色
    root.configure(bg=COLORS['background'])
    
    # 创建主框架
    main_frame = tk.Frame(root, bg=COLORS['background'])
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # 创建标题
    title = ttk.Label(main_frame,
                     text="配置编辑器",
                     font=('Microsoft YaHei UI', 24, 'bold'),
                     background=COLORS['background'],
                     foreground=COLORS['primary'])
    title.pack(pady=20)
    
    # 配置全局样式
    style = ttk.Style()
    style.configure('Config.TLabel',
                   font=('Microsoft YaHei UI', 10),
                   background=COLORS['background'])
    
    style.configure('Config.TButton',
                   font=('Microsoft YaHei UI', 10),
                   padding=(20, 10))
    
    # 配置项定义
    config_keys = list(label_names.keys())
    config_vars = {key: tk.StringVar() for key in config_keys}
    
    # 创建配置项框架
    config_frame = tk.Frame(main_frame, bg=COLORS['background'])
    config_frame.pack(fill=tk.X, pady=10)
    
    # 配置项输入界面
    for i, key in enumerate(config_keys):
        if key != "prompt":
            frame = tk.Frame(config_frame, bg=COLORS['background'])
            frame.pack(fill=tk.X, pady=5)
            
            label = ttk.Label(frame,
                            text=f"{label_names[key]}:",
                            width=label_width,
                            style='Config.TLabel')
            label.pack(side=tk.LEFT)
            
            if key == "module_type":
                options = module_list
                config_vars[key].set(options[0])
                option_menu = ttk.OptionMenu(frame, config_vars[key], options[0], *options)
                option_menu.config(width=option_menu_width)
                option_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
            elif key == "has_review_table":
                options = ["Y", "N"]
                config_vars[key].set(options[0])
                option_menu = ttk.OptionMenu(frame, config_vars[key], options[0], *options)
                option_menu.config(width=option_menu_width)
                option_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
            else:
                entry = ttk.Entry(frame,
                                textvariable=config_vars[key],
                                width=entry_width,
                                font=('Microsoft YaHei UI', 10))
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Prompt 输入区域
    prompt_frame = tk.Frame(main_frame, bg=COLORS['background'])
    prompt_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    prompt_label = ttk.Label(prompt_frame,
                           text=f"{label_names['prompt']}:",
                           style='Config.TLabel')
    prompt_label.pack(anchor=tk.W)
    
    prompt_text = scrolledtext.ScrolledText(
        prompt_frame,
        height=prompt_text_height,
        width=prompt_text_width,
        font=('Microsoft YaHei UI', 10),
        bg='white'
    )
    prompt_text.pack(fill=tk.BOTH, expand=True, pady=5)
    
    # 按钮区域
    button_frame = tk.Frame(main_frame, bg=COLORS['background'])
    button_frame.pack(pady=20)
    
    save_button = ttk.Button(
        button_frame,
        text="保存配置",
        style='Config.TButton',
        command=lambda: save_config(get_config_file_path())
    )
    save_button.pack()
    
    # 加载配置文件
    config_file_path = get_config_file_path()
    load_config(config_file_path)
    
    # 主循环
    root.mainloop()
