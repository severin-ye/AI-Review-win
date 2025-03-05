import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import shutil
import sys
import subprocess
import winreg
import json
import traceback
import logging
from pathlib import Path
from datetime import datetime
import time
import threading
import tempfile
import zipfile
import requests
import io
import re
import platform
import ctypes
from PIL import Image, ImageDraw

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 导入主题管理器
try:
    from src.styles.theme_manager import theme_manager
except ImportError:
    # 如果无法导入，创建一个简化版的主题管理器
    class SimpleThemeManager:
        def __init__(self):
            self.theme = {
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
                    'title': ('Microsoft YaHei UI', 16, 'bold'),
                    'subtitle': ('Microsoft YaHei UI', 14, 'bold'),
                    'small': ('Microsoft YaHei UI', 9),
                    'button': ('Microsoft YaHei UI', 10),
                    'input': ('Microsoft YaHei UI', 10)
                },
                'padding': {
                    'button': (20, 10),
                    'frame': 20,
                    'input': 5
                }
            }
        
        def get_color(self, color_name):
            return self.theme['colors'].get(color_name, self.theme['colors']['primary'])
        
        def get_font(self, font_name):
            return self.theme['fonts'].get(font_name, self.theme['fonts']['default'])
        
        def get_padding(self, padding_name):
            return self.theme['padding'].get(padding_name, self.theme['padding']['frame'])
        
        def apply_theme(self, root):
            # 设置窗口背景色
            root.configure(bg=self.get_color('background'))
            
            # 配置全局样式
            style = ttk.Style()
            
            # 尝试导入主题管理器
            try:
                # 添加项目根目录到系统路径
                import sys
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                
                # 导入主题管理器
                from src.styles.theme_manager import ThemeManager
                
                # 创建临时主题管理器实例并应用按钮样式
                temp_theme_manager = ThemeManager()
                temp_theme_manager.apply_button_styles(style)
                
                print("成功使用主题管理器应用按钮样式")
            except ImportError:
                print("无法导入主题管理器，使用本地按钮样式定义")
                # 如果无法导入主题管理器，则使用本地定义的按钮样式
                self._apply_local_button_styles(style)
            
            # 配置标题样式
            style.configure('Title.TLabel',
                           font=self.get_font('title'),
                           background=self.get_color('background'),
                           foreground=self.get_color('primary'))
            
            # 配置信息标签样式
            style.configure('Info.TLabel',
                           font=self.get_font('default'),
                           background=self.get_color('background'),
                           foreground=self.get_color('text'))
            
            # 配置进度条样式
            style.configure('Horizontal.TProgressbar',
                           thickness=15)
        
        def _apply_local_button_styles(self, style):
            """本地按钮样式定义，仅在无法导入主题管理器时使用"""
            # 配置按钮样式 - 美化版本
            style.configure('TButton',
                           font=self.get_font('button'),
                           padding=self.get_padding('button'),
                           background='#FFFFFF',
                           foreground=self.get_color('button'),
                           relief=tk.RAISED,
                           borderwidth=1,
                           highlightthickness=1,
                           highlightbackground=self.get_color('primary'),
                           highlightcolor=self.get_color('primary'))
            
            # 配置按钮悬停和按下状态
            style.map('TButton',
                     background=[('active', '#E3F2FD'),
                                ('pressed', '#E3F2FD')],
                     foreground=[('active', self.get_color('button_hover')),
                                ('pressed', self.get_color('button_hover'))],
                     relief=[('pressed', 'sunken')])
            
            # 配置主按钮样式
            style.configure('Main.TButton',
                           font=self.get_font('button'),
                           padding=self.get_padding('button'),
                           background='#FFFFFF',
                           foreground=self.get_color('button'),
                           relief=tk.RAISED,
                           borderwidth=1,
                           highlightthickness=1,
                           highlightbackground=self.get_color('primary'),
                           highlightcolor=self.get_color('primary'))
            
            # 配置主按钮悬停和按下状态
            style.map('Main.TButton',
                     background=[('active', '#E3F2FD'),
                                ('pressed', '#E3F2FD')],
                     foreground=[('active', self.get_color('button_hover')),
                                ('pressed', self.get_color('button_hover'))],
                     relief=[('pressed', 'sunken')])
            
            # 配置次要按钮样式
            style.configure('Secondary.TButton',
                           font=self.get_font('button'),
                           padding=self.get_padding('button'),
                           background='#FFFFFF',
                           foreground=self.get_color('secondary'),
                           relief=tk.RAISED,
                           borderwidth=1,
                           highlightthickness=1,
                           highlightbackground=self.get_color('secondary'),
                           highlightcolor=self.get_color('secondary'))
            
            # 配置次要按钮悬停和按下状态
            style.map('Secondary.TButton',
                     background=[('active', '#FFF8E1'),
                                ('pressed', '#FFF8E1')],
                     foreground=[('active', '#E6A800'),
                                ('pressed', '#E6A800')],
                     relief=[('pressed', 'sunken')])
            
            # 配置危险按钮样式
            style.configure('Danger.TButton',
                           font=self.get_font('button'),
                           padding=self.get_padding('button'),
                           background='#FFFFFF',
                           foreground=self.get_color('error'),
                           relief=tk.RAISED,
                           borderwidth=1,
                           highlightthickness=1,
                           highlightbackground=self.get_color('error'),
                           highlightcolor=self.get_color('error'))
            
            # 配置危险按钮悬停和按下状态
            style.map('Danger.TButton',
                     background=[('active', '#FFEBEE'),
                                ('pressed', '#FFEBEE')],
                     foreground=[('active', '#D32F2F'),
                                ('pressed', '#D32F2F')],
                     relief=[('pressed', 'sunken')])
            
            # 配置成功按钮样式
            style.configure('Success.TButton',
                           font=self.get_font('button'),
                           padding=self.get_padding('button'),
                           background='#FFFFFF',
                           foreground=self.get_color('success'),
                           relief=tk.RAISED,
                           borderwidth=1,
                           highlightthickness=1,
                           highlightbackground=self.get_color('success'),
                           highlightcolor=self.get_color('success'))
            
            # 配置成功按钮悬停和按下状态
            style.map('Success.TButton',
                     background=[('active', '#E8F5E9'),
                                ('pressed', '#E8F5E9')],
                     foreground=[('active', '#388E3C'),
                                ('pressed', '#388E3C')],
                     relief=[('pressed', 'sunken')])
    
    theme_manager = SimpleThemeManager()

'''
AI审校助手安装程序

使用说明:
1. 确保安装包中包含以下文件:
   - AI审校助手.exe (主程序)
   - material/1-logo.ico (安装程序图标)
   - material/2-logo.ico (主程序图标)

2. 打包命令:
   pyinstaller --noconfirm installer.spec

注意事项:
- 安装程序不会在用户电脑上尝试打包主程序
- 安装前会检查必要文件是否存在
- 如果缺少图标文件，将使用默认图标
'''

# 设置日志记录
def setup_logging():
    """设置日志记录"""
    log_dir = os.path.join(os.path.expanduser("~"), "AI审校助手_logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"installer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_file

def main():
    """主函数"""
    try:
        log_file = setup_logging()
        logging.info("安装程序启动")
        logging.info(f"Python 版本: {sys.version}")
        logging.info(f"工作目录: {os.getcwd()}")
        logging.info(f"系统平台: {sys.platform}")
        logging.info(f"命令行参数: {sys.argv}")
        
        installer = InstallerGUI()
        installer.run()
    except Exception as e:
        error_msg = f"发生错误:\n{str(e)}\n\n详细错误信息已保存到:\n{log_file}"
        logging.error(f"未处理的异常: {str(e)}")
        logging.error(f"错误详情:\n{traceback.format_exc()}")
        
        try:
            # 尝试使用 tkinter 显示错误
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("错误", error_msg)
            root.destroy()
        except:
            # 如果 tkinter 失败，使用命令行显示错误
            print("\n" + "="*50)
            print("错误:")
            print(error_msg)
            print("="*50)
            input("\n按回车键退出...")

def get_resource_path(relative_path, required=False):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是打包后的运行，则使用当前目录
        base_path = os.path.abspath(os.path.dirname(__file__))
        # 如果是在scripts目录下，则需要回到上一级目录
        if os.path.basename(base_path) == 'scripts':
            base_path = os.path.dirname(base_path)
    
    # 构建完整路径
    full_path = os.path.join(base_path, relative_path)
    
    # 检查文件是否存在
    if not os.path.exists(full_path):
        # 尝试在material子目录中查找
        alt_path = os.path.join(base_path, 'material', os.path.basename(relative_path))
        if os.path.exists(alt_path):
            return alt_path
            
        # 尝试在当前目录的material子目录中查找
        current_dir_path = os.path.join(os.getcwd(), 'material', os.path.basename(relative_path))
        if os.path.exists(current_dir_path):
            return current_dir_path
            
        # 如果还是找不到，且不是必需的，返回None
        if not required:
            logging.warning(f"找不到资源文件(非必需): {relative_path}")
            return None
            
        # 如果是必需的，则记录详细信息并抛出异常
        error_msg = (
            f"找不到资源文件: {relative_path}\n"
            f"尝试的路径:\n"
            f"1. {full_path}\n"
            f"2. {alt_path}\n"
            f"3. {current_dir_path}\n"
            f"当前目录: {os.getcwd()}\n"
            f"基础路径: {base_path}\n"
            f"_MEIPASS: {getattr(sys, '_MEIPASS', '未定义')}\n"
            f"可用文件列表:\n"
        )
        
        # 列出基础路径下的所有文件
        try:
            files = []
            for root, dirs, filenames in os.walk(base_path):
                rel_path = os.path.relpath(root, base_path)
                for f in filenames:
                    files.append(os.path.join(rel_path, f))
            error_msg += "\n".join(files)
        except Exception as e:
            error_msg += f"无法列出文件: {str(e)}"
            
        raise FileNotFoundError(error_msg)
        
    return full_path

class InstallerGUI:
    def __init__(self):
        logging.info("初始化安装程序界面")
        self.root = tk.Tk()
        self.root.title("AI审校助手 - 安装程序")
        
        # 设置窗口大小和位置
        window_width = 600
        window_height = 550
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 应用主题
        theme_manager.apply_theme(self.root)
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding=theme_manager.get_padding('frame'))
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title = ttk.Label(self.main_frame, 
                         text="AI审校助手安装程序",
                         style='Title.TLabel')
        title.pack(pady=20)
        
        # 安装路径选择
        path_frame = ttk.Frame(self.main_frame)
        path_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(path_frame, text="安装路径：").pack(side=tk.LEFT)
        self.install_path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "AI审校助手"))
        path_entry = ttk.Entry(path_frame, textvariable=self.install_path, width=50)
        path_entry.pack(side=tk.LEFT, padx=5)
        
        browse_btn = ttk.Button(path_frame, text="浏览", command=self.browse_path)
        browse_btn.pack(side=tk.LEFT)
        
        # 创建桌面快捷方式选项
        self.create_shortcut_var = tk.BooleanVar(value=True)
        shortcut_check = ttk.Checkbutton(self.main_frame, 
                                       text="创建桌面快捷方式",
                                       variable=self.create_shortcut_var)
        shortcut_check.pack(pady=10)
        
        # 信息标签
        self.info_label = ttk.Label(self.main_frame,
                                  text="准备安装...",
                                  style='Info.TLabel',
                                  wraplength=500)
        self.info_label.pack(pady=10)
        
        # 详细信息文本框
        self.detail_text = scrolledtext.ScrolledText(self.main_frame, 
                                                   height=8,
                                                   width=60,
                                                   font=theme_manager.get_font('small'))
        self.detail_text.pack(pady=10)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.main_frame,
                                          variable=self.progress_var,
                                          maximum=100,
                                          style='Horizontal.TProgressbar',
                                          length=500)
        self.progress_bar.pack(pady=20)
        
        # 按钮框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=10)
        
        # 安装按钮
        self.install_button = ttk.Button(button_frame,
                                       text="开始安装",
                                       style='Success.TButton',
                                       command=self.start_installation)
        self.install_button.pack(side=tk.LEFT, padx=10)
        
        # 退出按钮
        self.exit_button = ttk.Button(button_frame,
                                    text="退出",
                                    style='Danger.TButton',
                                    command=self.root.destroy)
        self.exit_button.pack(side=tk.LEFT, padx=10)
        
        # 需要创建的文件夹列表
        self.folders = {
            "_1_原文件": "存放待处理的原始文件",
            "_2_审校后": "存放处理完成的文件",
            "hide_file": "存放程序运行时的临时文件",
            "hide_file/中间文件": "存放处理过程中的临时文件",
            "hide_file/配置文件": "存放程序配置文件"
        }
        
        # 主程序exe文件
        self.main_exe = "AI审校助手.exe"
        
        # 检查是否存在打包好的exe文件
        if not os.path.exists(self.main_exe):
            self.log_message(f"警告: 找不到主程序文件 {self.main_exe}，将在安装时查找")
            # 不再调用build_exe方法
        
        # 设置窗口图标
        try:
            icon_path = get_resource_path("1-logo.ico", required=False)
            if icon_path and os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                self.log_message(f"成功加载图标: {icon_path}")
            else:
                self.log_message("未找到图标文件，使用默认图标")
        except Exception as e:
            self.log_message(f"设置窗口图标失败: {str(e)}")
            # 不显示错误对话框，只记录日志
    
    def browse_path(self):
        """浏览并选择安装路径"""
        from tkinter import filedialog
        path = filedialog.askdirectory()
        if path:
            self.install_path.set(path)
    
    def log_message(self, message):
        """添加日志消息到详细信息框"""
        logging.info(message)
        self.detail_text.insert(tk.END, message + "\n")
        self.detail_text.see(tk.END)
        self.root.update()
    
    def update_progress(self, value, message):
        """更新进度条和信息标签"""
        self.progress_var.set(value)
        self.info_label.config(text=message)
        self.root.update()
    
    def create_folder(self, folder_path, description):
        """创建文件夹并返回结果信息"""
        try:
            full_path = os.path.join(self.install_path.get(), folder_path)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
                return f"创建文件夹 {folder_path} 成功: {description}"
            else:
                return f"文件夹 {folder_path} 已存在: {description}"
        except Exception as e:
            return f"创建文件夹 {folder_path} 失败: {str(e)}"
    
    def ensure_exe_icon(self, exe_path, icon_path):
        """确保可执行文件具有正确的图标"""
        try:
            import win32api
            import win32gui
            import win32con
            
            # 检查文件是否存在
            if not os.path.exists(exe_path):
                self.log_message(f"警告: 目标程序不存在: {exe_path}")
                return False
            
            if not os.path.exists(icon_path):
                self.log_message(f"警告: 图标文件不存在: {icon_path}")
                return False
            
            try:
                # 获取当前图标句柄
                large, small = win32gui.ExtractIconEx(exe_path, 0)
                if large:
                    for handle in large:
                        win32gui.DestroyIcon(handle)
                if small:
                    for handle in small:
                        win32gui.DestroyIcon(handle)
                
                # 设置新图标
                icon_handle = win32gui.LoadImage(
                    0, icon_path, win32con.IMAGE_ICON,
                    0, 0, win32con.LR_LOADFROMFILE
                )
                
                if icon_handle:
                    self.log_message(f"成功加载图标: {icon_path}")
                    win32gui.SendMessage(
                        win32gui.GetDesktopWindow(),
                        win32con.WM_SETICON,
                        win32con.ICON_BIG,
                        icon_handle
                    )
                    self.log_message(f"成功设置程序图标: {exe_path}")
                    return True
                else:
                    self.log_message("加载图标失败")
                    return False
                
            except Exception as e:
                self.log_message(f"设置图标失败: {str(e)}")
                return False
                
        except Exception as e:
            self.log_message(f"设置程序图标时出错: {str(e)}")
            return False

    def copy_program_files(self):
        """复制程序文件到安装目录"""
        try:
            # 获取安装路径
            install_dir = self.install_path.get()
            self.log_message(f"正在复制程序文件到: {install_dir}")
            
            # 创建安装目录
            os.makedirs(install_dir, exist_ok=True)
            
            # 查找主程序文件
            exe_found = False
            exe_search_paths = [
                get_resource_path(self.main_exe, required=False),
                os.path.join(".", self.main_exe),
                os.path.join(os.getcwd(), self.main_exe),
                os.path.join(os.path.dirname(sys.executable), self.main_exe),
                os.path.join("dist", self.main_exe),
                os.path.join(os.path.dirname(sys.executable), "dist", self.main_exe),
                os.path.join(os.path.dirname(os.path.dirname(sys.executable)), self.main_exe)
            ]
            
            # 尝试复制主程序文件
            for src_path in exe_search_paths:
                if src_path and os.path.exists(src_path):
                    dst_path = os.path.join(install_dir, self.main_exe)
                    try:
                        shutil.copy2(src_path, dst_path)
                        self.log_message(f"已复制主程序: {src_path} -> {dst_path}")
                        self.log_message(f"文件大小: {os.path.getsize(dst_path)} 字节")
                        exe_found = True
                        break
                    except Exception as e:
                        self.log_message(f"复制主程序文件失败: {str(e)}")
            
            if not exe_found:
                self.log_message("错误: 未找到主程序文件，安装无法继续")
                messagebox.showerror("安装错误", 
                                  "未找到主程序文件，请确保安装包完整。\n\n" +
                                  "请检查以下位置是否存在主程序文件:\n" +
                                  f"1. 当前目录: {os.getcwd()}\n" +
                                  f"2. 程序目录: {os.path.dirname(sys.executable)}")
                return False
            
            # 确保图标文件存在
            if not self.ensure_icon_files():
                self.log_message("警告: 图标文件准备失败，但安装将继续")
            
            # 创建快捷方式
            self.create_shortcut()
            
            self.log_message("程序文件复制完成")
            return True
        except Exception as e:
            self.log_message(f"复制程序文件时出错: {str(e)}")
            return False
    
    def create_shortcut(self):
        """创建桌面快捷方式"""
        try:
            # 获取所有可能的桌面路径
            desktop_paths = []
            try:
                # 本地桌面
                local_desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.exists(local_desktop):
                    desktop_paths.append(local_desktop)
                local_desktop_cn = os.path.join(os.path.expanduser("~"), "桌面")
                if os.path.exists(local_desktop_cn):
                    desktop_paths.append(local_desktop_cn)
                
                # OneDrive 桌面
                onedrive_desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
                if os.path.exists(onedrive_desktop):
                    desktop_paths.append(onedrive_desktop)
                onedrive_desktop_cn = os.path.join(os.path.expanduser("~"), "OneDrive", "桌面")
                if os.path.exists(onedrive_desktop_cn):
                    desktop_paths.append(onedrive_desktop_cn)
                
                if not desktop_paths:
                    raise Exception("找不到任何可用的桌面路径")
                
                self.log_message(f"找到的桌面路径: {', '.join(desktop_paths)}")
            except Exception as e:
                self.log_message(f"警告: 无法获取桌面路径: {str(e)}")
                return False
            
            # 检查目标文件是否存在
            target_exe = os.path.abspath(os.path.join(self.install_path.get(), self.main_exe))
            if not os.path.exists(target_exe):
                self.log_message(f"警告: 目标程序不存在: {target_exe}")
                return False
            else:
                self.log_message(f"目标程序路径: {target_exe}")
                self.log_message(f"目标程序大小: {os.path.getsize(target_exe)} 字节")
            
            # 检查图标文件是否存在
            icon_file = os.path.abspath(os.path.join(self.install_path.get(), '2-logo.ico'))
            has_icon = os.path.exists(icon_file)
            if not has_icon:
                self.log_message(f"警告: 图标文件不存在: {icon_file}")
                # 尝试查找其他可能的图标位置
                alt_icon_paths = [
                    os.path.join(os.path.dirname(target_exe), "material", "2-logo.ico"),
                    os.path.join(os.getcwd(), "material", "2-logo.ico"),
                    os.path.join(os.path.dirname(sys.executable), "material", "2-logo.ico")
                ]
                for alt_path in alt_icon_paths:
                    if os.path.exists(alt_path):
                        icon_file = alt_path
                        has_icon = True
                        self.log_message(f"找到替代图标文件: {icon_file}")
                        break
            else:
                self.log_message(f"图标文件路径: {icon_file}")
            
            # 检查工作目录是否存在
            work_dir = os.path.abspath(self.install_path.get())
            if not os.path.exists(work_dir):
                self.log_message(f"警告: 工作目录不存在: {work_dir}")
                return False
            else:
                self.log_message(f"工作目录: {work_dir}")
            
            success = False
            # 在每个桌面路径上创建快捷方式
            for desktop in desktop_paths:
                try:
                    shortcut_path = os.path.join(desktop, "AI审校助手.lnk")
                    self.log_message(f"\n尝试在以下位置创建快捷方式: {shortcut_path}")
                    
                    # 如果快捷方式已存在，先删除
                    if os.path.exists(shortcut_path):
                        try:
                            os.remove(shortcut_path)
                            self.log_message("已删除旧的快捷方式")
                            # 等待文件系统更新
                            self.root.after(1000)
                        except Exception as e:
                            self.log_message(f"警告: 无法删除已存在的快捷方式: {str(e)}")
                            continue
                    
                    try:
                        # 直接使用 win32com 创建快捷方式
                        import win32com.client
                        shell = win32com.client.Dispatch("WScript.Shell")
                        shortcut = shell.CreateShortCut(shortcut_path)
                        
                        # 设置快捷方式属性
                        shortcut.TargetPath = target_exe
                        shortcut.WorkingDirectory = work_dir
                        if has_icon:
                            shortcut.IconLocation = icon_file
                        shortcut.Description = "AI审校助手"
                        
                        # 保存快捷方式
                        self.log_message("正在保存快捷方式...")
                        shortcut.Save()
                        
                        # 等待文件系统更新
                        self.root.after(1000)
                        
                        # 检查快捷方式是否真的创建成功
                        if os.path.exists(shortcut_path):
                            size = os.path.getsize(shortcut_path)
                            self.log_message(f"快捷方式创建成功，文件大小: {size} 字节")
                            success = True
                        else:
                            raise Exception("快捷方式文件不存在")
                        
                    except Exception as e:
                        self.log_message(f"警告: 使用win32com创建快捷方式失败: {str(e)}")
                        
                        try:
                            # 使用 subprocess 直接执行 PowerShell 命令
                            ps_command = f'''
                            $shell = New-Object -ComObject WScript.Shell;
                            $shortcut = $shell.CreateShortcut('{shortcut_path}');
                            $shortcut.TargetPath = '{target_exe}';
                            $shortcut.WorkingDirectory = '{work_dir}';
                            '''
                            
                            # 只有在图标文件存在时才设置图标
                            if has_icon:
                                ps_command += f"$shortcut.IconLocation = '{icon_file}';\n"
                                
                            ps_command += '''
                            $shortcut.Description = 'AI审校助手';
                            $shortcut.Save();
                            '''
                            
                            self.log_message("尝试使用PowerShell创建快捷方式...")
                            result = subprocess.run(['powershell', '-Command', ps_command], 
                                                 capture_output=True, text=True)
                            
                            if result.returncode != 0:
                                self.log_message(f"PowerShell错误输出: {result.stderr}")
                                raise Exception(f"PowerShell返回错误代码: {result.returncode}")
                            
                            # 检查快捷方式是否创建成功
                            if os.path.exists(shortcut_path) and os.path.getsize(shortcut_path) > 0:
                                size = os.path.getsize(shortcut_path)
                                self.log_message(f"使用PowerShell成功创建快捷方式，文件大小: {size} 字节")
                                success = True
                            else:
                                raise Exception("快捷方式创建失败：文件不存在或大小为0")
                            
                        except Exception as e2:
                            self.log_message(f"警告: 在此位置创建快捷方式失败: {str(e2)}")
                            continue
                            
                except Exception as e:
                    self.log_message(f"警告: 在 {desktop} 创建快捷方式失败: {str(e)}")
                    continue
            
            return success
            
        except Exception as e:
            self.log_message(f"警告: 创建快捷方式过程出错: {str(e)}")
            return False
    
    def start_installation(self):
        """开始安装过程"""
        try:
            self.install_button.config(state='disabled')
            self.detail_text.delete(1.0, tk.END)
            
            # 检查安装包完整性
            self.update_progress(0, "正在检查安装包完整性...")
            if not self.check_installation_integrity():
                self.update_progress(0, "安装包不完整，无法继续安装")
                messagebox.showerror("安装错误", 
                                  "安装包不完整，缺少必要文件。\n\n" +
                                  "请重新下载完整的安装包后再试。")
                self.install_button.config(state='normal')
                return
            
            # 检查并删除已存在的安装目录
            install_path = self.install_path.get()
            if os.path.exists(install_path):
                self.update_progress(5, "正在删除已存在的安装目录...")
                try:
                    # 首先尝试删除可能被占用的exe文件
                    exe_path = os.path.join(install_path, self.main_exe)
                    if os.path.exists(exe_path):
                        try:
                            os.chmod(exe_path, 0o777)  # 尝试修改文件权限
                            os.remove(exe_path)
                            self.log_message("已删除旧的exe文件")
                        except Exception as e:
                            self.log_message(f"警告: 无法删除exe文件，可能正在运行: {str(e)}")
                            messagebox.showwarning("警告", 
                                               "请关闭正在运行的AI审校助手程序后再继续安装。\n" +
                                               "点击确定后重试...")
                            # 等待一段时间后重试
                            self.root.after(2000)
                            try:
                                os.remove(exe_path)
                            except Exception as e2:
                                raise Exception(f"无法删除程序文件，请手动关闭程序后重试: {str(e2)}")
                    
                    # 然后删除整个目录
                    for root, dirs, files in os.walk(install_path, topdown=False):
                        for name in files:
                            try:
                                file_path = os.path.join(root, name)
                                os.chmod(file_path, 0o777)
                                os.remove(file_path)
                            except Exception as e:
                                self.log_message(f"警告: 无法删除文件 {name}: {str(e)}")
                        for name in dirs:
                            try:
                                dir_path = os.path.join(root, name)
                                os.rmdir(dir_path)
                            except Exception as e:
                                self.log_message(f"警告: 无法删除目录 {name}: {str(e)}")
                    
                    # 最后删除根目录
                    try:
                        os.rmdir(install_path)
                    except Exception as e:
                        self.log_message(f"警告: 无法删除根目录: {str(e)}")
                        # 如果目录非空，强制删除
                        import shutil
                        shutil.rmtree(install_path, ignore_errors=True)
                    
                    self.log_message(f"已删除原有安装目录: {install_path}")
                except Exception as e:
                    raise Exception(f"删除原有安装目录失败: {str(e)}")
            
            # 创建安装目录
            self.update_progress(10, "正在创建安装目录...")
            os.makedirs(install_path, exist_ok=True)
            
            # 复制程序文件
            self.update_progress(15, "正在复制程序文件...")
            if not self.copy_program_files():
                raise Exception("复制程序文件失败")
            
            # 确保图标文件存在
            self.update_progress(30, "正在准备图标文件...")
            self.ensure_icon_files()
            
            # 创建必要的文件夹
            total_folders = len(self.folders)
            for i, (folder, description) in enumerate(self.folders.items(), 1):
                progress = 40 + (i / total_folders * 30)
                self.update_progress(progress, f"正在创建: {folder}")
                result = self.create_folder(folder, description)
                self.log_message(result)
                self.root.after(200)  # 短暂延迟以显示进度
            
            # 创建快捷方式
            if self.create_shortcut_var.get():
                self.update_progress(90, "正在创建桌面快捷方式...")
                if not self.create_shortcut():
                    self.log_message("警告: 创建快捷方式失败")
            
            # 安装完成
            self.update_progress(100, "安装完成！")
            messagebox.showinfo("安装完成", 
                              f"AI审校助手已成功安装到：\n{self.install_path.get()}\n\n" +
                              "现在可以运行程序了！")
            # 安装完成后自动退出
            self.root.quit()
            
        except Exception as e:
            self.log_message(f"安装过程出错: {str(e)}")
            messagebox.showerror("错误", f"安装过程中出现错误：\n{str(e)}")
        finally:
            self.install_button.config(state='normal')
    
    def run(self):
        """运行安装程序"""
        self.root.mainloop()

    def show_error(self, title, message):
        """显示错误对话框"""
        messagebox.showerror(title, message)

    def ensure_icon_files(self):
        """确保图标文件存在于安装目录中"""
        self.log_message("正在准备图标文件...")
        
        # 创建图标目录
        icon_dir = os.path.join(self.install_path.get(), "material")
        os.makedirs(icon_dir, exist_ok=True)
        
        # 图标文件列表
        icon_files = ["1-logo.ico", "2-logo.ico"]
        icons_copied = []
        
        # 尝试复制图标文件
        for icon in icon_files:
            # 尝试查找图标文件
            icon_path = get_resource_path(icon, required=False)
            if not icon_path:
                icon_path = os.path.join("material", icon)
            
            # 目标路径
            target_path = os.path.join(icon_dir, icon)
            
            # 如果找到图标文件，复制它
            if icon_path and os.path.exists(icon_path):
                try:
                    shutil.copy2(icon_path, target_path)
                    self.log_message(f"已复制图标文件: {icon}")
                    icons_copied.append(icon)
                except Exception as e:
                    self.log_message(f"复制图标文件失败: {icon}, 错误: {str(e)}")
            else:
                self.log_message(f"未找到图标文件: {icon}，将创建空白图标")
        
        # 检查是否所有图标都已复制
        missing_icons = [icon for icon in icon_files if icon not in icons_copied]
        
        # 为缺失的图标创建空白图标
        if missing_icons:
            self.log_message("正在创建空白图标文件...")
            for icon in missing_icons:
                target_path = os.path.join(icon_dir, icon)
                try:
                    self.create_blank_icon(target_path)
                    self.log_message(f"已创建空白图标: {icon}")
                except Exception as e:
                    self.log_message(f"创建空白图标失败: {icon}, 错误: {str(e)}")
        
        return True
        
    def create_blank_icon(self, filepath, size=32):
        """创建一个空白的图标文件"""
        try:
            # 尝试导入PIL库
            from PIL import Image
            
            # 创建空白图像
            img = Image.new('RGBA', (size, size), color=(255, 255, 255, 0))
            
            # 保存为ICO文件
            img.save(filepath, format='ICO')
            return True
        except ImportError:
            self.log_message("警告: 未安装PIL库，无法创建空白图标")
            # 创建一个空文件作为替代
            with open(filepath, 'wb') as f:
                # 写入最小的有效ICO文件头
                f.write(bytes.fromhex('00 00 01 00 01 00 10 10 00 00 01 00 04 00 28 01 00 00 16 00 00 00 28 00 00 00 10 00 00 00 20 00 00 00 01 00 04 00 00 00 00 00 80 00 00 00 00 00 00 00 00 00 00 00 10 00 00 00 00 00 00 00'))
            return True
        except Exception as e:
            self.log_message(f"创建空白图标时出错: {str(e)}")
            return False

    def check_installation_integrity(self):
        """检查安装包完整性"""
        self.log_message("正在检查安装包完整性...")
        
        # 检查主程序文件
        exe_found = False
        exe_search_paths = [
            get_resource_path(self.main_exe, required=False),
            os.path.join(".", self.main_exe),
            os.path.join(os.getcwd(), self.main_exe),
            os.path.join(os.path.dirname(sys.executable), self.main_exe),
            os.path.join("dist", self.main_exe),
            os.path.join(os.path.dirname(sys.executable), "dist", self.main_exe),
            os.path.join(os.path.dirname(os.path.dirname(sys.executable)), self.main_exe)
        ]
        
        self.log_message(f"正在以下位置查找主程序文件 {self.main_exe}:")
        for i, path in enumerate(exe_search_paths, 1):
            self.log_message(f"  {i}. {path}")
            if path and os.path.exists(path):
                self.log_message(f"✓ 找到主程序: {path}")
                self.log_message(f"  文件大小: {os.path.getsize(path)} 字节")
                exe_found = True
                break
            else:
                self.log_message(f"✗ 未找到")
        
        if not exe_found:
            self.log_message("警告: 未找到主程序文件，安装可能无法完成")
            
        # 检查图标文件
        icons_found = []
        icon_files = ["1-logo.ico", "2-logo.ico"]
        
        self.log_message("正在查找图标文件:")
        for icon in icon_files:
            icon_search_paths = [
                get_resource_path(icon, required=False),
                os.path.join("material", icon),
                os.path.join(os.getcwd(), "material", icon),
                os.path.join(os.path.dirname(sys.executable), "material", icon),
                os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "material", icon),
                os.path.join(".", icon)
            ]
            
            icon_found = False
            self.log_message(f"  正在查找图标: {icon}")
            for path in icon_search_paths:
                if path and os.path.exists(path):
                    self.log_message(f"  ✓ 找到图标文件: {path}")
                    icons_found.append(icon)
                    icon_found = True
                    break
            
            if not icon_found:
                self.log_message(f"  ✗ 未找到图标: {icon}")
        
        if len(icons_found) < len(icon_files):
            missing_icons = [icon for icon in icon_files if icon not in icons_found]
            self.log_message(f"警告: 未找到以下图标文件: {', '.join(missing_icons)}")
            self.log_message("将使用默认图标或创建空白图标")
        
        # 检查系统环境
        self.log_message("\n系统环境信息:")
        self.log_message(f"  操作系统: {sys.platform}")
        self.log_message(f"  Python版本: {sys.version}")
        self.log_message(f"  当前目录: {os.getcwd()}")
        self.log_message(f"  程序目录: {os.path.dirname(sys.executable)}")
        self.log_message(f"  临时目录: {getattr(sys, '_MEIPASS', '未定义')}")
        
        # 返回检查结果
        if exe_found:
            self.log_message("✓ 安装包完整性检查通过")
            return True
        else:
            self.log_message("✗ 安装包完整性检查失败: 缺少主程序文件")
            return False

if __name__ == "__main__":
    main() 