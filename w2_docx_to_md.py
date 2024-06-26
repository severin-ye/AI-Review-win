import os
import pypandoc

def convert_file_md(source_file, output_file):
    output_format = 'markdown'

    # 指定图片的提取路径，这里假设图片存储在与输出文件同名的文件夹中
    extract_media_path = os.path.splitext(output_file)[0] + '_media'
    # 使用 os.path.join 确保路径在不同操作系统上都正确
    extract_media_path = os.path.join(extract_media_path)
    extra_args = ['--extract-media=' + extract_media_path, '--toc', '--standalone']

    output = pypandoc.convert_file(source_file, to=output_format, outputfile=output_file, extra_args=extra_args)

    # 转换完成后，处理生成的 Markdown 文件，替换图片路径中的反斜线
    replace_backslashes_in_md(output_file)

    print("MD文件格式转换成功")

def replace_backslashes_in_md(md_file_path):
    # 读取 Markdown 文件内容
    with open(md_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 替换内容中的反斜线为正斜线
    updated_content = content.replace('\\', '/')
    
    # 将更新后的内容写回文件
    with open(md_file_path, 'w', encoding='utf-8') as file:
        file.write(updated_content)

def convert_md_to_docx(input_md_path, output_docx_path):
    # 将markdown文件转换为docx
    # 为了处理路径问题，我们确保输入和输出路径都是正确的
    input_md_path = os.path.normpath(input_md_path)
    output_docx_path = os.path.normpath(output_docx_path)

    output = pypandoc.convert_file(input_md_path, 'docx', outputfile=output_docx_path)
    
    print("Word文档格式转换成功")
    return output


