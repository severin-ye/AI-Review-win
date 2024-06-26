import os
import time
from time_lock import check_date
check_date()

def delete_files_and_folders_in_directory(directory_path):
    # 出错的文件名和文件夹名列表
    error_names = []

    # 检查路径是否存在
    if not os.path.exists(directory_path):
        print(f"'{directory_path}' 不存在.")
        return error_names

    if not os.path.isdir(directory_path):
        print(f"'{directory_path}' 不是一个文件夹.")
        return error_names

    # 遍历文件夹中的所有文件和子文件夹
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                os.remove(file_path)
                print(f"'{file_path}' 已被删除.")
            except Exception as e:
                print(f"删除 '{file_path}' 时出错: {e}")
                error_names.append(file_path)

        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                os.rmdir(dir_path)
                if os.path.isdir(dir_path):  # 检查文件夹是否真的被删除
                    raise Exception("文件夹未完全删除")
                print(f"'{dir_path}' 已被删除.")
            except Exception as e:
                print(f"删除 '{dir_path}' 时出错: {e}")
                error_names.append(dir_path)

    return error_names

# 需要删除文件的文件夹列表
directories_to_clean = [r"_1_原文件", r"_2_审校后", r"hide_file\中间文件"]
all_error_names = []

for dir_path in directories_to_clean:
    error_names = delete_files_and_folders_in_directory(dir_path)
    all_error_names.extend(error_names)

# 检查是否有删除失败的文件或文件夹
if not all_error_names:
    print("已删除所有文档, 无需其他操作")
else:
    print("以下文件或文件夹删除失败:")
    for name in all_error_names:
        print(name)
    print("其他文件或文件夹已删除")
print("程序将在10秒后自动关闭...")

time.sleep(10)
