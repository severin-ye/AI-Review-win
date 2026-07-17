import os
import re
import shutil
from config import path_manager

# 遍历文件夹, 生成文件名, 并返回文件名列表
def traverse_folder(folder_path):
    file_name_list = []
    file_type_list = []
    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            file_name_list.append(file_name)  # 保留完整文件名（包含扩展名）
            if file_name.endswith(".docx"):
                file_type_list.append('docx')
            elif file_name.endswith(".md"):
                file_type_list.append('md')
                
    return file_name_list , file_type_list



# 根据文件名, 生成路径
def generate_path(file_name):
    """生成路径并确保目录存在"""
    # 确保文件名没有特殊字符
    # 清理文件名中的非法字符
    clean_file_name = re.sub(r'[\\/*?:"<>|]', '_', file_name)
    
    # 分离文件名和扩展名
    base_name, ext = os.path.splitext(clean_file_name)
    
    # 使用路径管理器生成所有相关路径
    # 对于原始文件路径，使用完整文件名（包含扩展名）
    # 对于其他生成的路径，使用没有扩展名的基本文件名
    paths = path_manager.generate_file_paths(clean_file_name, base_name)
    return paths

def remove_middle_folder(file_name):
    # 获取路径
    _, no_table, path_extract, md_path, ai_path, word_path, _ = generate_path(file_name)

    # 删除中间文件夹及其所有内容
    shutil.rmtree(os.path.dirname(no_table), ignore_errors=True)
    shutil.rmtree(os.path.dirname(path_extract), ignore_errors=True)
    shutil.rmtree(os.path.dirname(md_path), ignore_errors=True)
    shutil.rmtree(os.path.dirname(ai_path), ignore_errors=True)
    shutil.rmtree(os.path.dirname(word_path), ignore_errors=True)

    return 0