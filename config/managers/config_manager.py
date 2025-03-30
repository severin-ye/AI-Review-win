"""
配置管理器类
负责应用配置的加载、保存和验证
"""

import os
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config.core import path_manager
from config.constants import (
    MODULE_LIST, 
    LABEL_NAMES, 
    LABEL_WIDTH, 
    ENTRY_WIDTH,
    PROMPT_TEXT_HEIGHT,
    PROMPT_TEXT_WIDTH,
    DEFAULT_PROMPT,
    DEFAULT_MEDICAL_PROMPT,
    DEFAULT_ENABLE_MEDICAL_RAG
)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_path = path_manager.get_app_config_path()
        self.theme_config = path_manager.get_theme_config()
        self.config = self.load_config()
        
        # UI组件
        self.openai_api_key_entry = None
        self.tyqw_api_key_entry = None
        self.module_type_combobox = None
        self.prompt_text = None
        self.has_review_table_combobox = None
        self.enable_medical_rag_checkbox = None
        self.enable_medical_rag_var = None
        
    def load_config(self):
        """加载配置文件
        
        Returns:
            dict: 加载的配置信息
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self.create_default_config()
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            return self.create_default_config()
        
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置文件时出错: {e}")
        
    def create_default_config(self):
        """创建默认配置
        
        Returns:
            dict: 默认配置
        """
        default_config = {
            "openai_api_key": "",
            "tyqw_api_key": "",
            "module_type": MODULE_LIST[0],
            "prompt": DEFAULT_PROMPT,
            "has_review_table": "Y",
            "output_dir": path_manager.get_default_output_dir(),
            "enable_medical_rag": DEFAULT_ENABLE_MEDICAL_RAG
        }
        return default_config
    
    def validate_api_key_format(self, api_key, provider="openai"):
        """验证API密钥格式
        
        Args:
            api_key (str): API密钥
            provider (str): 提供商，如'openai'或'tyqw'
            
        Returns:
            bool: 格式是否有效
        """
        if not api_key:
            return False
        
        if provider == "openai":
            # OpenAI API密钥格式: "sk-" 后跟48个字符
            return bool(re.match(r'^sk-[A-Za-z0-9]{48}$', api_key))
        elif provider == "tyqw":
            # 通义千问API密钥格式: 长度至少为10个字符
            return len(api_key) >= 10
        
        return False
        
    def create_config_ui(self, parent_frame):
        """创建配置界面
        
        Args:
            parent_frame (tk.Frame): 父级框架
            
        Returns:
            tuple: 配置框架和配置项
        """
        frame = ttk.Frame(parent_frame)
        
        # OpenAI API Key
        openai_key_label = ttk.Label(frame, text=LABEL_NAMES["openai_api_key"], width=LABEL_WIDTH)
        openai_key_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.openai_api_key_entry = ttk.Entry(frame, width=ENTRY_WIDTH)
        self.openai_api_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.openai_api_key_entry.insert(0, self.config.get("openai_api_key", ""))
        
        # 通义千问 API Key
        tyqw_key_label = ttk.Label(frame, text=LABEL_NAMES["tyqw_api_key"], width=LABEL_WIDTH)
        tyqw_key_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.tyqw_api_key_entry = ttk.Entry(frame, width=ENTRY_WIDTH)
        self.tyqw_api_key_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.tyqw_api_key_entry.insert(0, self.config.get("tyqw_api_key", ""))
        
        # 模型类型
        module_type_label = ttk.Label(frame, text=LABEL_NAMES["module_type"], width=LABEL_WIDTH)
        module_type_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        self.module_type_combobox = ttk.Combobox(frame, values=MODULE_LIST, width=ENTRY_WIDTH-3)
        self.module_type_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.module_type_combobox.set(self.config.get("module_type", MODULE_LIST[0]))
        
        # 是否有审校表格
        has_review_table_label = ttk.Label(frame, text=LABEL_NAMES["has_review_table"], width=LABEL_WIDTH)
        has_review_table_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        
        self.has_review_table_combobox = ttk.Combobox(frame, values=["Y", "N"], width=ENTRY_WIDTH-3)
        self.has_review_table_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.has_review_table_combobox.set(self.config.get("has_review_table", "Y"))
        
        # 启用医学RAG系统
        medical_rag_label = ttk.Label(frame, text=LABEL_NAMES["enable_medical_rag"], width=LABEL_WIDTH)
        medical_rag_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        
        self.enable_medical_rag_var = tk.BooleanVar(value=self.config.get("enable_medical_rag", DEFAULT_ENABLE_MEDICAL_RAG))
        self.enable_medical_rag_checkbox = ttk.Checkbutton(frame, variable=self.enable_medical_rag_var)
        self.enable_medical_rag_checkbox.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        
        # 绑定医学RAG复选框变更事件
        self.enable_medical_rag_var.trace_add("write", self.toggle_medical_prompt)
        
        # 输出目录
        output_dir_label = ttk.Label(frame, text=LABEL_NAMES["output_dir"], width=LABEL_WIDTH)
        output_dir_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
        
        output_dir_frame = ttk.Frame(frame)
        output_dir_frame.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        
        self.output_dir_entry = ttk.Entry(output_dir_frame, width=ENTRY_WIDTH-5)
        self.output_dir_entry.pack(side="left", fill="x", expand=True)
        self.output_dir_entry.insert(0, self.config.get("output_dir", path_manager.get_default_output_dir()))
        
        browse_button = ttk.Button(output_dir_frame, text="浏览", width=5, command=self.browse_output_dir)
        browse_button.pack(side="right", padx=(5, 0))
        
        # 提示语
        prompt_label = ttk.Label(frame, text=LABEL_NAMES["prompt"], width=LABEL_WIDTH)
        prompt_label.grid(row=6, column=0, padx=5, pady=5, sticky="nw")
        
        self.prompt_text = tk.Text(frame, height=PROMPT_TEXT_HEIGHT, width=PROMPT_TEXT_WIDTH)
        self.prompt_text.grid(row=6, column=1, padx=5, pady=5, sticky="nsew")
        self.prompt_text.insert("1.0", self.config.get("prompt", DEFAULT_PROMPT))
        
        # 设置行列权重
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, weight=1)
        
        return frame
    
    def toggle_medical_prompt(self, *args):
        """根据医学RAG系统的启用状态切换提示语"""
        if self.enable_medical_rag_var.get():
            # 只有当当前提示语是默认值时才自动切换到医学提示语
            current_prompt = self.prompt_text.get("1.0", "end-1c").strip()
            if current_prompt == DEFAULT_PROMPT:
                self.prompt_text.delete("1.0", "end")
                self.prompt_text.insert("1.0", DEFAULT_MEDICAL_PROMPT)
        else:
            # 只有当当前提示语是医学提示语时才自动切换回默认提示语
            current_prompt = self.prompt_text.get("1.0", "end-1c").strip()
            if current_prompt == DEFAULT_MEDICAL_PROMPT:
                self.prompt_text.delete("1.0", "end")
                self.prompt_text.insert("1.0", DEFAULT_PROMPT)
    
    def browse_output_dir(self):
        """浏览并选择输出目录"""
        current_dir = self.output_dir_entry.get()
        dir_path = filedialog.askdirectory(initialdir=current_dir if os.path.exists(current_dir) else ".")
        if dir_path:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, dir_path)
    
    def save_ui_config(self):
        """从UI保存配置"""
        # 获取API密钥
        openai_api_key = self.openai_api_key_entry.get()
        tyqw_api_key = self.tyqw_api_key_entry.get()
        
        # 验证API密钥格式
        if openai_api_key and not self.validate_api_key_format(openai_api_key, "openai"):
            messagebox.showerror("错误", "OpenAI API密钥格式无效")
            return False
        
        if tyqw_api_key and not self.validate_api_key_format(tyqw_api_key, "tyqw"):
            messagebox.showerror("错误", "通义千问API密钥格式无效")
            return False
        
        # 更新配置
        self.config["openai_api_key"] = openai_api_key
        self.config["tyqw_api_key"] = tyqw_api_key
        self.config["module_type"] = self.module_type_combobox.get()
        self.config["prompt"] = self.prompt_text.get("1.0", "end-1c")
        self.config["has_review_table"] = self.has_review_table_combobox.get()
        self.config["output_dir"] = self.output_dir_entry.get()
        self.config["enable_medical_rag"] = self.enable_medical_rag_var.get()
        
        # 保存配置
        self.save_config()
        return True
    
    def apply_theme(self, theme_data):
        """应用主题配置
        
        Args:
            theme_data (dict): 主题数据
        """
        try:
            # 在这里处理主题应用
            pass
        except Exception as e:
            print(f"应用主题时出错: {e}")

# 单例配置管理器
config_manager = ConfigManager() 