import tkinter as tk
from tkinter import ttk
import sys
import os

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

# 导入主题管理器
try:
    from src.utils.theme_manager import theme_manager
except ImportError:
    print("无法导入主题管理器，请确保项目结构正确")
    sys.exit(1)

class ButtonPreview:
    def __init__(self, root):
        self.root = root
        self.root.title("按钮样式预览")
        self.root.geometry("800x600")
        
        # 应用主题
        theme_manager.apply_theme(self.root)
        
        # 创建主框架
        main_frame = tk.Frame(self.root, bg=theme_manager.get_color('background'))
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建标题
        title = ttk.Label(main_frame,
                         text="按钮样式预览",
                         style='Title.TLabel')
        title.pack(pady=20)
        
        # 创建说明
        description = ttk.Label(main_frame,
                              text="以下是所有可用的按钮样式，可用于整个应用程序",
                              style='TLabel')
        description.pack(pady=10)
        
        # 创建按钮样式预览区域
        preview_frame = tk.Frame(main_frame, bg=theme_manager.get_color('background'))
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # 定义所有按钮样式
        button_styles = [
            ('TButton', '默认按钮', '默认按钮样式，蓝色边框和文字'),
            ('Main.TButton', '主按钮', '用于主要操作，蓝色边框和文字'),
            ('Secondary.TButton', '次要按钮', '用于次要操作，黄色边框和文字'),
            ('Success.TButton', '成功按钮', '用于确认、保存等操作，绿色边框和文字'),
            ('Danger.TButton', '危险按钮', '用于删除、退出等操作，红色边框和文字'),
            ('Small.TButton', '小型按钮', '用于空间有限的区域，蓝色边框和文字，尺寸更小'),
            ('Custom.TButton', '自定义按钮', '与主按钮相同，为了兼容性'),
            ('Action.TButton', '操作按钮', '用于特定操作，蓝色边框和文字，内边距略有不同')
        ]
        
        # 创建每种样式的按钮
        for i, (style, name, desc) in enumerate(button_styles):
            # 创建样式容器
            style_frame = tk.Frame(preview_frame, bg=theme_manager.get_color('background'))
            style_frame.pack(fill=tk.X, pady=10)
            
            # 创建样式名称标签
            style_label = ttk.Label(style_frame,
                                  text=f"{name} ({style})",
                                  style='TLabel',
                                  font=('Microsoft YaHei UI', 12, 'bold'))
            style_label.pack(anchor='w')
            
            # 创建样式描述标签
            desc_label = ttk.Label(style_frame,
                                 text=desc,
                                 style='TLabel')
            desc_label.pack(anchor='w', pady=5)
            
            # 创建按钮示例
            button_frame = tk.Frame(style_frame, bg=theme_manager.get_color('background'))
            button_frame.pack(fill=tk.X, pady=10)
            
            # 正常状态按钮
            normal_button = ttk.Button(button_frame,
                                     text="正常状态",
                                     style=style)
            normal_button.pack(side=tk.LEFT, padx=10)
            
            # 禁用状态按钮
            disabled_button = ttk.Button(button_frame,
                                       text="禁用状态",
                                       style=style,
                                       state='disabled')
            disabled_button.pack(side=tk.LEFT, padx=10)
            
            # 添加分隔线
            if i < len(button_styles) - 1:
                separator = ttk.Separator(preview_frame, orient='horizontal')
                separator.pack(fill=tk.X, pady=10)
        
        # 创建关闭按钮
        close_button = ttk.Button(main_frame,
                                text="关闭预览",
                                style='Secondary.TButton',
                                command=self.root.destroy)
        close_button.pack(pady=20)

if __name__ == "__main__":
    root = tk.Tk()
    app = ButtonPreview(root)
    root.mainloop()