import ttkbootstrap as ttk
from tkinter import messagebox
import os
from src.ui.styles.theme_manager import theme_manager
from src.security.key_generator_legacy import SECRET_KEY
from src.security import key_verifier

class KeyVerifyPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller  # 保存controller引用
        
        # 创建标题
        title = theme_manager.create_label(
            self, 
            text="密钥验证",
            is_title=True,
            bootstyle="primary"
        )
        title.pack(pady=50)
        
        # 创建输入框容器
        entry_frame = ttk.Frame(self)
        entry_frame.pack(pady=20)
        
        # 创建输入框
        self.key_entry = theme_manager.create_entry(entry_frame)
        self.key_entry.pack(pady=10)
        
        # 创建验证按钮
        verify_button = theme_manager.create_button(
            self,
            text="验证",
            command=self.verify_key,
            bootstyle="success"
        )
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