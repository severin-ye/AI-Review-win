import re
import os
from config import max_length, has_review_table

# 分割表格
def table_divider(text):
    divided_contents = []  # 存储分割后的文本内容

    above_pattern = re.compile(r'(.*?)Content Above the Table(.*?)(?=Content Above the Table|Content Below the Table|$)', re.DOTALL)
    below_pattern = re.compile(r'Content Below the Table(.*?)(?=Content Above the Table|Content Below the Table|$)', re.DOTALL)

    above_matches = [match.groups() for match in above_pattern.finditer(text)]
    below_matches = [match.group(1) for match in below_pattern.finditer(text)]

    for i, groups in enumerate(above_matches):
        # 处理不被定界符包围的文本，并按每一行划分为一个元素
        if i == 0 and groups[0].strip():
            divided_contents.extend(groups[0].strip().splitlines())

        # 处理被定界符包围的文本
        divided_contents.append(groups[1].strip())

        # 处理不被定界符包围的文本，并按每一行划分为一个元素
        if below_matches:
            below_content = below_matches.pop(0).strip()
            divided_contents.extend(below_content.splitlines())

    # 如果没有找到任何表格定界符，将整个原始文本按行分割
    if not divided_contents:
        divided_contents.extend(text.strip().splitlines())

    print(f"表格分割为{len(divided_contents)}段")

    return divided_contents

# 以max_length分割文本
def divide_text(md_path, max_length):
    md_path = md_path
    max_length = int(max_length)
    with open(md_path, 'r', encoding='utf-8') as f:
        try:
            text = f.read()
            # 以表格为单位分割文本
            paragraphs = table_divider(text)
            
            # 以max_length分割文本
            segments = []
            segment = ''
            for paragraph in paragraphs:
                new_segment = segment + ('\n' if segment else '') + paragraph
                if len(new_segment) > max_length:
                    if segment:
                        segments.append(segment)
                    segment = paragraph
                else:
                    segment = new_segment

            if segment:
                segments.append(segment)
        except Exception as e:
            print(f"分割文本时出现错误：{e}")
        
    f.close()
    print(f"智能分段共分割为{len(segments)}段")
    return segments








