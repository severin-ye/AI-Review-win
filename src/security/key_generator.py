from w6_1_key_generator import generate_key, SECRET_KEY
import tkinter as tk
from tkinter import messagebox, ttk
import pyperclip  # 用于复制到剪贴板

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
    
    # 定义颜色主题
    colors = {
        'primary': '#2196F3',    # 主色调 - 蓝色
        'secondary': '#FFC107',  # 次要色调 - 琥珀色
        'background': '#F5F5F5', # 背景色 - 浅灰
        'text': '#333333',       # 文本色 - 深灰
        'button': '#1976D2',     # 按钮色 - 深蓝
        'button_hover': '#1565C0', # 按钮悬停色
        'border': '#E0E0E0'      # 边框色 - 灰色
    }
    
    # 设置窗口背景色
    window.configure(bg=colors['background'])
    
    # 创建主框架
    main_frame = tk.Frame(window, bg=colors['background'])
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # 创建标题
    title = ttk.Label(main_frame,
                     text="密钥生成器",
                     font=('Microsoft YaHei UI', 18, 'bold'),
                     background=colors['background'],
                     foreground=colors['primary'])
    title.pack(pady=(0, 30))
    
    # 创建密钥显示框架
    key_frame = tk.Frame(main_frame, bg=colors['background'])
    key_frame.pack(fill=tk.X, pady=10)
    
    # 显示密钥的文本框
    key_entry = ttk.Entry(key_frame, width=40, font=('Microsoft YaHei UI', 10))
    key_entry.insert(0, key)
    key_entry.config(state='readonly')
    key_entry.pack(pady=10)
    
    # 配置按钮样式
    style = ttk.Style()
    style.configure('Main.TButton',
                   font=('Microsoft YaHei UI', 10),
                   padding=(20, 10))
    
    # 复制按钮
    copy_button = ttk.Button(main_frame,
                           text="复制密钥",
                           style='Main.TButton',
                           command=lambda: copy_to_clipboard(key))
    copy_button.pack(pady=20)
    
    # 设置窗口置顶
    window.lift()
    window.attributes('-topmost', True)
    
    window.mainloop()

if __name__ == "__main__":
    generated_key = generate_key(SECRET_KEY)
    show_key_dialog(generated_key)