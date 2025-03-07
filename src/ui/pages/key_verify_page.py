import tkinter as tk
from tkinter import ttk, messagebox
import os
from src.styles.theme_manager import theme_manager
from src.security.key_generator_legacy import SECRET_KEY
from src.security import key_verifier

class KeyVerifyPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg=theme_manager.get_color('background'))
        self.controller = controller  # 保存controller引用
        
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
                                command=self.verify_key)
        verify_button.pack(pady=20)
    
    def verify_key(self):
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
                    from src.ui.pages.start_page import StartPage  # 动态导入
                    self.controller.show_frame(StartPage)
                else:
                    messagebox.showerror("错误", "无效的密钥！")
            except Exception as e:
                messagebox.showerror("错误", f"验证过程出错：{str(e)}")
                
        except Exception as e:
            messagebox.showerror("错误", f"验证过程出错：{str(e)}") 