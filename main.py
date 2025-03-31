#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI审校助手入口文件
"""

import os
import sys
import logging
import traceback
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import path_manager
from src.utils.cleanup_utils import cleanup_all_directories

def setup_logging():
    """配置日志系统"""
    # 获取日志文件路径
    log_file = path_manager.get_log_file()
    
    # 配置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_environment():
    """检查运行环境"""
    try:
        # 检查Python版本
        if sys.version_info < (3, 7):
            raise RuntimeError("Python版本必须是3.7或更高")
        
        # 检查必要目录（现在由 PathManager 自动创建）
        path_manager._ensure_directories()
        
        return True
    except Exception as e:
        logging.error(f"环境检查失败：{str(e)}")
        return False

def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理器"""
    # 忽略KeyboardInterrupt异常
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # 记录异常信息
    logging.error("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # 如果GUI已经初始化，显示错误对话框
    try:
        if tk._default_root:
            error_msg = f"程序发生错误：\n{str(exc_value)}\n\n是否查看详细信息？"
            if messagebox.askyesno("错误", error_msg):
                detailed_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                messagebox.showerror("错误详情", detailed_msg)
    except:
        pass

def main():
    """主函数"""
    try:
        # 配置日志系统
        setup_logging()
        
        # 设置全局异常处理器
        sys.excepthook = handle_exception
        
        # 记录启动信息
        logging.info("正在启动AI审校助手...")
        
        # 检查运行环境
        if not check_environment():
            messagebox.showerror("错误", "环境检查失败，请查看日志文件了解详情")
            return
        
        # 清理工作目录（仅在main.py运行时执行）
        cleanup_result = cleanup_all_directories()
        logging.info(cleanup_result)
        
        # 导入主应用程序
        from src.ui import MainApp
        
        # 创建并运行应用程序
        app = MainApp()
        
        # 配置窗口图标（如果存在）
        icon_path = os.path.join(project_root, 'material', 'icon.ico')
        if os.path.exists(icon_path):
            app.iconbitmap(icon_path)
        
        # 运行主循环
        app.mainloop()
        
    except Exception as e:
        logging.error(f"程序运行出错：{str(e)}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败：{str(e)}\n\n请查看日志文件了解详情")
        raise
    finally:
        logging.info("程序已退出")

if __name__ == "__main__":
    main() 