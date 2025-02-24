import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import shutil
import sys
import subprocess
import winreg
import json
from pathlib import Path

class InstallerGUI:
    def __init__(self):
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
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure('Title.TLabel', font=('Microsoft YaHei UI', 16, 'bold'))
        self.style.configure('Info.TLabel', font=('Microsoft YaHei UI', 10))
        self.style.configure('Progress.Horizontal.TProgressbar', thickness=15)
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="20")
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
                                                   font=('Microsoft YaHei UI', 9))
        self.detail_text.pack(pady=10)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.main_frame,
                                          variable=self.progress_var,
                                          maximum=100,
                                          style='Progress.Horizontal.TProgressbar',
                                          length=500)
        self.progress_bar.pack(pady=20)
        
        # 按钮框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=10)
        
        # 安装按钮
        self.install_button = ttk.Button(button_frame,
                                       text="开始安装",
                                       command=self.start_installation)
        self.install_button.pack(side=tk.LEFT, padx=5)
        
        # 退出按钮
        self.exit_button = ttk.Button(button_frame,
                                    text="退出",
                                    command=self.root.quit)
        self.exit_button.pack(side=tk.LEFT, padx=5)
        
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
            self.build_exe()
    
    def build_exe(self):
        """使用PyInstaller打包主程序"""
        try:
            self.log_message("正在打包主程序...")
            self.update_progress(5, "准备打包环境...")
            
            # 创建spec文件内容
            spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['s_0_main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'win32com.client',
        'winshell',
        'json',
        'subprocess',
        'shutil'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI审校助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['material/2-logo.ico'],
    collect_all=['s_1_auto_ai', 's_2_select_replace', 's_3_clear_out', 's_4_config_use',
                'w0_file_path', 'w1_table_about', 'w2_docx_to_md', 'w3_smart_divide',
                'w4_ai_answer', 'w5_same_find', 'w6_1_key_generator', 'w6_2_key_verifier',
                'config', 'time_lock']
)
'''
            # 写入spec文件
            with open('ai_review.spec', 'w', encoding='utf-8') as f:
                f.write(spec_content)
            
            self.update_progress(10, "正在分析依赖关系...")
            
            # 运行PyInstaller
            python_exe = sys.executable
            pyinstaller_cmd = [
                python_exe,
                '-m',
                'PyInstaller',
                '--noconfirm',
                'ai_review.spec'
            ]
            
            process = subprocess.Popen(
                pyinstaller_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 定义关键阶段和对应的进度
            stages = {
                'Analyzing dependencies': (15, "正在分析程序依赖..."),
                'Analyzing': (20, "正在分析文件..."),
                'Processing': (30, "正在处理文件..."),
                'Searching': (40, "正在搜索依赖..."),
                'Loading module': (50, "正在加载模块..."),
                'Building EXE': (60, "正在构建可执行文件..."),
                'Building PYZ': (70, "正在打包Python模块..."),
                'Building PKG': (80, "正在打包资源文件..."),
                'Copying': (90, "正在复制必要文件...")
            }
            
            # 用于存储当前阶段的计数器
            stage_counters = {}
            last_progress = 10
            
            # 实时读取输出并更新进度
            while True:
                # 读取标准输出
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                line = line.strip()
                if line:
                    self.log_message(line)
                    
                    # 检查是否进入新阶段
                    for stage, (base_progress, message) in stages.items():
                        if stage in line:
                            if stage not in stage_counters:
                                stage_counters[stage] = 0
                            stage_counters[stage] += 1
                            
                            # 计算当前阶段的进度
                            stage_progress = min(5, stage_counters[stage])
                            current_progress = base_progress + stage_progress
                            
                            # 确保进度不会后退
                            if current_progress > last_progress:
                                last_progress = current_progress
                                self.update_progress(current_progress, f"{message} ({stage_counters[stage]})")
                            break
                
                # 读取错误输出
                error = process.stderr.readline()
                if error:
                    error = error.strip()
                    if error:
                        self.log_message(f"警告: {error}")
                
                # 更新界面
                self.root.update()
            
            # 检查进程返回值
            if process.returncode != 0:
                error_output = process.stderr.read()
                self.log_message("错误输出:")
                self.log_message(error_output)
                raise Exception("PyInstaller打包失败")
            
            # 复制生成的exe文件
            self.update_progress(95, "正在完成打包...")
            dist_exe = os.path.join('dist', 'AI审校助手.exe')
            if os.path.exists(dist_exe):
                shutil.copy2(dist_exe, self.main_exe)
                self.update_progress(100, "打包完成！")
                self.log_message("主程序打包完成！")
            else:
                raise Exception("找不到生成的exe文件")
                
        except Exception as e:
            self.log_message(f"打包主程序时出错: {str(e)}")
            raise
    
    def browse_path(self):
        """浏览并选择安装路径"""
        from tkinter import filedialog
        path = filedialog.askdirectory()
        if path:
            self.install_path.set(path)
    
    def log_message(self, message):
        """添加日志消息到详细信息框"""
        self.detail_text.insert(tk.END, message + "\n")
        self.detail_text.see(tk.END)
        self.root.update()
    
    def update_progress(self, value, message):
        """更新进度条和信息标签"""
        self.progress_var.set(value)
        self.info_label.config(text=message)
        self.log_message(message)
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
    
    def copy_program_files(self):
        """复制程序文件到安装目录"""
        try:
            current_dir = os.getcwd()
            
            # 复制主程序exe
            if os.path.exists(self.main_exe):
                dst_exe = os.path.join(self.install_path.get(), self.main_exe)
                shutil.copy2(self.main_exe, dst_exe)
                self.log_message(f"复制文件: {self.main_exe}")
            else:
                raise Exception("找不到主程序exe文件")
            
            # 复制图标文件
            icon_src = os.path.join('material', '2-logo.ico')
            if os.path.exists(icon_src):
                icon_dst = os.path.join(self.install_path.get(), '2-logo.ico')
                shutil.copy2(icon_src, icon_dst)
                self.log_message(f"复制文件: {icon_src}")
            else:
                raise Exception("找不到图标文件")
            
            return True
        except Exception as e:
            self.log_message(f"复制文件时出错: {str(e)}")
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
            if not os.path.exists(icon_file):
                self.log_message(f"警告: 图标文件不存在: {icon_file}")
                return False
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
                            $shortcut.IconLocation = '{icon_file}';
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
            
            # 检查并删除已存在的安装目录
            install_path = self.install_path.get()
            if os.path.exists(install_path):
                self.update_progress(0, "正在删除已存在的安装目录...")
                try:
                    shutil.rmtree(install_path)
                    self.log_message(f"已删除原有安装目录: {install_path}")
                except Exception as e:
                    raise Exception(f"删除原有安装目录失败: {str(e)}")
            
            # 创建安装目录
            self.update_progress(5, "正在创建安装目录...")
            os.makedirs(install_path)
            
            # 复制程序文件
            self.update_progress(10, "正在复制程序文件...")
            if not self.copy_program_files():
                raise Exception("复制程序文件失败")
            
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
            
        except Exception as e:
            self.log_message(f"安装过程出错: {str(e)}")
            messagebox.showerror("错误", f"安装过程中出现错误：\n{str(e)}")
        finally:
            self.install_button.config(state='normal')
    
    def run(self):
        """运行安装程序"""
        self.root.mainloop()

if __name__ == "__main__":
    installer = InstallerGUI()
    installer.run() 