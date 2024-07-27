import os
import pypandoc
from docx import Document
from docx.shared import Pt
import shutil
import logging

# 删除指定文件夹中不在排除列表中的文件和文件夹
def delete_existing_files_and_folders(folder, exclude_files):
    try:
        for item_name in os.listdir(folder):  # 列出文件夹中的所有文件和文件夹
            item_path = os.path.join(folder, item_name)
            if item_name not in exclude_files:
                if os.path.isfile(item_path):  # 检查是否为文件
                    os.remove(item_path)  # 删除文件
                    logging.info(f"Deleted file: {item_path}")
                elif os.path.isdir(item_path):  # 检查是否为文件夹
                    shutil.rmtree(item_path)  # 删除文件夹及其所有内容
                    logging.info(f"Deleted folder: {item_path}")
    except Exception as e:
        logging.error(f"Error deleting files and folders: {e}")

def convert_file_md(source_file, output_file):
    output_format = 'markdown'

    extract_media_path = os.path.splitext(output_file)[0] + '_media'
    extract_media_path = os.path.join(extract_media_path)
    extra_args = ['--extract-media=' + extract_media_path, '--toc', '--standalone']

    output = pypandoc.convert_file(source_file, to=output_format, outputfile=output_file, extra_args=extra_args)
    replace_backslashes_in_md(output_file)

    print("MD文件格式转换成功")

def replace_backslashes_in_md(md_file_path):
    with open(md_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    updated_content = content.replace('\\', '/')
    with open(md_file_path, 'w', encoding='utf-8') as file:
        file.write(updated_content)

def add_indents_to_md(md_file_path, docx_file_path):
    with open(md_file_path, 'r', encoding='utf-8') as file:
        md_content = file.readlines()

    docx = Document(docx_file_path)
    indents = []
    for para in docx.paragraphs:
        left_indent = para.paragraph_format.left_indent.pt if para.paragraph_format.left_indent else 0
        first_line_indent = para.paragraph_format.first_line_indent.pt if para.paragraph_format.first_line_indent else 0
        hanging_indent = -first_line_indent if first_line_indent < 0 else 0
        indents.append((left_indent, first_line_indent, hanging_indent))

    new_md_content = []
    indent_idx = 0
    for line in md_content:
        if line.strip() != "" and not line.startswith("[^"):  # 忽略注解行
            if indent_idx < len(indents):
                left_indent, first_line_indent, hanging_indent = indents[indent_idx]
                indent_text = ''
                if left_indent > 0:
                    indent_text += f'[left_indent: {left_indent}pt]'
                if first_line_indent > 0:
                    indent_text += f'[first_line_indent: {first_line_indent}pt]'
                if hanging_indent > 0:
                    indent_text += f'[hanging_indent: {hanging_indent}pt]'
                new_md_content.append(indent_text + line)
                indent_idx += 1
            else:
                print(f"Warning: More paragraphs in Markdown than in DOCX. Skipping indent for line: {line.strip()}")
                new_md_content.append(line)
        else:
            new_md_content.append(line)

    with open(md_file_path, 'w', encoding='utf-8') as file:
        file.writelines(new_md_content)
    
    # Debugging: Print the updated Markdown content with indent placeholders
    print("\nUpdated Markdown content with indent placeholders:\n")
    for line in new_md_content:
        print(line)

def convert_md_to_docx(input_md_path, output_docx_path):
    input_md_path = os.path.normpath(input_md_path)
    output_docx_path = os.path.normpath(output_docx_path)

    output = pypandoc.convert_file(input_md_path, 'docx', outputfile=output_docx_path)
    
    print("Word文档格式转换成功")
    return output

def replace_indent_placeholders(docx_file_path):
    doc = Document(docx_file_path)
    for para in doc.paragraphs:
        if '[left_indent:' in para.text:
            text = para.text
            left_indent = first_line_indent = hanging_indent = 0
            if '[left_indent:' in text:
                left_indent = float(text.split('[left_indent:')[1].split('pt]')[0])
                text = text.replace(f'[left_indent: {left_indent}pt]', '')
            if '[first_line_indent:' in text:
                first_line_indent = float(text.split('[first_line_indent:')[1].split('pt]')[0])
                text = text.replace(f'[first_line_indent: {first_line_indent}pt]', '')
            if '[hanging_indent:' in text:
                hanging_indent = float(text.split('[hanging_indent:')[1].split('pt]')[0])
                text = text.replace(f'[hanging_indent: {hanging_indent}pt]', '')
            para.text = text
            if left_indent > 0:
                para.paragraph_format.left_indent = Pt(left_indent)
            if first_line_indent > 0:
                para.paragraph_format.first_line_indent = Pt(first_line_indent)
            if hanging_indent > 0:
                para.paragraph_format.hanging_indent = Pt(hanging_indent)
            print(f"Replaced indent: left_indent={left_indent}, first_line_indent={first_line_indent}, hanging_indent={hanging_indent} for paragraph: {para.text}")
            # Debugging: Print the final paragraph format
            print(f"Final paragraph format: left_indent={para.paragraph_format.left_indent}, first_line_indent={para.paragraph_format.first_line_indent}, hanging_indent={para.paragraph_format.hanging_indent}")
    doc.save(docx_file_path)
    print(f"Indent placeholders replaced in {docx_file_path}")

if __name__ == '__main__':
    test_folder = 'Doc_conver_test'
    test_files = os.listdir(test_folder)

    for file_name in test_files:
        source_file = os.path.join(test_folder, file_name)
        if file_name.endswith('.docx') and not file_name.endswith('_converted.docx'):  # 仅处理未转换的DOCX文件
            exclude_files = [file_name]  # 保留源文件
            delete_existing_files_and_folders(test_folder, exclude_files)  # 删除其他文件和文件夹

            output_md_file = os.path.splitext(source_file)[0] + '.md'
            output_docx_file = os.path.splitext(source_file)[0] + '_converted.docx'
            
            convert_file_md(source_file, output_md_file)
            add_indents_to_md(output_md_file, source_file)
            convert_md_to_docx(output_md_file, output_docx_file)
            replace_indent_placeholders(output_docx_file)  # 新增功能: 转换后替换缩进占位符
