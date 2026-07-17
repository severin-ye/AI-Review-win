"""
配置模块加载测试
"""

import sys
import os

try:
    # 导入配置模块
    from config import (
        path_manager, 
        config_manager, 
        theme_config, 
        has_review_table, 
        module_type,
        openai_api_key,
        tyqw_api_key,
        prompt,
        MODULE_LIST
    )
    
    # 测试配置是否正确加载
    print("-" * 50)
    print("配置模块加载测试")
    print("-" * 50)
    print(f"模块类型: {module_type}")
    print(f"模块列表: {MODULE_LIST}")
    print(f"审校表格: {has_review_table}")
    print(f"配置文件路径: {path_manager.config_file}")
    print(f"主题文件路径: {path_manager.theme_file}")
    print("-" * 50)
    print("配置模块加载成功")
    
except Exception as e:
    print(f"配置模块加载失败: {str(e)}")
    import traceback
    traceback.print_exc() 