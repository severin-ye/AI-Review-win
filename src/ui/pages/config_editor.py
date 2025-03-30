try:
    import ttkbootstrap as ttk
    from tkinter import messagebox, scrolledtext, LEFT, RIGHT, TOP, BOTH, X, Y, W
    
    # 直接从各个模块导入需要的常量
    import sys
    import os
    import logging
    import traceback
    from datetime import datetime
    
    # 添加项目根目录到Python路径
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 设置日志
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"config_editor_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("config_editor")
    logger.info("配置编辑器启动")
    
    from config.constants import MODULE_LIST, LABEL_NAMES, LABEL_WIDTH, ENTRY_WIDTH, PROMPT_TEXT_HEIGHT, PROMPT_TEXT_WIDTH
    from config.managers.config_manager import config_manager
    
    class ConfigEditor:
        def __init__(self):
            self.root = None
            logger.info("ConfigEditor实例化")
        
        def create_window(self):
            """创建配置编辑器窗口"""
            try:
                self.root = ttk.Window(themename="litera")
                self.root.title("配置编辑器")
                self.root.geometry("800x600")
                
                # 创建主框架
                main_frame = ttk.Frame(self.root)
                main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
                
                # 创建标题
                title = ttk.Label(main_frame, 
                                 text="配置编辑器",
                                 font=config_manager.theme_manager.get_font('title'),
                                 bootstyle="primary")
                title.pack(pady=20)
                
                # 使用ConfigManager的create_config_ui方法创建配置界面
                config_ui_frame = config_manager.create_config_ui(main_frame)
                config_ui_frame.pack(fill=BOTH, expand=True, pady=10)
                
                # 创建按钮框架
                button_frame = ttk.Frame(main_frame)
                button_frame.pack(pady=20)
                
                save_button = ttk.Button(button_frame,
                                      text="保存配置",
                                      bootstyle="success",
                                      command=self.save_config)
                save_button.pack(side=LEFT, padx=10)
                
                cancel_button = ttk.Button(button_frame,
                                        text="取消",
                                        bootstyle="secondary",
                                        command=self.root.destroy)
                cancel_button.pack(side=LEFT, padx=10)
                
                # 运行窗口
                logger.info("启动主窗口")
                self.root.mainloop()
            except Exception as e:
                logger.error(f"创建窗口时出错: {e}")
                logger.error(traceback.format_exc())
                messagebox.showerror("错误", f"创建窗口时出错: {e}")
        
        def save_config(self):
            """保存配置"""
            try:
                logger.info("保存配置")
                if config_manager.save_ui_config():
                    logger.info("配置保存成功")
                    messagebox.showinfo("成功", "配置已保存！")
                    self.root.destroy()
                else:
                    logger.warning("配置保存失败")
            except Exception as e:
                logger.error(f"保存配置时出错: {e}")
                logger.error(traceback.format_exc())
                messagebox.showerror("错误", f"保存配置时出错: {e}")

    if __name__ == "__main__":
        logger.info("创建ConfigEditor实例")
        editor = ConfigEditor()
        editor.create_window()
except Exception as e:
    try:
        logging.error(f"发生严重错误: {e}")
        logging.error(traceback.format_exc())
    except:
        pass
    import traceback
    print(f"发生错误: {e}")
    print(traceback.format_exc()) 