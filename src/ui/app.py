import tkinter as tk
from src.styles.theme_manager import theme_manager
from src.ui.pages.key_verify_page import KeyVerifyPage
from src.ui.pages.start_page import StartPage
from src.ui.pages.process_page import ProcessPage

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和大小
        self.title("AI审校助手")
        self.geometry("800x600")
        
        # 设置全屏显示
        self.state('zoomed')
        
        # 应用主题
        theme_manager.apply_theme(self)
        
        # 存储主题颜色和字体，方便访问
        self.colors = theme_manager.theme['colors']
        self.default_font = theme_manager.get_font('default')
        self.title_font = theme_manager.get_font('title')
        
        # 创建一个容器来存放所有页面
        container = tk.Frame(self, bg=theme_manager.get_color('background'))
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

if __name__ == "__main__":
    app = MainApp()
    app.mainloop() 