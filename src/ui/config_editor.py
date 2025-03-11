import ttkbootstrap as ttk
from tkinter import messagebox, scrolledtext, LEFT, RIGHT, TOP, BOTH, X, Y, W
from config import config_manager, MODULE_LIST, LABEL_NAMES, LABEL_WIDTH, ENTRY_WIDTH, PROMPT_TEXT_HEIGHT, PROMPT_TEXT_WIDTH

class ConfigEditor:
    def __init__(self):
        self.root = None
        self.config_vars = {}
        self.prompt_text = None
    
    def create_window(self):
        """创建配置编辑器窗口"""
        self.root = ttk.Window(themename="litera")
        self.root.title("配置编辑器")
        self.root.geometry("800x600")
        
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # 创建标题
        title = ttk.Label(main_frame, 
                         text="配置编辑器",
                         font=config_manager.theme_manager.get_font('title'),
                         bootstyle="primary")
        title.pack(pady=20)
        
        # 配置项定义
        config_keys = list(LABEL_NAMES.keys())
        self.config_vars = {key: ttk.StringVar() for key in config_keys}
        
        # 创建配置项框架
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill=X, pady=10)
        
        # 创建配置项输入界面
        for i, key in enumerate(config_keys):
            if key != "prompt":
                frame = ttk.Frame(config_frame)
                frame.pack(fill=X, pady=5)
                
                label = ttk.Label(frame,
                                text=f"{LABEL_NAMES[key]}:",
                                width=LABEL_WIDTH)
                label.pack(side=LEFT)
                
                if key == "module_type":
                    options = MODULE_LIST
                    self.config_vars[key].set(options[0])
                    option_menu = ttk.OptionMenu(frame, self.config_vars[key], options[0], *options)
                    option_menu.pack(side=LEFT, fill=X, expand=True)
                elif key == "has_review_table":
                    options = ["Y", "N"]
                    self.config_vars[key].set(options[0])
                    option_menu = ttk.OptionMenu(frame, self.config_vars[key], options[0], *options)
                    option_menu.pack(side=LEFT, fill=X, expand=True)
                else:
                    entry = ttk.Entry(frame,
                                    textvariable=self.config_vars[key],
                                    width=ENTRY_WIDTH)
                    entry.pack(side=LEFT, fill=X, expand=True)
        
        # Prompt 输入区域
        prompt_frame = ttk.Frame(main_frame)
        prompt_frame.pack(fill=BOTH, expand=True, pady=10)
        
        prompt_label = ttk.Label(prompt_frame,
                               text=f"{LABEL_NAMES['prompt']}:",
                               bootstyle="primary")
        prompt_label.pack(anchor=W)
        
        self.prompt_text = scrolledtext.ScrolledText(
            prompt_frame,
            height=PROMPT_TEXT_HEIGHT,
            width=PROMPT_TEXT_WIDTH,
            font=config_manager.theme_manager.get_font('input')
        )
        self.prompt_text.pack(fill=BOTH, expand=True, pady=5)
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        save_button = ttk.Button(button_frame,
                               text="保存配置",
                               bootstyle="success",
                               command=self.save_config)
        save_button.pack(side=LEFT, padx=10)
        
        cancel_button = ttk.Button(button_frame,
                                text="取消",
                                bootstyle="secondary",
                                command=self.root.destroy)
        cancel_button.pack(side=LEFT, padx=10)
        
        # 设置配置管理器的widgets
        config_manager.config_vars = self.config_vars
        config_manager.prompt_text = self.prompt_text
        
        # 加载配置
        config_manager.load_config()
        
        # 运行窗口
        self.root.mainloop()
    
    def save_config(self):
        """保存配置"""
        if config_manager.save_config():
            messagebox.showinfo("成功", "配置已保存！")
            self.root.destroy()

if __name__ == "__main__":
    editor = ConfigEditor()
    editor.create_window() 