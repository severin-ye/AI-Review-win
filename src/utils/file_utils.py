import os
import re
import shutil

# 遍历文件夹, 生成文件名, 并返回文件名列表
def traverse_folder(folder_path):
    file_name_list = []
    file_type_list = []
    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            file_name_list.append(os.path.splitext(file_name)[0])
            if file_name.endswith(".docx"):
                file_type_list.append('docx')
            elif file_name.endswith(".md"):
                file_type_list.append('md')
                
    return file_name_list , file_type_list



# 根据文件名, 生成路径
def generate_path(file_name):
    # 去除文件名中的不合法字符
    file_name = re.sub(r'[\\/:*?"<>|]', '', file_name)

    # 原文件路径
    begin_path = os.path.join(os.getcwd(), "_1_原文件", f"{file_name}.docx")
    # 中间文件夹路径
    intermediate_folder = os.path.join(os.getcwd(), "hide_file/中间文件", file_name)
    # 无表格文件路径
    no_table = os.path.join(intermediate_folder, f"{file_name}_移除表格_.docx")  # GPT审校的文件
    # 提取的表格文件路径
    path_extract = os.path.join(intermediate_folder, f"{file_name}_提取表格_.docx")
    #word转md文件路径
    md_path = os.path.join(intermediate_folder, f"{file_name}_转为md_.md")
    # AI审校后md文件路径
    ai_path = os.path.join(intermediate_folder, f"{file_name}_审校后_.md")
    # 选择后的md文件路径
    select_path_1 = os.path.join(intermediate_folder, f"{file_name}_审校后_选择后_替换.md")
    select_path_2 = os.path.join(intermediate_folder, f"{file_name}_审校后_选择后_对照.md")
    # md转word文件路径
    word_path_1 = os.path.join(intermediate_folder, f"{file_name}_转为word_替换_.docx")
    word_path_2 = os.path.join(intermediate_folder, f"{file_name}_转为word_对照_.docx")
    # 替换表格文件路径
    final_path_1 = os.path.join(os.getcwd(), "_2_审校后", f"{file_name}_替换_.docx")
    final_path_2 = os.path.join(os.getcwd(), "_2_审校后", f"{file_name}_对照_.docx")

    # 创建所有必要的中间目录
    os.makedirs(intermediate_folder, exist_ok=True)
    os.makedirs(os.path.dirname(begin_path), exist_ok=True)
    os.makedirs(os.path.dirname(final_path_1), exist_ok=True)

    return begin_path, no_table, path_extract, md_path, ai_path, word_path_1, word_path_2, final_path_1, final_path_2, select_path_1, select_path_2

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