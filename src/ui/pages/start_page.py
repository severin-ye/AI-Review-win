import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import shutil
from src.ui.styles.theme_manager import theme_manager
from src.utils import cleanup_utils
from config.managers import config_manager

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg=theme_manager.get_color('background'))
        self.controller = controller  # 保存controller引用
        
        # 使用全局配置管理器实例
        self.config_manager = config_manager
        
        # 创建标题
        title = ttk.Label(self, 
                         text="AI审校助手",
                         style='Title.TLabel')
        title.pack(pady=50)
        
        # 创建主按钮容器
        main_button_frame = tk.Frame(self, bg=theme_manager.get_color('background'))
        main_button_frame.pack(expand=True)
        
        # 创建左侧按钮容器
        left_button_frame = tk.Frame(main_button_frame, bg=theme_manager.get_color('background'))
        left_button_frame.pack(side=tk.LEFT, padx=20)
        
        # 创建右侧按钮容器
        right_button_frame = tk.Frame(main_button_frame, bg=theme_manager.get_color('background'))
        right_button_frame.pack(side=tk.LEFT, padx=20)
        
        # 左侧按钮（文件操作）
        left_buttons = [
            ("上传文件", self.upload_file, 'Main.TButton'),
            ("清理文件", self.clear_files, 'Secondary.TButton'),
        ]
        
        # 右侧按钮（程序操作）
        right_buttons = [
            ("开始处理", self.show_process_page, 'Success.TButton'),
            ("配置设置", self.show_config_page, 'Main.TButton'),
            ("退出程序", self.quit_app, 'Danger.TButton')
        ]
        
        # 创建左侧按钮
        for text, command, style in left_buttons:
            btn = ttk.Button(left_button_frame,
                          text=text,
                          style=style,
                          command=command)
            btn.pack(pady=10)
        
        # 创建右侧按钮
        for text, command, style in right_buttons:
            btn = ttk.Button(right_button_frame,
                          text=text,
                          style=style,
                          command=command)
            btn.pack(pady=10)
        
        # 创建配置页面（初始隐藏）
        self.config_frame = tk.Frame(self)
        self.create_config_page()
    
    def show_process_page(self):
        """显示处理页面"""
        from src.ui.pages.process_page import ProcessPage  # 动态导入
        self.controller.show_frame(ProcessPage)
    
    def upload_file(self):
        """上传文件功能"""
        files = filedialog.askopenfilenames(
            title="选择要审校的文件",
            filetypes=[
                ("Word文档", "*.docx;*.doc"),
                ("所有文件", "*.*")
            ]
        )
        
        if not files:
            return
            
        # 确保目标目录存在
        target_dir = os.path.join(os.getcwd(), "_1_原文件")
        os.makedirs(target_dir, exist_ok=True)
        
        # 复制选中的文件到目标目录
        success_count = 0
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                target_path = os.path.join(target_dir, file_name)
                shutil.copy2(file_path, target_path)
                success_count += 1
            except Exception as e:
                messagebox.showerror("错误", f"复制文件 {file_name} 时出错：{str(e)}")
        
        # 显示成功消息
        if success_count > 0:
            messagebox.showinfo("上传成功", f"成功上传 {success_count} 个文件到处理目录！")
    
    def clear_files(self):
        """运行清理文件脚本"""
        try:
            directories_to_clean = [r"_1_原文件", r"_2_审校后", r"hide_file\中间文件"]
            all_error_names = []
            
            for dir_path in directories_to_clean:
                error_names = cleanup_utils.delete_files_and_folders_in_directory(dir_path)
                if isinstance(error_names, str):
                    all_error_names.append(error_names)
                else:
                    all_error_names.extend(error_names)
            
            if not all_error_names:
                messagebox.showinfo("清理完成", "已成功清理所有文件！")
            else:
                messagebox.showinfo("清理完成", "以下文件或文件夹清理失败：\n" + "\n".join(all_error_names))
        except Exception as e:
            messagebox.showerror("错误", f"清理文件时出错：{str(e)}")
    
    def show_config_page(self):
        """显示配置页面"""
        # 隐藏主页面的所有组件
        for widget in self.winfo_children():
            if widget != self.config_frame:
                widget.pack_forget()
        
        # 显示配置页面
        self.config_frame.pack(fill="both", expand=True)
        
        # 加载配置
        self.config_manager.load_config()
    
    def create_config_page(self):
        """创建配置页面"""
        # 创建主框架
        main_frame = tk.Frame(self.config_frame, bg=self.master.master.colors['background'])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题
        title = ttk.Label(main_frame,
                         text="配置设置",
                         style='Title.TLabel')
        title.pack(pady=20)
        
        # 创建配置项框架
        config_frame = tk.Frame(main_frame, bg=self.master.master.colors['background'])
        config_frame.pack(fill="x", pady=10)
        
        # 配置项定义
        self.config_keys = list(self.config_manager.label_names.keys())
        self.config_vars = {key: tk.StringVar() for key in self.config_keys}
        
        # 创建配置项输入界面
        for i, key in enumerate(self.config_keys):
            if key != "prompt":
                frame = tk.Frame(config_frame, bg=self.master.master.colors['background'])
                frame.pack(fill="x", pady=5)
                
                label = ttk.Label(frame,
                                text=f"{self.config_manager.label_names[key]}:",
                                width=self.config_manager.label_width,
                                background=self.master.master.colors['background'])
                label.pack(side="left")
                
                if key == "module_type":
                    options = self.config_manager.module_list
                    self.config_vars[key].set(options[0])
                    option_menu = ttk.OptionMenu(frame, self.config_vars[key], options[0], *options)
                    option_menu.config(width=self.config_manager.option_menu_width)
                    option_menu.pack(side="left", fill="x", expand=True)
                elif key == "has_review_table":
                    options = ["Y", "N"]
                    self.config_vars[key].set(options[0])
                    option_menu = ttk.OptionMenu(frame, self.config_vars[key], options[0], *options)
                    option_menu.config(width=self.config_manager.option_menu_width)
                    option_menu.pack(side="left", fill="x", expand=True)
                elif key == "output_dir":
                    # 创建输出目录选择框架
                    dir_frame = tk.Frame(frame, bg=self.master.master.colors['background'])
                    dir_frame.pack(side="left", fill="x", expand=True)
                    
                    # 创建输入框
                    entry = ttk.Entry(dir_frame,
                                    textvariable=self.config_vars[key],
                                    width=self.config_manager.entry_width - 10,
                                    font=self.master.master.default_font)
                    entry.pack(side="left", fill="x", expand=True)
                    
                    # 创建浏览按钮
                    browse_btn = ttk.Button(dir_frame,
                                          text="浏览",
                                          command=lambda: self.browse_output_dir(key),
                                          width=8)
                    browse_btn.pack(side="left", padx=5)
                else:
                    entry = ttk.Entry(frame,
                                    textvariable=self.config_vars[key],
                                    width=self.config_manager.entry_width,
                                    font=self.master.master.default_font)
                    entry.pack(side="left", fill="x", expand=True)
        
        # Prompt 输入区域
        prompt_frame = tk.Frame(main_frame, bg=self.master.master.colors['background'])
        prompt_frame.pack(fill="both", expand=True, pady=10)
        
        prompt_label = ttk.Label(prompt_frame,
                               text=f"{self.config_manager.label_names['prompt']}:",
                               background=self.master.master.colors['background'])
        prompt_label.pack(anchor="w")
        
        self.prompt_text = tk.scrolledtext.ScrolledText(
            prompt_frame,
            height=self.config_manager.prompt_text_height,
            width=self.config_manager.prompt_text_width,
            font=self.master.master.default_font,
            bg='white'
        )
        self.prompt_text.pack(fill="both", expand=True, pady=5)
        
        # 创建保存和返回按钮
        button_frame = tk.Frame(main_frame, bg=self.master.master.colors['background'])
        button_frame.pack(pady=20)
        
        save_button = ttk.Button(button_frame,
                               text="保存配置",
                               style='Success.TButton',
                               command=self.save_config)
        save_button.pack(side=tk.LEFT, padx=10)
        
        back_button = ttk.Button(button_frame,
                               text="返回主页",
                               style='Secondary.TButton',
                               command=self.show_main_page)
        back_button.pack(side=tk.LEFT, padx=10)
        
        # 设置配置管理器的widgets
        self.config_manager.set_widgets(self.config_vars, self.prompt_text)
    
    def save_config(self):
        """保存配置"""
        self.config_manager.save_config()
    
    def show_main_page(self):
        """返回主页面"""
        # 隐藏配置页面
        self.config_frame.pack_forget()
        
        # 重新显示主页面的所有组件
        for widget in self.winfo_children():
            if widget != self.config_frame:
                widget.pack()
        
        # 重新排列主要组件
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Label) and widget.cget("text") == "AI审校助手":
                widget.pack(pady=50)
            elif isinstance(widget, tk.Frame) and widget != self.config_frame:
                widget.pack(expand=True)
    
    def browse_output_dir(self, key):
        """浏览并选择输出目录"""
        # 获取当前目录
        current_dir = self.config_vars[key].get()
        if not current_dir or not os.path.exists(current_dir):
            current_dir = os.getcwd()
        
        # 打开目录选择对话框
        selected_dir = filedialog.askdirectory(
            title="选择输出目录",
            initialdir=current_dir
        )
        
        # 如果选择了目录，更新配置
        if selected_dir:
            self.config_vars[key].set(selected_dir)
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.quit() 