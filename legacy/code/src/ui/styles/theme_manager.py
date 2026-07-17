import ttkbootstrap as ttk  # 导入ttkbootstrap库用于创建美观的GUI界面
import os  # 导入os模块用于处理文件路径
import json  # 导入json模块用于读写主题配置文件

class ThemeManager:
    """
    主题管理器类，用于统一管理整个应用程序的样式和主题。
    提供了统一的主题配置、组件创建和样式管理功能。
    """
    
    # 默认主题配置，定义了应用程序的默认样式
    DEFAULT_THEME = {
        'colors': {
            'primary': '#2196F3',      # 主色调 - 蓝色，用于主要元素
            'secondary': '#FFC107',    # 次要色调 - 琥珀色，用于次要元素
            'background': '#F5F5F5',   # 背景色 - 浅灰，用于窗口和面板背景
            'text': '#333333',         # 文本色 - 深灰，用于普通文本
            'button': '#1976D2',       # 按钮色 - 深蓝，用于按钮背景
            'button_hover': '#1565C0', # 按钮悬停色，鼠标悬停时的颜色
            'border': '#E0E0E0',       # 边框色 - 灰色，用于分隔线和边框
            'success': '#4CAF50',      # 成功色 - 绿色，用于表示成功状态
            'warning': '#FF9800',      # 警告色 - 橙色，用于表示警告状态
            'error': '#F44336',        # 错误色 - 红色，用于表示错误状态
            'info': '#2196F3'          # 信息色 - 蓝色，用于表示信息状态
        },
        'fonts': {
            'default': ('Microsoft YaHei UI', 10),        # 默认字体，用于普通文本
            'title': ('Microsoft YaHei UI', 24, 'bold'),  # 标题字体，用于主标题
            'subtitle': ('Microsoft YaHei UI', 18, 'bold'),# 副标题字体
            'small': ('Microsoft YaHei UI', 9),           # 小字体，用于注释文本
            'button': ('Microsoft YaHei UI', 12),         # 按钮字体
            'input': ('Microsoft YaHei UI', 10)           # 输入框字体
        },
        'components': {
            'button': {
                'width': 20,           # 按钮宽度（字符数）
                'padding': (30, 25),   # 按钮内边距（水平，垂直）像素值
                'font': 'button',      # 使用的字体类型，对应fonts中的键
                'radius': 20           # 按钮圆角半径，像素值
            },
            'entry': {
                'width': 40,           # 输入框宽度（字符数）
                'padding': 5,          # 输入框内边距，像素值
                'font': 'input'        # 使用的字体类型，对应fonts中的键
            },
            'label': {
                'font': 'default',     # 默认标签字体，对应fonts中的键
                'title_font': 'title', # 标题标签字体，对应fonts中的键
                'padding': (5, 5)      # 标签内边距（水平，垂直）像素值
            }
        },
        'padding': {
            'button': (60, 30),    # 按钮外边距（水平，垂直）像素值，水平间距增加到两倍
            'frame': 20,           # 框架内边距，像素值
            'input': 5             # 输入框外边距，像素值
        },
        'border_radius': 10,          # 边框圆角半径，像素值
        'animation_duration': 200      # 动画持续时间，毫秒
    }
    
    def __init__(self):
        """
        初始化主题管理器
        - 创建主题配置的深拷贝
        - 加载自定义主题配置
        - 初始化样式对象为None
        """
        self.theme = self.DEFAULT_THEME.copy()  # 创建默认主题的副本
        self.load_theme()  # 加载自定义主题配置
        self.style = None  # 初始化样式对象为None，延迟创建
    
    def create_button(self, parent, text, command=None, bootstyle="primary"):
        """
        创建统一样式的按钮
        Args:
            parent: 父级窗口部件
            text: 按钮文本
            command: 点击按钮时执行的函数
            bootstyle: 按钮样式，可选值：primary, secondary, success等
        Returns:
            ttk.Button: 创建的按钮部件
        """
        if self.style is None:
            self.style = ttk.Style()
            # 为每种 bootstyle 创建自定义样式
            for style_name in ["primary", "secondary", "success", "danger", "warning", "info"]:
                style_id = f"Custom.{style_name}.TButton"
                self.style.configure(
                    style_id,
                    font=self.get_font('button'),
                    padding=self.theme['components']['button']['padding']
                )
                # 添加圆角效果
                radius = self.theme['components']['button']['radius']
                self.style.layout(style_id, [
                    ('Button.border', {
                        'sticky': 'nswe',
                        'border': f'{radius}',
                        'children': [
                            ('Button.padding', {
                                'sticky': 'nswe',
                                'children': [
                                    ('Button.label', {'sticky': 'nswe'})
                                ]
                            })
                        ]
                    })
                ])
        
        button_style = self.theme['components']['button']
        btn = ttk.Button(
            parent,
            text=text,
            command=command,
            bootstyle=bootstyle,
            style=f"Custom.{bootstyle}.TButton",
            width=button_style['width']
        )
        
        # 应用默认的按钮间距
        btn.pack(pady=self.get_padding('button')[1])
        return btn

    def create_entry(self, parent, width=None, **kwargs):
        """
        创建统一样式的输入框
        Args:
            parent: 父级窗口部件
            width: 输入框宽度，如果为None则使用默认宽度
            **kwargs: 其他传递给ttk.Entry的参数
        Returns:
            ttk.Entry: 创建的输入框部件
        """
        entry_style = self.theme['components']['entry']
        return ttk.Entry(
            parent,
            width=width or entry_style['width'],
            font=self.get_font(entry_style['font']),
            **kwargs
        )

    def create_label(self, parent, text, is_title=False, bootstyle=None, **kwargs):
        """
        创建统一样式的标签
        Args:
            parent: 父级窗口部件
            text: 标签文本
            is_title: 是否为标题样式
            bootstyle: 标签样式
            **kwargs: 其他传递给ttk.Label的参数
        Returns:
            ttk.Label: 创建的标签部件
        """
        label_style = self.theme['components']['label']
        font_type = label_style['title_font'] if is_title else label_style['font']
        return ttk.Label(
            parent,
            text=text,
            font=self.get_font(font_type),
            bootstyle=bootstyle,
            padding=label_style['padding'],
            **kwargs
        )

    def load_theme(self):
        """
        从配置文件加载自定义主题
        尝试读取theme.json文件并更新当前主题配置
        如果加载失败则保持默认主题
        """
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
        """
        递归更新字典
        Args:
            d: 目标字典
            u: 更新源字典
        Returns:
            dict: 更新后的字典
        """
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._update_dict(d.get(k, {}), v)
            else:
                d[k] = v
        return d
    
    def apply_theme(self, root):
        """
        应用主题到根窗口及其样式
        Args:
            root: 根窗口对象
        注：在ttkbootstrap中，大部分样式已经由主题处理
        """
        pass
    
    def get_color(self, color_name):
        """
        获取指定的颜色值
        Args:
            color_name: 颜色名称
        Returns:
            str: 颜色的十六进制值
        """
        return self.theme['colors'].get(color_name, self.theme['colors']['primary'])
    
    def get_font(self, font_name):
        """
        获取指定的字体配置
        Args:
            font_name: 字体名称
        Returns:
            tuple: 字体配置元组(字体名, 大小, 样式)
        """
        return self.theme['fonts'].get(font_name, self.theme['fonts']['default'])
    
    def get_padding(self, padding_name):
        """
        获取指定的内边距配置
        Args:
            padding_name: 内边距名称
        Returns:
            int或tuple: 内边距值
        """
        return self.theme['padding'].get(padding_name, self.theme['padding']['frame'])

    def get_component_style(self, component_name):
        """
        获取指定组件的样式配置
        Args:
            component_name: 组件名称
        Returns:
            dict: 组件的样式配置字典
        """
        return self.theme['components'].get(component_name, {})

# 创建全局主题管理器实例，供整个应用程序使用
theme_manager = ThemeManager() 