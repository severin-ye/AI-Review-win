import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import os
import sys
import json
import logging
from datetime import datetime
from .path_manager import path_manager

class ConfigManager:
    def __init__(self):
        # 从 constants.py 导入常量
        from ..constants import (
            MODULE_LIST,
            LABEL_NAMES,
            LABEL_WIDTH,
            ENTRY_WIDTH,
            PROMPT_TEXT_HEIGHT,
            PROMPT_TEXT_WIDTH,
            BUTTON_PAD_Y,
            DEFAULT_PROMPT
        )
        
        self.config_vars = {}
        self.prompt_text = None
        self.module_list = MODULE_LIST
        self.label_names = LABEL_NAMES
        self.label_width = LABEL_WIDTH
        self.entry_width = ENTRY_WIDTH
        self.prompt_text_height = PROMPT_TEXT_HEIGHT
        self.prompt_text_width = PROMPT_TEXT_WIDTH
        self.button_pad_y = BUTTON_PAD_Y
        self.option_menu_width = ENTRY_WIDTH
        self.default_output_dir = path_manager.reviewed_files_dir
        self.default_prompt = DEFAULT_PROMPT
        self._theme_manager = None
    
    @property
    def theme_manager(self):
        if self._theme_manager is None:
            from src.ui.styles.theme_manager import theme_manager
            self._theme_manager = theme_manager
            # 加载主题配置
            from ..settings import theme_config
            self._theme_manager.update_theme(theme_config)
        return self._theme_manager
    
    def set_widgets(self, config_vars, prompt_text=None):
        """设置配置变量和prompt文本框"""
        self.config_vars = config_vars
        self.prompt_text = prompt_text
    
    def validate_api_key(self, api_key, key_type):
        """验证 API 密钥的格式"""
        if not api_key:
            return True  # 允许空密钥
            
        if key_type == 'openai':
            return api_key.startswith('sk-') and len(api_key) > 20
        elif key_type == 'tyqw':
            return len(api_key) > 20
        return False
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(path_manager.config_file, 'r', encoding='utf-8') as file:
                config_data = json.load(file)
            
            if self.config_vars:
                # 加载 API 密钥
                api_keys = config_data.get('api_keys', {})
                openai_key = api_keys.get('openai', '')
                tyqw_key = api_keys.get('tyqw', '')
                
                # 验证 API 密钥
                if not self.validate_api_key(openai_key, 'openai'):
                    messagebox.showwarning("警告", "OpenAI API 密钥格式无效")
                if not self.validate_api_key(tyqw_key, 'tyqw'):
                    messagebox.showwarning("警告", "通义千问 API 密钥格式无效")
                
                # 设置 API 密钥
                self.config_vars['openai_api_key'].set(openai_key)
                self.config_vars['tyqw_api_key'].set(tyqw_key)
                
                # 加载其他配置
                self.config_vars['module_type'].set(config_data.get('module_type', 'gpt-4o'))
                self.config_vars['has_review_table'].set('Y' if config_data.get('has_review_table', True) else 'N')
                self.config_vars['output_dir'].set(config_data.get('output_dir', self.default_output_dir))
                
                # 加载 prompt
                if self.prompt_text:
                    self.prompt_text.delete('1.0', tk.END)
                    self.prompt_text.insert('1.0', config_data.get('prompt', self.default_prompt))
            
            return config_data
            
        except FileNotFoundError:
            return self._create_default_config()
        except Exception as e:
            logging.error(f"加载配置失败：{str(e)}")
            if self.config_vars:
                messagebox.showerror("错误", f"无法加载配置：{str(e)}")
            return {}
    
    def save_config(self):
        """保存配置到文件"""
        try:
            if not self.config_vars:
                raise ValueError("配置变量未初始化")
                
            # 验证 API 密钥
            openai_key = self.config_vars["openai_api_key"].get().strip()
            tyqw_key = self.config_vars["tyqw_api_key"].get().strip()
            
            if not self.validate_api_key(openai_key, 'openai'):
                messagebox.showerror("错误", "OpenAI API 密钥格式无效")
                return False
                
            if not self.validate_api_key(tyqw_key, 'tyqw'):
                messagebox.showerror("错误", "通义千问 API 密钥格式无效")
                return False

            # 获取 prompt 内容
            prompt_content = self.default_prompt
            if self.prompt_text:
                try:
                    prompt_content = self.prompt_text.get('1.0', tk.END).strip()
                except Exception as e:
                    logging.error(f"获取 prompt 内容时出错：{str(e)}")

            # 构建配置数据
            config_data = {
                "api_keys": {
                    "openai": openai_key,
                    "tyqw": tyqw_key
                },
                "module_type": self.config_vars["module_type"].get(),
                "has_review_table": self.config_vars["has_review_table"].get() == 'Y',
                "output_dir": self.config_vars["output_dir"].get(),
                "prompt": prompt_content
            }
            
            # 保存配置
            os.makedirs(os.path.dirname(path_manager.config_file), exist_ok=True)
            with open(path_manager.config_file, 'w', encoding='utf-8') as file:
                json.dump(config_data, file, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("成功", "配置已保存")
            return True
            
        except Exception as e:
            logging.error(f"保存配置失败：{str(e)}")
            messagebox.showerror("错误", f"无法保存配置：{str(e)}")
            return False
    
    def _create_default_config(self):
        """创建默认配置"""
        config_data = {
            "api_keys": {
                "openai": "",
                "tyqw": ""
            },
            "module_type": self.module_list[0],
            "has_review_table": True,
            "output_dir": self.default_output_dir,
            "prompt": self.default_prompt
        }
        
        try:
            os.makedirs(os.path.dirname(path_manager.config_file), exist_ok=True)
            with open(path_manager.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            return config_data
        except Exception as e:
            logging.error(f"创建默认配置失败：{str(e)}")
            return {}

# 创建全局实例
config_manager = ConfigManager() 