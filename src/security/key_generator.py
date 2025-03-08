from src.security.key_generator_legacy import generate_key, SECRET_KEY
import tkinter as tk
from tkinter import messagebox, ttk
import pyperclip  # 用于复制到剪贴板
import secrets
import string
import hashlib
import os
import sys
import json
from datetime import datetime, timedelta
from src.ui.styles.theme_manager import theme_manager

def copy_to_clipboard(text):
    pyperclip.copy(text)
    messagebox.showinfo("成功", "密钥已复制到剪贴板！")

def show_key_dialog(key):
    # 创建主窗口
    window = tk.Tk()
    window.title("密钥生成器")
    window.geometry("500x300")
    
    # 设置窗口在屏幕中央
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - 500) // 2
    y = (screen_height - 300) // 2
    window.geometry(f"500x300+{x}+{y}")
    
    # 应用主题
    theme_manager.apply_theme(window)
    
    # 创建主框架
    main_frame = tk.Frame(window, bg=theme_manager.get_color('background'))
    main_frame.pack(fill=tk.BOTH, expand=True, padx=theme_manager.get_padding('frame'), pady=theme_manager.get_padding('frame'))
    
    # 创建标题
    title = ttk.Label(main_frame,
                     text="密钥生成器",
                     style='Subtitle.TLabel')
    title.pack(pady=(0, 30))
    
    # 创建密钥显示框架
    key_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
    key_frame.pack(fill=tk.X, pady=10)
    
    # 显示密钥的文本框
    key_entry = ttk.Entry(key_frame, width=40, font=theme_manager.get_font('input'))
    key_entry.insert(0, key)
    key_entry.config(state='readonly')
    key_entry.pack(pady=10)
    
    # 创建按钮框架
    button_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
    button_frame.pack(pady=20)
    
    # 复制按钮
    copy_button = ttk.Button(button_frame, 
                           text="复制密钥", 
                           style='Success.TButton',
                           command=lambda: copy_to_clipboard(key))
    copy_button.pack(side=tk.LEFT, padx=10)
    
    # 关闭按钮
    close_button = ttk.Button(button_frame, 
                            text="关闭", 
                            style='Secondary.TButton',
                            command=window.destroy)
    close_button.pack(side=tk.LEFT, padx=10)
    
    # 运行窗口
    window.mainloop()

def generate_key():
    """生成一个随机密钥"""
    # 生成一个随机字符串
    alphabet = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    # 使用 SHA-256 哈希算法生成密钥
    key = hashlib.sha256(random_string.encode()).hexdigest()
    
    return key

if __name__ == "__main__":
    # 生成密钥并显示
    key = generate_key()
    show_key_dialog(key)