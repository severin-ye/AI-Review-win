import ttkbootstrap as ttk
from tkinter import messagebox, LEFT, RIGHT, TOP, BOTH, X, Y, W
import os
import threading
from queue import Queue
import time
from src.ui.styles.theme_manager import theme_manager
from src.core import ai_review, text_processor

class ProcessPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller  # 保存controller引用
        
        # 创建消息队列用于线程间通信
        self.progress_queue = Queue()
        
        # 创建标题
        title = theme_manager.create_label(
            self, 
            text="处理文件",
            is_title=True,
            bootstyle="primary"
        )
        title.pack(pady=50)
        
        # 创建按钮容器
        button_frame = ttk.Frame(self)
        button_frame.pack(expand=True)
        
        # 创建按钮
        buttons = [
            ("自动处理", self.auto_process, 'success'),
            ("人工审校", self.manual_process, 'primary'),
            ("返回主页", self.return_to_start, 'info')
        ]
        
        for text, command, bootstyle in buttons:
            btn = theme_manager.create_button(
                button_frame,
                text=text,
                command=command,
                bootstyle=bootstyle
            )
            btn.pack(pady=10)
    
    def return_to_start(self):
        """返回主页"""
        from src.ui.pages.start_page import StartPage  # 动态导入
        self.controller.show_frame(StartPage)
    
    class ProgressWindow:
        def __init__(self, total_files):
            self.root = ttk.Toplevel()
            self.root.title("处理进度")
            self.root.geometry("500x300")
            
            # 设置窗口在屏幕中央
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - 500) // 2
            y = (screen_height - 300) // 2
            self.root.geometry(f"500x300+{x}+{y}")
            
            # 创建主框架
            main_frame = ttk.Frame(self.root)
            main_frame.pack(fill=BOTH, expand=True, padx=theme_manager.get_padding('frame'), pady=theme_manager.get_padding('frame'))
            
            # 创建标题
            title = theme_manager.create_label(
                main_frame,
                text="处理进度",
                is_title=True,
                bootstyle="primary"
            )
            title.pack(pady=(0, 20))
            
            # 创建文件总进度条框架
            total_frame = ttk.Frame(main_frame)
            total_frame.pack(fill=X, pady=10)
            
            self.file_progress_label = theme_manager.create_label(
                total_frame,
                text="总体进度:",
                bootstyle="primary"
            )
            self.file_progress_label.pack(anchor='w')
            
            self.file_progress_var = ttk.DoubleVar()
            self.file_progress_bar = ttk.Progressbar(
                total_frame,
                variable=self.file_progress_var,
                maximum=total_files,
                length=460,
                mode='determinate',
                bootstyle="primary"
            )
            self.file_progress_bar.pack(pady=5)
            
            # 创建当前文件进度条框架
            current_frame = ttk.Frame(main_frame)
            current_frame.pack(fill=X, pady=10)
            
            self.label_var = ttk.StringVar(value="准备开始...")
            self.current_label = theme_manager.create_label(
                current_frame,
                textvariable=self.label_var,
                bootstyle="primary"
            )
            self.current_label.pack(anchor='w')
            
            self.current_progress_var = ttk.DoubleVar()
            self.current_progress_bar = ttk.Progressbar(
                current_frame,
                variable=self.current_progress_var,
                maximum=100,
                length=460,
                mode='determinate',
                bootstyle="success"
            )
            self.current_progress_bar.pack(pady=5)
            
            # 创建百分比标签
            self.percent_var = ttk.StringVar(value="总进度: 0.0%")
            self.percent_label = theme_manager.create_label(
                main_frame,
                textvariable=self.percent_var,
                bootstyle="primary"
            )
            self.percent_label.pack(pady=10)
            
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
        except Queue.Empty:
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