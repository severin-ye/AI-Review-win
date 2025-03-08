import ttkbootstrap as ttk
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
            'button': (20, 10),  # 按钮内边距：水平20像素，垂直10像素
            'frame': 20,         # 框架内边距：四周均为20像素
            'input': 5          # 输入框内边距：四周均为5像素
        },
        'border_radius': 4,
        'animation_duration': 200
    }
    
    def __init__(self):
        """初始化主题管理器"""
        self.theme = self.DEFAULT_THEME.copy()
        self.load_theme()
    
    def load_theme(self):
        """从配置文件加载主题"""
        try:
            theme_file = os.path.join(os.path.dirname(__file__), 'theme.json')
            if os.path.exists(theme_file):
                with open(theme_file, 'r', encoding='utf-8') as f:
                    custom_theme = json.load(f)
                    # 递归更新主题配置
                    self._update_dict(self.theme, custom_theme)
        except Exception as e:
            print(f"加载主题配置失败：{str(e)}")
    
    def _update_dict(self, d, u):
        """递归更新字典"""
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._update_dict(d.get(k, {}), v)
            else:
                d[k] = v
        return d
    
    def apply_theme(self, root):
        """应用主题到根窗口及其样式"""
        # 在 ttkbootstrap 中，大部分样式已经由主题处理
        # 我们只需要设置一些自定义的样式
        pass
    
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