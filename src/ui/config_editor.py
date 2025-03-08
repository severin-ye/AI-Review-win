import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
from config import config_manager, MODULE_LIST, LABEL_NAMES, LABEL_WIDTH, ENTRY_WIDTH, PROMPT_TEXT_HEIGHT, PROMPT_TEXT_WIDTH

class ConfigEditor:
    def __init__(self):
        self.root = None
        self.config_vars = {}
        self.prompt_text = None
    
    def create_window(self):
        """创建配置编辑器窗口"""
        self.root = tk.Tk()
        self.root.title("配置编辑器")
        self.root.geometry("800x600")
        
        # 应用主题
        config_manager.theme_manager.apply_theme(self.root)
        
        # 设置窗口背景色
        self.root.configure(bg=config_manager.theme_manager.get_color('background'))
        
        # 创建主框架
        main_frame = tk.Frame(self.root, bg=config_manager.theme_manager.get_color('background'))
        main_frame.pack(fill=tk.BOTH, expand=True, padx=config_manager.theme_manager.get_padding('frame'), 
                       pady=config_manager.theme_manager.get_padding('frame'))
        
        # 创建标题
        title = ttk.Label(main_frame, text="配置编辑器", style='Title.TLabel')
        title.pack(pady=20)
        
        # 配置项定义
        config_keys = list(LABEL_NAMES.keys())
        self.config_vars = {key: tk.StringVar() for key in config_keys}
        
        # 创建配置项框架
        config_frame = tk.Frame(main_frame, bg=config_manager.theme_manager.get_color('background'))
        config_frame.pack(fill=tk.X, pady=10)
        
        # 配置项输入界面
        for key in config_keys:
            if key != "prompt":
                frame = tk.Frame(config_frame, bg=config_manager.theme_manager.get_color('background'))
                frame.pack(fill=tk.X, pady=5)
                
                label = ttk.Label(frame,
                                text=f"{LABEL_NAMES[key]}:",
                                width=LABEL_WIDTH,
                                style='Config.TLabel')
                label.pack(side=tk.LEFT)
                
                if key == "module_type":
                    options = MODULE_LIST
                    self.config_vars[key].set(options[0])
                    option_menu = ttk.OptionMenu(frame, self.config_vars[key], options[0], *options)
                    option_menu.config(width=ENTRY_WIDTH)
                    option_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
                elif key == "has_review_table":
                    options = ["Y", "N"]
                    self.config_vars[key].set(options[0])
                    option_menu = ttk.OptionMenu(frame, self.config_vars[key], options[0], *options)
                    option_menu.config(width=ENTRY_WIDTH)
                    option_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
                else:
                    entry = ttk.Entry(frame,
                                    textvariable=self.config_vars[key],
                                    width=ENTRY_WIDTH,
                                    font=('Microsoft YaHei UI', 10))
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Prompt 输入区域
        prompt_frame = tk.Frame(main_frame, bg=config_manager.theme_manager.get_color('background'))
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        prompt_label = ttk.Label(prompt_frame,
                               text=f"{LABEL_NAMES['prompt']}:",
                               style='Config.TLabel')
        prompt_label.pack(anchor=tk.W)
        
        self.prompt_text = scrolledtext.ScrolledText(
            prompt_frame,
            height=PROMPT_TEXT_HEIGHT,
            width=PROMPT_TEXT_WIDTH,
            font=('Microsoft YaHei UI', 10),
            bg='white'
        )
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 按钮区域
        button_frame = tk.Frame(main_frame, bg=config_manager.theme_manager.get_color('background'))
        button_frame.pack(pady=20)
        
        save_button = ttk.Button(
            button_frame,
            text="保存配置",
            style='Config.TButton',
            command=self.save_config
        )
        save_button.pack()
        
        # 设置配置管理器的小部件引用
        config_manager.set_widgets(self.config_vars, self.prompt_text)
        
        # 加载配置
        config_manager.load_config()
    
    def save_config(self):
        """保存配置"""
        config_manager.save_config()
    
    def run(self):
        """运行配置编辑器"""
        self.create_window()
        self.root.mainloop()

if __name__ == "__main__":
    editor = ConfigEditor()
    editor.run() 