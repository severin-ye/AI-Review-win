import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import os
import sys
import subprocess
import time
import json
import threading
import queue
import shutil

# 从新的模块路径导入
from src.security.key_generator_legacy import SECRET_KEY
from src.security import key_verifier
from src.utils import cleanup_utils
from src.core import ai_review, text_processor
from config.config_manager import ConfigManager
from src.utils.theme_manager import theme_manager

# 创建配置管理器实例
config_manager = ConfigManager()

class KeyVerifyPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg=theme_manager.get_color('background'))
        
        # 创建标题
        title = ttk.Label(self, 
                         text="密钥验证",
                         style='Title.TLabel')
        title.pack(pady=50)
        
        # 创建输入框容器
        entry_frame = tk.Frame(self, bg=theme_manager.get_color('background'))
        entry_frame.pack(pady=20)
        
        # 创建输入框
        self.key_entry = ttk.Entry(entry_frame, 
                                 width=40,
                                 font=theme_manager.get_font('input'))
        self.key_entry.pack(pady=10)
        
        # 创建验证按钮
        verify_button = ttk.Button(self, 
                                text="验证",
                                style='Success.TButton',
                                command=lambda: self.verify_key(controller))
        verify_button.pack(pady=20)
    
    def verify_key(self, controller):
        """验证密钥"""
        try:
            key = self.key_entry.get().strip()
            if not key:
                messagebox.showerror("错误", "请输入密钥！")
                return
            
            # 导入验证模块
            try:
                if key_verifier.verify_key(key, SECRET_KEY):
                    os.environ['AI_REVIEW_VERIFIED'] = 'TRUE'  # 设置验证通过的环境变量
                    controller.show_frame(StartPage)
                else:
                    messagebox.showerror("错误", "无效的密钥！")
            except Exception as e:
                messagebox.showerror("错误", f"验证过程出错：{str(e)}")
                
        except Exception as e:
            messagebox.showerror("错误", f"验证过程出错：{str(e)}")

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和大小
        self.title("AI审校助手")
        self.geometry("800x600")
        
        # 设置全屏显示
        self.state('zoomed')
        
        # 应用主题
        theme_manager.apply_theme(self)
        
        # 存储主题颜色和字体，方便访问
        self.colors = theme_manager.theme['colors']
        self.default_font = theme_manager.get_font('default')
        self.title_font = theme_manager.get_font('title')
        
        # 创建一个容器来存放所有页面
        container = tk.Frame(self, bg=theme_manager.get_color('background'))
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # 存储页面的字典
        self.frames = {}
        
        # 初始化所有页面
        for F in (KeyVerifyPage, StartPage, ProcessPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            
        # 显示密钥验证页面
        self.show_frame(KeyVerifyPage)
    
    def show_frame(self, cont):
        """切换到指定页面"""
        frame = self.frames[cont]
        frame.tkraise()

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg=theme_manager.get_color('background'))
        
        # 创建配置管理器实例
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
            ("开始处理", lambda: controller.show_frame(ProcessPage), 'Success.TButton'),
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
    
    def upload_file(self):
        """上传文件功能"""
        from tkinter import filedialog
        
        # 打开文件选择对话框
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
        self.config_keys = list(config_manager.label_names.keys())
        self.config_vars = {key: tk.StringVar() for key in self.config_keys}
        
        # 创建配置项输入界面
        for i, key in enumerate(self.config_keys):
            if key != "prompt":
                frame = tk.Frame(config_frame, bg=self.master.master.colors['background'])
                frame.pack(fill="x", pady=5)
                
                label = ttk.Label(frame,
                                text=f"{config_manager.label_names[key]}:",
                                width=config_manager.label_width,
                                background=self.master.master.colors['background'])
                label.pack(side="left")
                
                if key == "module_type":
                    options = config_manager.module_list
                    self.config_vars[key].set(options[0])
                    option_menu = ttk.OptionMenu(frame, self.config_vars[key], options[0], *options)
                    option_menu.config(width=config_manager.option_menu_width)
                    option_menu.pack(side="left", fill="x", expand=True)
                elif key == "has_review_table":
                    options = ["Y", "N"]
                    self.config_vars[key].set(options[0])  # 设置默认值为 "Y"
                    option_menu = ttk.OptionMenu(frame, self.config_vars[key], options[0], *options)
                    option_menu.config(width=config_manager.option_menu_width)
                    option_menu.pack(side="left", fill="x", expand=True)
                elif key == "output_dir":
                    # 创建输出目录选择框架
                    dir_frame = tk.Frame(frame, bg=self.master.master.colors['background'])
                    dir_frame.pack(side="left", fill="x", expand=True)
                    
                    # 创建输入框
                    entry = ttk.Entry(dir_frame,
                                    textvariable=self.config_vars[key],
                                    width=config_manager.entry_width - 10,  # 减小宽度以适应按钮
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
                                    width=config_manager.entry_width,
                                    font=self.master.master.default_font)
                    entry.pack(side="left", fill="x", expand=True)
        
        # Prompt 输入区域
        prompt_frame = tk.Frame(main_frame, bg=self.master.master.colors['background'])
        prompt_frame.pack(fill="both", expand=True, pady=10)
        
        prompt_label = ttk.Label(prompt_frame,
                               text=f"{config_manager.label_names['prompt']}:",
                               background=self.master.master.colors['background'])
        prompt_label.pack(anchor="w")
        
        self.prompt_text = scrolledtext.ScrolledText(
            prompt_frame,
            height=config_manager.prompt_text_height,
            width=config_manager.prompt_text_width,
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
    
    def show_main_page(self):
        """返回主页面"""
        # 隐藏配置页面
        self.config_frame.pack_forget()
        
        # 创建标题
        title = ttk.Label(self, 
                         text="AI审校助手",
                         style='Title.TLabel')
        title.pack(pady=50)
        
        # 创建主按钮容器
        main_button_frame = tk.Frame(self, bg=self.master.master.colors['background'])
        main_button_frame.pack(expand=True)
        
        # 创建左侧按钮容器
        left_button_frame = tk.Frame(main_button_frame, bg=self.master.master.colors['background'])
        left_button_frame.pack(side=tk.LEFT, padx=20)
        
        # 创建右侧按钮容器
        right_button_frame = tk.Frame(main_button_frame, bg=self.master.master.colors['background'])
        right_button_frame.pack(side=tk.LEFT, padx=20)
        
        # 左侧按钮（文件操作）
        left_buttons = [
            ("上传文件", self.upload_file, 'Main.TButton'),
            ("清理文件", self.clear_files, 'Secondary.TButton'),
        ]
        
        # 右侧按钮（程序操作）
        right_buttons = [
            ("开始处理", lambda: self.master.master.show_frame(ProcessPage), 'Success.TButton'),
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
    
    def save_config(self):
        """保存配置"""
        self.config_manager.save_config()
    
    def clear_files(self):
        """运行清理文件脚本"""
        try:
            # 导入模块
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
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.quit()

    def browse_output_dir(self, key):
        """浏览并选择输出目录"""
        from tkinter import filedialog
        
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

class ProcessPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg=theme_manager.get_color('background'))
        
        # 创建消息队列用于线程间通信
        self.progress_queue = queue.Queue()
        
        # 创建标题
        title = ttk.Label(self, 
                         text="处理文件",
                         style='Title.TLabel')
        title.pack(pady=50)
        
        # 创建按钮容器
        button_frame = tk.Frame(self, bg=theme_manager.get_color('background'))
        button_frame.pack(expand=True)
        
        # 创建按钮
        buttons = [
            ("自动处理", self.auto_process, 'Success.TButton'),
            ("人工审校", self.manual_process, 'Main.TButton'),
            ("返回主页", lambda: controller.show_frame(StartPage), 'Secondary.TButton')
        ]
        
        for text, command, style in buttons:
            btn = ttk.Button(button_frame,
                          text=text,
                          style=style,
                          command=command)
            btn.pack(pady=10)
    
    class ProgressWindow:
        def __init__(self, total_files):
            self.root = tk.Toplevel()
            self.root.title("处理进度")
            self.root.geometry("500x300")
            
            # 设置窗口在屏幕中央
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - 500) // 2
            y = (screen_height - 300) // 2
            self.root.geometry(f"500x300+{x}+{y}")
            
            # 设置窗口样式
            self.root.configure(bg=theme_manager.get_color('background'))
            
            # 创建主框架
            main_frame = tk.Frame(self.root, bg=theme_manager.get_color('background'))
            main_frame.pack(fill=tk.BOTH, expand=True, padx=theme_manager.get_padding('frame'), pady=theme_manager.get_padding('frame'))
            
            # 创建标题
            title = ttk.Label(main_frame,
                            text="处理进度",
                            style='Subtitle.TLabel')
            title.pack(pady=(0, 20))
            
            # 创建文件总进度条框架
            total_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
            total_frame.pack(fill=tk.X, pady=10)
            
            self.file_progress_label = ttk.Label(total_frame,
                                               text="总体进度:",
                                               style='TLabel')
            self.file_progress_label.pack(anchor='w')
            
            self.file_progress_var = tk.DoubleVar()
            self.file_progress_bar = ttk.Progressbar(
                total_frame,
                variable=self.file_progress_var,
                maximum=total_files,
                length=460,
                mode='determinate'
            )
            self.file_progress_bar.pack(pady=5)
            
            # 创建当前文件进度条框架
            current_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
            current_frame.pack(fill=tk.X, pady=10)
            
            self.current_progress_label = ttk.Label(current_frame,
                                                  text="当前文件进度:",
                                                  style='TLabel')
            self.current_progress_label.pack(anchor='w')
            
            self.current_progress_var = tk.DoubleVar()
            self.current_progress_bar = ttk.Progressbar(
                current_frame,
                variable=self.current_progress_var,
                maximum=100,
                length=460,
                mode='determinate'
            )
            self.current_progress_bar.pack(pady=5)
            
            # 创建信息显示框架
            info_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
            info_frame.pack(fill=tk.X, pady=10)
            
            # 创建标签显示当前处理的文件
            self.label_var = tk.StringVar()
            self.label = ttk.Label(info_frame,
                                textvariable=self.label_var,
                                font=('Microsoft YaHei UI', 10),
                                background=theme_manager.get_color('background'))
            self.label.pack(pady=5)
            
            # 创建百分比标签
            self.percent_var = tk.StringVar()
            self.percent_label = ttk.Label(info_frame,
                                        textvariable=self.percent_var,
                                        font=('Microsoft YaHei UI', 10),
                                        background=theme_manager.get_color('background'))
            self.percent_label.pack(pady=5)
            
            # 设置窗口置顶
            self.root.lift()
            self.root.attributes('-topmost', True)
            
            # 配置进度条样式
            style = ttk.Style()
            style.configure("Horizontal.TProgressbar",
                          troughcolor='#E0E0E0',
                          background='#2196F3',
                          thickness=15)
            
        def update_progress(self, current_file, file_name, current_progress=0):
            self.file_progress_var.set(current_file)
            self.current_progress_var.set(current_progress * 100)
            self.label_var.set(f"正在处理: {file_name}")
            total_percentage = ((current_file - 1 + current_progress) / self.file_progress_bar['maximum']) * 100
            self.percent_var.set(f"总进度: {total_percentage:.1f}%")
            self.root.update()
            
        def close(self):
            self.root.destroy()
    
    def process_files_thread(self, file_name_list, file_type_list):
        """在新线程中处理文件"""
        for index, (file_name, file_type) in enumerate(zip(file_name_list, file_type_list), 1):
            current_progress = {"value": 0}
            
            def update_progress(progress):
                current_progress["value"] = progress
                self.progress_queue.put((index, file_name, progress))
            
            ai_review.process_file(file_name, file_type, progress_callback=update_progress)
            # 确保最后一次进度更新为100%
            self.progress_queue.put((index, file_name, 1.0))
            
        # 处理完成，发送结束信号
        self.progress_queue.put(None)
    
    def update_progress_from_queue(self, progress_window):
        """从队列中更新进度"""
        try:
            # 非阻塞方式获取队列消息
            message = self.progress_queue.get_nowait()
            if message is None:
                # 处理完成
                progress_window.close()
                time_now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                messagebox.showinfo("完成", f"AI程序执行完毕, 当前时间: {time_now}")
                return
            else:
                # 更新进度
                index, file_name, current_progress = message
                progress_window.update_progress(index, file_name, current_progress)
                # 继续检查队列
                self.after(100, lambda: self.update_progress_from_queue(progress_window))
        except queue.Empty:
            # 队列为空，继续等待
            self.after(100, lambda: self.update_progress_from_queue(progress_window))
    
    def auto_process(self):
        """运行自动处理脚本"""
        try:
            # 获取文件列表
            file_name_list, file_type_list = ai_review.traverse_folder(os.path.join(os.getcwd(), "_1_原文件"))
            
            if not file_name_list:
                messagebox.showwarning("警告", "没有找到需要处理的文件！")
                return
            
            # 创建进度条窗口
            progress_window = self.ProgressWindow(len(file_name_list))
            
            # 创建并启动处理线程
            process_thread = threading.Thread(
                target=self.process_files_thread,
                args=(file_name_list, file_type_list),
                daemon=True
            )
            process_thread.start()
            
            # 开始从队列更新进度
            self.after(100, lambda: self.update_progress_from_queue(progress_window))
            
        except Exception as e:
            messagebox.showerror("错误", f"自动处理时出错：{str(e)}")
    
    def manual_process(self):
        """运行人工审校脚本"""
        try:
            # 直接调用主要功能
            text_processor.revision_use()
        except Exception as e:
            messagebox.showerror("错误", f"人工审校时出错：{str(e)}")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
