import os
from src.security.time_lock import check_date
from config import path_manager
check_date()

def delete_files_and_folders_in_directory(directory_path):
    # 出错的文件名和文件夹名列表
    error_names = []

    # 检查路径是否存在
    if not os.path.exists(directory_path):
        return f"'{directory_path}' 不存在."

    if not os.path.isdir(directory_path):
        return f"'{directory_path}' 不是一个文件夹."

    # 遍历文件夹中的所有文件和子文件夹
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                os.remove(file_path)
            except Exception as e:
                error_names.append(file_path)

        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                os.rmdir(dir_path)
                if os.path.isdir(dir_path):  # 检查文件夹是否真的被删除
                    raise Exception("文件夹未完全删除")
            except Exception as e:
                error_names.append(dir_path)

    return error_names

# 获取需要清理的目录路径
directories_to_clean = [
    path_manager.original_files_dir,
    path_manager.reviewed_files_dir,
    path_manager.temp_files_dir
]
all_error_names = []

for dir_path in directories_to_clean:
    error_names = delete_files_and_folders_in_directory(dir_path)
    if isinstance(error_names, str):  # 如果返回错误信息字符串
        all_error_names.append(error_names)
    else:
        all_error_names.extend(error_names)

# 返回清理结果
if not all_error_names:
    result = "已成功清理所有文件！"
else:
    result = "以下文件或文件夹清理失败：\n" + "\n".join(all_error_names)

print(result)  # 为了调试目的保留
