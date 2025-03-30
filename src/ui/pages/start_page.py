import ttkbootstrap as ttk
from tkinter import messagebox, filedialog, scrolledtext, LEFT, RIGHT, TOP, BOTH, X, Y, W
import os
import sys
import shutil
import threading
import tkinter as tk
from src.ui.styles.theme_manager import theme_manager
from src.utils import cleanup_utils
from config.managers import config_manager
from config.constants import LABEL_NAMES, MODULE_LIST, LABEL_WIDTH, ENTRY_WIDTH, PROMPT_TEXT_HEIGHT, PROMPT_TEXT_WIDTH
from config import path_manager

class StartPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller  # 保存controller引用
        self.master = parent  # 保存父级引用
        
        # 使用全局配置管理器实例
        self.config_manager = config_manager
        
        # 创建标题
        title = theme_manager.create_label(
            self, 
            text="AI审校助手",
            is_title=True,
            bootstyle="primary"
        )
        title.pack(pady=50)
        
        # 创建主按钮容器
        main_button_frame = ttk.Frame(self)
        main_button_frame.pack(expand=True)
        
        # 创建左侧按钮容器
        left_button_frame = ttk.Frame(main_button_frame)
        left_button_frame.pack(side=LEFT, padx=40)
        
        # 创建右侧按钮容器
        right_button_frame = ttk.Frame(main_button_frame)
        right_button_frame.pack(side=LEFT, padx=40)
        
        # 左侧按钮（文件操作）
        left_buttons = [
            ("上传文件", self.upload_file, 'primary'),
            ("上传医学参考", self.upload_medical_docs, 'info'),
            ("清理文件", self.clear_files, 'info'),
        ]
        
        # 右侧按钮（程序操作）
        right_buttons = [
            ("开始处理", self.show_process_page, 'success'),
            ("配置设置", self.show_config_page, 'primary'),
            ("退出程序", self.quit_app, 'danger')
        ]
        
        # 创建左侧按钮
        for text, command, bootstyle in left_buttons:
            btn = theme_manager.create_button(
                left_button_frame,
                text=text,
                command=command,
                bootstyle=bootstyle
            )
        
        # 创建右侧按钮
        for text, command, bootstyle in right_buttons:
            btn = theme_manager.create_button(
                right_button_frame,
                text=text,
                command=command,
                bootstyle=bootstyle
            )
        
        # 创建配置页面（初始隐藏）
        self.config_frame = ttk.Frame(self)
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
            
        # 使用路径管理器获取原文件目录
        target_dir = path_manager.original_files_dir
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
    
    def upload_medical_docs(self):
        """上传医学参考文档功能"""
        files = filedialog.askopenfilenames(
            title="选择医学参考文档",
            filetypes=[
                ("医学文档", "*.pdf;*.txt;*.csv;*.docx;*.doc"),
                ("PDF文档", "*.pdf"),
                ("文本文件", "*.txt"),
                ("CSV数据", "*.csv"),
                ("Word文档", "*.docx;*.doc"),
                ("所有文件", "*.*")
            ]
        )
        
        if not files:
            return
            
        # 使用路径管理器获取医学参考文档上传目录
        target_dir = path_manager.get_medical_docs_upload_dir()
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
            msg = f"成功上传 {success_count} 个医学参考文档！\n\n文档将在下次启动程序时自动索引。"
            messagebox.showinfo("上传成功", msg)
    
    def clear_files(self):
        """运行清理文件脚本"""
        try:
            # 使用cleanup_utils模块的功能来清理文件
            directories_to_clean = [
                path_manager.original_files_dir,
                path_manager.reviewed_files_dir,
                path_manager.temp_files_dir
            ]
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
    
    def create_config_page(self):
        """创建配置页面"""
        # 创建主框架
        main_frame = ttk.Frame(self.config_frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题
        title = theme_manager.create_label(
            main_frame,
            text="配置设置",
            is_title=True,
            bootstyle="primary"
        )
        title.pack(pady=20)
        
        # 使用ConfigManager的create_config_ui方法创建配置界面
        config_ui_frame = self.config_manager.create_config_ui(main_frame)
        config_ui_frame.pack(fill="both", expand=True, pady=10)
        
        # 创建保存和返回按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        save_button = theme_manager.create_button(
            button_frame,
            text="保存配置",
            command=self.save_config,
            bootstyle="success"
        )
        save_button.pack(side=ttk.LEFT, padx=10)
        
        back_button = theme_manager.create_button(
            button_frame,
            text="返回主页",
            command=self.show_main_page,
            bootstyle="secondary"
        )
        back_button.pack(side=ttk.LEFT, padx=10)
    
    def save_config(self):
        """保存配置"""
        if self.config_manager.save_ui_config():
            messagebox.showinfo("成功", "配置已保存！")
            self.show_main_page()
    
    def show_main_page(self):
        """返回主页面"""
        # 清空并隐藏配置页面
        self.config_frame.pack_forget()
        
        # 显示主页面组件
        for widget in self.winfo_children():
            if widget != self.config_frame:
                widget.pack()
        
        # 重新排列主要组件
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Label) and widget.cget("text") == "AI审校助手":
                widget.pack(pady=50)
            elif isinstance(widget, ttk.Frame) and widget != self.config_frame:
                widget.pack(expand=True)
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askyesno("确认退出", "确定要退出程序吗？"):
            self.controller.destroy() 