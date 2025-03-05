import tkinter as tk
from tkinter import ttk
import os
import json

class ThemeManager:
    """
    主题管理器类，用于统一管理整个应用程序的样式和主题
    """
    
    # 默认主题配置
    DEFAULT_THEME = {
        'colors': {
            'primary': '#2196F3',      # 主色调 - 蓝色
            'secondary': '#FFC107',    # 次要色调 - 琥珀色
            'background': '#F5F5F5',   # 背景色 - 浅灰
            'text': '#333333',         # 文本色 - 深灰
            'button': '#1976D2',       # 按钮色 - 深蓝
            'button_hover': '#1565C0', # 按钮悬停色
            'border': '#E0E0E0',       # 边框色 - 灰色
            'success': '#4CAF50',      # 成功色 - 绿色
            'warning': '#FF9800',      # 警告色 - 橙色
            'error': '#F44336',        # 错误色 - 红色
            'info': '#2196F3'          # 信息色 - 蓝色
        },
        'fonts': {
            'default': ('Microsoft YaHei UI', 10),
            'title': ('Microsoft YaHei UI', 24, 'bold'),
            'subtitle': ('Microsoft YaHei UI', 18, 'bold'),
            'small': ('Microsoft YaHei UI', 9),
            'button': ('Microsoft YaHei UI', 10),
            'input': ('Microsoft YaHei UI', 10)
        },
        'padding': {
            'button': (20, 10),
            'frame': 20,
            'input': 5
        },
        'border_radius': 4,
        'animation_duration': 200
    }
    
    def __init__(self):
        """初始化主题管理器"""
        self.theme = self.DEFAULT_THEME.copy()
        self.load_theme()
    
    def load_theme(self):
        """从配置文件加载主题设置"""
        try:
            theme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     'config', 'theme.json')
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as f:
                    custom_theme = json.load(f)
                    # 递归更新主题配置
                    self._update_dict(self.theme, custom_theme)
        except Exception as e:
            print(f"加载主题配置失败: {str(e)}")
    
    def _update_dict(self, d, u):
        """递归更新字典"""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_dict(d[k], v)
            else:
                d[k] = v
    
    def save_theme(self):
        """保存主题设置到配置文件"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
            os.makedirs(config_dir, exist_ok=True)
            theme_path = os.path.join(config_dir, 'theme.json')
            with open(theme_path, 'w', encoding='utf-8') as f:
                json.dump(self.theme, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存主题配置失败: {str(e)}")
    
    def apply_theme(self, root):
        """应用主题到根窗口及其样式"""
        # 设置窗口背景色
        root.configure(bg=self.theme['colors']['background'])
        
        # 配置全局样式
        style = ttk.Style()
        
        # 应用按钮样式
        self.apply_button_styles(style)
        
        # 配置标题样式
        style.configure('Title.TLabel',
                       font=self.theme['fonts']['title'],
                       background=self.theme['colors']['background'],
                       foreground=self.theme['colors']['primary'])
        
        # 配置副标题样式
        style.configure('Subtitle.TLabel',
                       font=self.theme['fonts']['subtitle'],
                       background=self.theme['colors']['background'],
                       foreground=self.theme['colors']['primary'])
        
        # 配置普通标签样式
        style.configure('TLabel',
                       font=self.theme['fonts']['default'],
                       background=self.theme['colors']['background'],
                       foreground=self.theme['colors']['text'])
        
        # 配置输入框样式
        style.configure('TEntry',
                       font=self.theme['fonts']['input'])
        
        # 配置进度条样式
        style.configure('Horizontal.TProgressbar',
                       thickness=15)
        
        # 配置复选框样式
        style.configure('TCheckbutton',
                       font=self.theme['fonts']['default'],
                       background=self.theme['colors']['background'])
        
        # 配置单选按钮样式
        style.configure('TRadiobutton',
                       font=self.theme['fonts']['default'],
                       background=self.theme['colors']['background'])
        
        # 配置下拉菜单样式
        style.configure('TCombobox',
                       font=self.theme['fonts']['default'])
        
        # 配置框架样式
        style.configure('TFrame',
                       background=self.theme['colors']['background'])
        
        # 配置信息标签样式
        style.configure('Info.TLabel',
                       font=self.theme['fonts']['default'],
                       background=self.theme['colors']['background'],
                       foreground=self.theme['colors']['info'])
        
        # 配置警告标签样式
        style.configure('Warning.TLabel',
                       font=self.theme['fonts']['default'],
                       background=self.theme['colors']['background'],
                       foreground=self.theme['colors']['warning'])
        
        # 配置错误标签样式
        style.configure('Error.TLabel',
                       font=self.theme['fonts']['default'],
                       background=self.theme['colors']['background'],
                       foreground=self.theme['colors']['error'])
        
        # 配置成功标签样式
        style.configure('Success.TLabel',
                       font=self.theme['fonts']['default'],
                       background=self.theme['colors']['background'],
                       foreground=self.theme['colors']['success'])
    
    def apply_button_styles(self, style):
        """应用所有按钮样式 - 集中定义所有按钮样式，供其他模块调用"""
        # 配置按钮样式 - 美化版本
        style.configure('Main.TButton',
                       font=self.theme['fonts']['button'],
                       padding=self.theme['padding']['button'],
                       background='#FFFFFF',
                       foreground=self.theme['colors']['primary'],
                       relief=tk.RAISED,
                       borderwidth=1,
                       highlightthickness=1,
                       highlightbackground=self.theme['colors']['primary'],
                       highlightcolor=self.theme['colors']['primary'])
        
        # 配置按钮悬停和按下状态
        style.map('Main.TButton',
                 background=[('active', '#E3F2FD'),
                            ('pressed', '#E3F2FD')],
                 foreground=[('active', self.theme['colors']['button_hover']),
                            ('pressed', self.theme['colors']['button_hover'])],
                 relief=[('pressed', 'sunken')])
        
        # 配置次要按钮样式
        style.configure('Secondary.TButton',
                       font=self.theme['fonts']['button'],
                       padding=self.theme['padding']['button'],
                       background='#FFFFFF',
                       foreground=self.theme['colors']['secondary'],
                       relief=tk.RAISED,
                       borderwidth=1,
                       highlightthickness=1,
                       highlightbackground=self.theme['colors']['secondary'],
                       highlightcolor=self.theme['colors']['secondary'])
        
        # 配置次要按钮悬停和按下状态
        style.map('Secondary.TButton',
                 background=[('active', '#FFF8E1'),
                            ('pressed', '#FFF8E1')],
                 foreground=[('active', '#E6A800'),
                            ('pressed', '#E6A800')],
                 relief=[('pressed', 'sunken')])
        
        # 配置危险按钮样式（如删除、退出等）
        style.configure('Danger.TButton',
                       font=self.theme['fonts']['button'],
                       padding=self.theme['padding']['button'],
                       background='#FFFFFF',
                       foreground=self.theme['colors']['error'],
                       relief=tk.RAISED,
                       borderwidth=1,
                       highlightthickness=1,
                       highlightbackground=self.theme['colors']['error'],
                       highlightcolor=self.theme['colors']['error'])
        
        # 配置危险按钮悬停和按下状态
        style.map('Danger.TButton',
                 background=[('active', '#FFEBEE'),
                            ('pressed', '#FFEBEE')],
                 foreground=[('active', '#D32F2F'),
                            ('pressed', '#D32F2F')],
                 relief=[('pressed', 'sunken')])
        
        # 配置成功按钮样式（如确认、保存等）
        style.configure('Success.TButton',
                       font=self.theme['fonts']['button'],
                       padding=self.theme['padding']['button'],
                       background='#FFFFFF',
                       foreground=self.theme['colors']['success'],
                       relief=tk.RAISED,
                       borderwidth=1,
                       highlightthickness=1,
                       highlightbackground=self.theme['colors']['success'],
                       highlightcolor=self.theme['colors']['success'])
        
        # 配置成功按钮悬停和按下状态
        style.map('Success.TButton',
                 background=[('active', '#E8F5E9'),
                            ('pressed', '#E8F5E9')],
                 foreground=[('active', '#388E3C'),
                            ('pressed', '#388E3C')],
                 relief=[('pressed', 'sunken')])
        
        # 配置小型按钮样式
        style.configure('Small.TButton',
                       font=self.theme['fonts']['small'],
                       padding=(10, 5),
                       background='#FFFFFF',
                       foreground=self.theme['colors']['primary'],
                       relief=tk.RAISED,
                       borderwidth=1,
                       highlightthickness=1,
                       highlightbackground=self.theme['colors']['primary'],
                       highlightcolor=self.theme['colors']['primary'])
        
        # 配置小型按钮悬停和按下状态
        style.map('Small.TButton',
                 background=[('active', '#E3F2FD'),
                            ('pressed', '#E3F2FD')],
                 foreground=[('active', self.theme['colors']['button_hover']),
                            ('pressed', self.theme['colors']['button_hover'])],
                 relief=[('pressed', 'sunken')])
                 
        # 配置默认按钮样式 (TButton) - 与Main.TButton相同
        style.configure('TButton',
                       font=self.theme['fonts']['button'],
                       padding=self.theme['padding']['button'],
                       background='#FFFFFF',
                       foreground=self.theme['colors']['primary'],
                       relief=tk.RAISED,
                       borderwidth=1,
                       highlightthickness=1,
                       highlightbackground=self.theme['colors']['primary'],
                       highlightcolor=self.theme['colors']['primary'])
        
        # 配置默认按钮悬停和按下状态
        style.map('TButton',
                 background=[('active', '#E3F2FD'),
                            ('pressed', '#E3F2FD')],
                 foreground=[('active', self.theme['colors']['button_hover']),
                            ('pressed', self.theme['colors']['button_hover'])],
                 relief=[('pressed', 'sunken')])
        
        # 配置自定义按钮样式 (Custom.TButton) - 与Main.TButton相同，为了兼容性
        style.configure('Custom.TButton',
                       font=self.theme['fonts']['button'],
                       padding=self.theme['padding']['button'],
                       background='#FFFFFF',
                       foreground=self.theme['colors']['primary'],
                       relief=tk.RAISED,
                       borderwidth=1,
                       highlightthickness=1,
                       highlightbackground=self.theme['colors']['primary'],
                       highlightcolor=self.theme['colors']['primary'])
        
        # 配置自定义按钮悬停和按下状态
        style.map('Custom.TButton',
                 background=[('active', '#E3F2FD'),
                            ('pressed', '#E3F2FD')],
                 foreground=[('active', self.theme['colors']['button_hover']),
                            ('pressed', self.theme['colors']['button_hover'])],
                 relief=[('pressed', 'sunken')])
                 
        # 配置操作按钮样式 (Action.TButton) - 为了兼容性
        style.configure('Action.TButton',
                       font=self.theme['fonts']['button'],
                       padding=(15, 8),
                       background='#FFFFFF',
                       foreground=self.theme['colors']['primary'],
                       relief=tk.RAISED,
                       borderwidth=1,
                       highlightthickness=1,
                       highlightbackground=self.theme['colors']['primary'],
                       highlightcolor=self.theme['colors']['primary'])
        
        # 配置操作按钮悬停和按下状态
        style.map('Action.TButton',
                 background=[('active', '#E3F2FD'),
                            ('pressed', '#E3F2FD')],
                 foreground=[('active', self.theme['colors']['button_hover']),
                            ('pressed', self.theme['colors']['button_hover'])],
                 relief=[('pressed', 'sunken')])
    
    def get_color(self, color_name):
        """获取指定的颜色"""
        return self.theme['colors'].get(color_name, self.theme['colors']['primary'])
    
    def get_font(self, font_name):
        """获取指定的字体"""
        return self.theme['fonts'].get(font_name, self.theme['fonts']['default'])
    
    def get_padding(self, padding_name):
        """获取指定的内边距"""
        return self.theme['padding'].get(padding_name, self.theme['padding']['frame'])

# 创建全局主题管理器实例
theme_manager = ThemeManager() 