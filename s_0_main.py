import tkinter as tk
from tkinter import messagebox, ttk
import os
import sys
import subprocess
from w6_1_key_generator import SECRET_KEY  # 导入密钥

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
        for F in (KeyVerifyPage, StartPage, ConfigPage, ProcessPage):
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
                                command=lambda: controller.show_frame(ConfigPage),
                                width=20, height=2)
        config_button.pack(pady=10)
        
        exit_button = tk.Button(self, text="退出程序",
                              command=self.quit_app,
                              width=20, height=2)
        exit_button.pack(pady=10)
    
    def clear_files(self):
        """运行清理文件脚本"""
        try:
            result = subprocess.run([sys.executable, "s_3_clear_out.py"], 
                                 capture_output=True, 
                                 text=True, 
                                 encoding='gbk')
            output = result.stdout
            if output:
                messagebox.showinfo("清理完成", output.strip())
            else:
                messagebox.showinfo("清理完成", "文件清理已完成")
        except UnicodeDecodeError:
            messagebox.showinfo("清理完成", "文件清理已完成")
        except Exception as e:
            messagebox.showerror("错误", f"清理文件时出错：{str(e)}")
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.quit()

class ConfigPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        
        title = tk.Label(self, text="配置设置", font=("Helvetica", 24))
        title.pack(pady=50)
        
        config_button = tk.Button(self, text="打开配置界面",
                                command=self.open_config,
                                width=20, height=2)
        config_button.pack(pady=10)
        
        back_button = tk.Button(self, text="返回主页",
                              command=lambda: controller.show_frame(StartPage),
                              width=20, height=2)
        back_button.pack(pady=10)
    
    def open_config(self):
        """运行配置脚本"""
        try:
            subprocess.run([sys.executable, "s_4_config_use.py"])
        except Exception as e:
            messagebox.showerror("错误", f"打开配置界面时出错：{str(e)}")

class ProcessPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        
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
    
    def auto_process(self):
        """运行自动处理脚本"""
        try:
            subprocess.run([sys.executable, "s_1_auto_ai.py"])
        except Exception as e:
            messagebox.showerror("错误", f"自动处理时出错：{str(e)}")
    
    def manual_process(self):
        """运行人工审校脚本"""
        try:
            subprocess.run([sys.executable, "s_2_select_replace.py"])
        except Exception as e:
            messagebox.showerror("错误", f"人工审校时出错：{str(e)}")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
