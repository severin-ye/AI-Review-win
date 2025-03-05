import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import os
import importlib.util
import sys
import json
from src.styles.theme_manager import theme_manager

# 模块列表
module_list = ['gpt-4o', 'gpt-4o-mini', '通义千问']

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
    "has_review_table": "有无审校表格",
    "output_dir": "输出目录"
}

class ConfigManager:
    def __init__(self):
        self.config_vars = {}
        self.prompt_text = None
        self.module_list = module_list
        self.label_names = label_names
        self.label_width = label_width
        self.entry_width = entry_width
        self.prompt_text_height = prompt_text_height
        self.prompt_text_width = prompt_text_width
        self.button_pad_y = button_pad_y
        self.option_menu_width = option_menu_width
        self.default_output_dir = os.path.join(os.getcwd(), "_2_审校后")
    
    def set_widgets(self, config_vars, prompt_text=None):
        """设置配置变量和prompt文本框"""
        self.config_vars = config_vars
        self.prompt_text = prompt_text
    
    def validate_api_key(self, api_key, key_type):
        """验证 API 密钥的格式
        
        Args:
            api_key (str): API 密钥
            key_type (str): 密钥类型 ('openai' 或 'tyqw')
            
        Returns:
            bool: 密钥格式是否有效
        """
        if not api_key:
            return True  # 允许空密钥
            
        if key_type == 'openai':
            return api_key.startswith('sk-') and len(api_key) > 20
        elif key_type == 'tyqw':
            return len(api_key) > 20
        return False

    def load_config(self):
        """加载配置文件"""
        try:
            config_file_path = get_config_file_path()
            with open(config_file_path, 'r', encoding='utf-8') as file:
                config_data = json.load(file)
            
            # 加载 API 密钥
            api_keys = config_data.get('api_keys', {})
            openai_key = api_keys.get('openai', '')
            tyqw_key = api_keys.get('tyqw', '')
            
            # 验证 API 密钥
            if not self.validate_api_key(openai_key, 'openai'):
                messagebox.showwarning("警告", "OpenAI API 密钥格式无效")
            if not self.validate_api_key(tyqw_key, 'tyqw'):
                messagebox.showwarning("警告", "通义千问 API 密钥格式无效")
            
            # 设置 API 密钥
            self.config_vars['openai_api_key'].set(openai_key)
            self.config_vars['tyqw_api_key'].set(tyqw_key)
            
            # 加载其他配置
            self.config_vars['module_type'].set(config_data.get('module_type', 'gpt-4o'))
            self.config_vars['has_review_table'].set('Y' if config_data.get('has_review_table', True) else 'N')
            self.config_vars['output_dir'].set(config_data.get('output_dir', self.default_output_dir))
            
            # 加载 prompt
            if self.prompt_text:
                self.prompt_text.delete('1.0', tk.END)
                self.prompt_text.insert('1.0', config_data.get('prompt', '你是一个专业的文档审校助手。请仔细审查以下文本，并提供修改建议。'))
            
            return True
            
        except FileNotFoundError:
            # 如果配置文件不存在，使用默认值
            self.config_vars['openai_api_key'].set('')
            self.config_vars['tyqw_api_key'].set('')
            self.config_vars['module_type'].set('gpt-4o')
            self.config_vars['has_review_table'].set('Y')
            self.config_vars['output_dir'].set(self.default_output_dir)
            if self.prompt_text:
                self.prompt_text.delete('1.0', tk.END)
                self.prompt_text.insert('1.0', '你是一个专业的文档审校助手。请仔细审查以下文本，并提供修改建议。')
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"无法加载配置：{str(e)}")
            return False
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 验证 API 密钥
            openai_key = self.config_vars["openai_api_key"].get().strip()
            tyqw_key = self.config_vars["tyqw_api_key"].get().strip()
            
            if not self.validate_api_key(openai_key, 'openai'):
                messagebox.showerror("错误", "OpenAI API 密钥格式无效")
                return False
                
            if not self.validate_api_key(tyqw_key, 'tyqw'):
                messagebox.showerror("错误", "通义千问 API 密钥格式无效")
                return False

            # 获取 prompt 内容
            prompt_content = ""
            if self.prompt_text:
                try:
                    prompt_content = self.prompt_text.get('1.0', tk.END).strip()
                except Exception as e:
                    print(f"获取 prompt 内容时出错：{str(e)}")
                    prompt_content = "你是一个专业的文档审校助手。请仔细审查以下文本，并提供修改建议。"

            # 构建配置数据
            config_data = {
                "api_keys": {
                    "openai": openai_key,
                    "tyqw": tyqw_key
                },
                "module_type": self.config_vars["module_type"].get(),
                "has_review_table": self.config_vars["has_review_table"].get() == 'Y',
                "output_dir": self.config_vars["output_dir"].get(),
                "prompt": prompt_content
            }
            
            # 获取配置文件路径并确保目录存在
            config_file_path = get_config_file_path()
            os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
            
            # 保存配置
            with open(config_file_path, 'w', encoding='utf-8') as file:
                json.dump(config_data, file, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("成功", "配置已保存")
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"无法保存配置：{str(e)}")
            return False

def get_config_file_path():
    """获取配置文件的路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        application_path = os.path.dirname(sys.executable)
    else:
        # 如果是开发环境
        application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    config_dir = os.path.join(application_path, "hide_file", "配置文件")
    config_file = os.path.join(config_dir, "config.json")
    
    # 确保配置目录存在
    os.makedirs(config_dir, exist_ok=True)
    
    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_file):
        default_config = {
            "api_keys": {
                "openai": "",
                "tyqw": ""
            },
            "module_type": "gpt-4o",
            "has_review_table": True,
            "output_dir": os.path.join(os.getcwd(), "_2_审校后"),
            "prompt": "你是一个专业的文档审校助手。请仔细审查以下文本，并提供修改建议。"
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
    
    return config_file

# 创建全局配置管理器实例
config_manager = ConfigManager()

if __name__ == "__main__":
    # 主窗口设置
    root = tk.Tk()
    root.title("配置编辑器")
    root.geometry("800x600")
    
    # 应用主题
    theme_manager.apply_theme(root)
    
    # 设置窗口背景色
    root.configure(bg=theme_manager.get_color('background'))
    
    # 创建主框架
    main_frame = tk.Frame(root, bg=theme_manager.get_color('background'))
    main_frame.pack(fill=tk.BOTH, expand=True, padx=theme_manager.get_padding('frame'), pady=theme_manager.get_padding('frame'))
    
    # 创建标题
    title = ttk.Label(main_frame,
                     text="配置编辑器",
                     style='Title.TLabel')
    title.pack(pady=20)
    
    # 配置项定义
    config_keys = list(label_names.keys())
    config_vars = {key: tk.StringVar() for key in config_keys}
    
    # 创建配置项框架
    config_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
    config_frame.pack(fill=tk.X, pady=10)
    
    # 配置项输入界面
    for i, key in enumerate(config_keys):
        if key != "prompt":
            frame = tk.Frame(config_frame, bg=theme_manager.get_color('background'))
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
            elif key == "output_dir":
                entry = ttk.Entry(frame,
                                textvariable=config_vars[key],
                                width=entry_width,
                                font=('Microsoft YaHei UI', 10))
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Prompt 输入区域
    prompt_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
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
    button_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
    button_frame.pack(pady=20)
    
    save_button = ttk.Button(
        button_frame,
        text="保存配置",
        style='Config.TButton',
        command=lambda: config_manager.save_config()
    )
    save_button.pack()
    
    # 加载配置文件
    config_manager.set_widgets(config_vars, prompt_text)
    config_manager.load_config()
    
    # 主循环
    root.mainloop()
