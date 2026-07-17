from src.security.key_generator_legacy import generate_key, SECRET_KEY
import ttkbootstrap as ttk
from tkinter import messagebox
import pyperclip  # 用于复制到剪贴板

def copy_to_clipboard(text):
    pyperclip.copy(text)
    messagebox.showinfo("成功", "密钥已复制到剪贴板！")

def show_key_dialog(key):
    # 创建主窗口
    window = ttk.Window(themename="litera")  # 使用 litera 主题
    window.title("密钥生成器")
    window.geometry("500x325")
    
    # 设置窗口在屏幕中央
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - 500) // 2
    y = (screen_height - 325) // 2
    window.geometry(f"500x325+{x}+{y}")
    
    # 创建主框架
    main_frame = ttk.Frame(window)
    main_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # 创建标题
    title = ttk.Label(main_frame,
                     text="密钥生成器",
                     font=('Microsoft YaHei UI', 18, 'bold'),
                     bootstyle="primary")
    title.pack(pady=(0, 30))
    
    # 创建密钥显示框架
    key_frame = ttk.Frame(main_frame)
    key_frame.pack(fill='x', pady=10)
    
    # 显示密钥的文本框
    key_entry = ttk.Entry(key_frame, 
                         width=40,
                         font=('Microsoft YaHei UI', 10))
    key_entry.insert(0, key)
    key_entry.config(state='readonly')
    key_entry.pack(pady=10)
    
    # 创建按钮框架
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=20)
    
    # 复制按钮
    copy_button = ttk.Button(button_frame, 
                           text="复制密钥",
                           bootstyle="success",
                           command=lambda: copy_to_clipboard(key))
    copy_button.pack(side='left', padx=10)
    
    # 关闭按钮
    close_button = ttk.Button(button_frame, 
                            text="关闭",
                            bootstyle="secondary",
                            command=window.destroy)
    close_button.pack(side='left', padx=10)
    
    # 运行窗口
    window.mainloop()

if __name__ == "__main__":
    # 使用legacy版本生成密钥并显示
    key = generate_key(SECRET_KEY)
    show_key_dialog(key)