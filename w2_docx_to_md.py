import os
import pypandoc
from docx import Document

def delete_existing_files(folder, exclude_files):
    for file_name in os.listdir(folder):
        file_path = os.path.join(folder, file_name)
        if file_name not in exclude_files and os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")

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
        if line.strip() != "":
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

def convert_md_to_docx(input_md_path, output_docx_path):
    input_md_path = os.path.normpath(input_md_path)
    output_docx_path = os.path.normpath(output_docx_path)

    output = pypandoc.convert_file(input_md_path, 'docx', outputfile=output_docx_path)
    
    print("Word文档格式转换成功")
    return output

if __name__ == '__main__':
    test_folder = 'Doc_conver_test'
    test_files = os.listdir(test_folder)

    for file_name in test_files:
        source_file = os.path.join(test_folder, file_name)
        if file_name.endswith('.docx'):
            delete_existing_files(test_folder, [file_name])

            output_md_file = os.path.splitext(source_file)[0] + '.md'
            output_docx_file = os.path.splitext(source_file)[0] + '_converted.docx'
            
            convert_file_md(source_file, output_md_file)
            add_indents_to_md(output_md_file, source_file)
            convert_md_to_docx(output_md_file, output_docx_file)
