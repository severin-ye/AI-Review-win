import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import os
import sys
import subprocess
from w6_1_key_generator import SECRET_KEY  # 导入密钥
import time
import json
import threading
import queue

class KeyVerifyPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        
        title = tk.Label(self, text="密钥验证", font=("Helvetica", 24))
        title.pack(pady=50)
        
        # 创建输入框
        self.key_entry = ttk.Entry(self, width=40)
        self.key_entry.pack(pady=10)
        
        # 创建验证按钮
        verify_button = tk.Button(self, text="验证",
                                command=lambda: self.verify_key(controller),
                                width=20, height=2)
        verify_button.pack(pady=10)
    
    def verify_key(self, controller):
        """验证密钥"""
        try:
            key = self.key_entry.get().strip()
            if not key:
                messagebox.showerror("错误", "请输入密钥！")
                return
            
            # 导入验证模块
            try:
                import w6_2_key_verifier
                if w6_2_key_verifier.verify_key(key, SECRET_KEY):
                    os.environ['AI_REVIEW_VERIFIED'] = 'TRUE'  # 设置验证通过的环境变量
                    controller.show_frame(StartPage)
                else:
                    messagebox.showerror("错误", "无效的密钥！")
            except ImportError:
                messagebox.showerror("错误", "无法加载验证模块！")
                
        except Exception as e:
            messagebox.showerror("错误", f"验证过程出错：{str(e)}")

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("AI审校助手")
        self.geometry("800x600")
        
        # 创建一个容器来存放所有页面
        container = tk.Frame(self)
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
        
        # 创建标题
        title = tk.Label(self, text="AI审校助手", font=("Helvetica", 24))
        title.pack(pady=50)
        
        # 创建按钮
        process_button = tk.Button(self, text="开始处理",
                                 command=lambda: controller.show_frame(ProcessPage),
                                 width=20, height=2)
        process_button.pack(pady=10)
        
        clear_button = tk.Button(self, text="清理文件",
                               command=self.clear_files,
                               width=20, height=2)
        clear_button.pack(pady=10)
        
        config_button = tk.Button(self, text="配置设置",
                                command=self.open_config,
                                width=20, height=2)
        config_button.pack(pady=10)
        
        exit_button = tk.Button(self, text="退出程序",
                              command=self.quit_app,
                              width=20, height=2)
        exit_button.pack(pady=10)
    
    def clear_files(self):
        """运行清理文件脚本"""
        try:
            # 导入模块
            import s_3_clear_out
            # 直接调用主要功能
            directories_to_clean = [r"_1_原文件", r"_2_审校后", r"hide_file\中间文件"]
            all_error_names = []
            
            for dir_path in directories_to_clean:
                error_names = s_3_clear_out.delete_files_and_folders_in_directory(dir_path)
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
    
    def open_config(self):
        """运行配置脚本"""
        try:
            # 导入模块
            import s_4_config_use
            # 创建配置窗口
            config_root = tk.Toplevel()
            config_root.title("Config Editor")
            
            # 配置项定义
            config_keys = list(s_4_config_use.label_names.keys())
            self.config_vars = {key: tk.StringVar() for key in config_keys}
            
            # 配置项输入界面
            for i, key in enumerate(config_keys):
                tk.Label(config_root, text=f"{s_4_config_use.label_names[key]}:", width=s_4_config_use.label_width).grid(row=i, column=0, sticky='w')
                
                if key == "module_type":
                    options = s_4_config_use.module_list
                    self.config_vars[key].set(options[0])
                    option_menu = tk.OptionMenu(config_root, self.config_vars[key], *options)
                    option_menu.config(width=s_4_config_use.option_menu_width)
                    option_menu.grid(row=i, column=1, sticky='ew')
                elif key == "has_review_table":
                    options = ["Y", "N"]
                    self.config_vars[key].set(options[0])
                    option_menu = tk.OptionMenu(config_root, self.config_vars[key], *options)
                    option_menu.config(width=s_4_config_use.option_menu_width)
                    option_menu.grid(row=i, column=1, sticky='ew')
                elif key != "prompt":
                    tk.Entry(config_root, textvariable=self.config_vars[key], width=s_4_config_use.entry_width).grid(row=i, column=1, sticky='ew')
            
            # 多行文本字段处理
            prompt_label = tk.Label(config_root, text=f"{s_4_config_use.label_names['prompt']}:", width=s_4_config_use.label_width)
            self.prompt_text = scrolledtext.ScrolledText(config_root, height=s_4_config_use.prompt_text_height, width=s_4_config_use.prompt_text_width)
            self.prompt_text.grid(row=config_keys.index("prompt"), column=1, sticky='ew')
            
            def save_config():
                """保存配置"""
                try:
                    config_data = {
                        "api_keys": {
                            "openai": self.config_vars["openai_api_key"].get(),
                            "tyqw": self.config_vars["tyqw_api_key"].get()
                        },
                        "module_type": self.config_vars["module_type"].get(),
                        "prompt": self.prompt_text.get('1.0', tk.END).strip(),
                        "has_review_table": self.config_vars["has_review_table"].get() == 'Y'
                    }
                    
                    config_file_path = s_4_config_use.get_config_file_path()
                    os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
                    
                    with open(config_file_path, 'w', encoding='utf-8') as file:
                        json.dump(config_data, file, indent=4)
                    
                    messagebox.showinfo("Information", "Configuration Saved Successfully")
                except Exception as e:
                    messagebox.showerror("Error", f"Unable to save configuration: {str(e)}")
            
            # 保存按钮
            save_button = tk.Button(config_root, text="Save Configuration", command=save_config)
            save_button.grid(row=len(config_keys) + 1, column=0, columnspan=2, pady=s_4_config_use.button_pad_y)
            
            # 加载配置文件
            try:
                config_file_path = s_4_config_use.get_config_file_path()
                with open(config_file_path, 'r', encoding='utf-8') as file:
                    config_data = json.load(file)
                
                # 加载 API 密钥
                api_keys = config_data.get('api_keys', {})
                self.config_vars['openai_api_key'].set(api_keys.get('openai', ''))
                self.config_vars['tyqw_api_key'].set(api_keys.get('tyqw', ''))
                
                # 加载其他配置
                self.config_vars['module_type'].set(config_data.get('module_type', ''))
                self.config_vars['has_review_table'].set('Y' if config_data.get('has_review_table', False) else 'N')
                
                # 加载 prompt
                self.prompt_text.delete('1.0', tk.END)
                self.prompt_text.insert('1.0', config_data.get('prompt', ''))
            except Exception as e:
                messagebox.showerror("Error", f"Unable to load configuration: {str(e)}")
            
            # 设置模态对话框
            config_root.transient(config_root.master)
            config_root.grab_set()
            config_root.mainloop()
        except Exception as e:
            messagebox.showerror("错误", f"打开配置界面时出错：{str(e)}")

class ProcessPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        
        # 创建消息队列用于线程间通信
        self.progress_queue = queue.Queue()
        
        title = tk.Label(self, text="处理文件", font=("Helvetica", 24))
        title.pack(pady=50)
        
        auto_process_button = tk.Button(self, text="自动处理",
                                      command=self.auto_process,
                                      width=20, height=2)
        auto_process_button.pack(pady=10)
        
        manual_process_button = tk.Button(self, text="人工审校",
                                        command=self.manual_process,
                                        width=20, height=2)
        manual_process_button.pack(pady=10)
        
        back_button = tk.Button(self, text="返回主页",
                              command=lambda: controller.show_frame(StartPage),
                              width=20, height=2)
        back_button.pack(pady=10)
    
    class ProgressWindow:
        def __init__(self, total_files):
            self.root = tk.Toplevel()
            self.root.title("处理进度")
            self.root.geometry("400x200")  # 增加窗口高度以容纳更多信息
            
            # 设置窗口在屏幕中央
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - 400) // 2
            y = (screen_height - 200) // 2
            self.root.geometry(f"400x200+{x}+{y}")
            
            # 创建文件总进度条
            self.file_progress_label = tk.Label(self.root, text="总体进度:")
            self.file_progress_label.pack(pady=(20,5))
            
            self.file_progress_var = tk.DoubleVar()
            self.file_progress_bar = ttk.Progressbar(
                self.root, 
                variable=self.file_progress_var,
                maximum=total_files,
                length=300,
                mode='determinate'
            )
            self.file_progress_bar.pack(pady=5)
            
            # 创建当前文件进度条
            self.current_progress_label = tk.Label(self.root, text="当前文件进度:")
            self.current_progress_label.pack(pady=(10,5))
            
            self.current_progress_var = tk.DoubleVar()
            self.current_progress_bar = ttk.Progressbar(
                self.root, 
                variable=self.current_progress_var,
                maximum=100,
                length=300,
                mode='determinate'
            )
            self.current_progress_bar.pack(pady=5)
            
            # 创建标签显示当前处理的文件
            self.label_var = tk.StringVar()
            self.label = tk.Label(self.root, textvariable=self.label_var)
            self.label.pack(pady=10)
            
            # 创建百分比标签
            self.percent_var = tk.StringVar()
            self.percent_label = tk.Label(self.root, textvariable=self.percent_var)
            self.percent_label.pack(pady=5)
            
            # 设置窗口置顶
            self.root.lift()
            self.root.attributes('-topmost', True)
            
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
        import s_1_auto_ai
        for index, (file_name, file_type) in enumerate(zip(file_name_list, file_type_list), 1):
            current_progress = {"value": 0}
            
            def update_progress(progress):
                current_progress["value"] = progress
                self.progress_queue.put((index, file_name, progress))
            
            s_1_auto_ai.process_file(file_name, file_type, progress_callback=update_progress)
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
                if messagebox.askyesno("完成", f"AI程序执行完毕, 当前时间: {time_now}\n是否退出程序?"):
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
            # 导入模块
            import s_1_auto_ai
            
            # 获取文件列表
            file_name_list, file_type_list = s_1_auto_ai.traverse_folder(os.path.join(os.getcwd(), "_1_原文件"))
            
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
            # 导入模块
            import s_2_select_replace
            # 直接调用主要功能
            s_2_select_replace.revision_use()
        except Exception as e:
            messagebox.showerror("错误", f"人工审校时出错：{str(e)}")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
