import re
import os
import shutil
from .semantic_divider import divide_text_semantically


# 分割表格
def table_divider(text):
    divided_contents = []

    above_pattern = re.compile(r'(.*?)Content Above the Table(.*?)(?=Content Above the Table|Content Below the Table|$)', re.DOTALL)
    below_pattern = re.compile(r'Content Below the Table(.*?)(?=Content Above the Table|Content Below the Table|$)', re.DOTALL)

    above_matches = [match.groups() for match in above_pattern.finditer(text)]
    below_matches = [match.group(1) for match in below_pattern.finditer(text)]

    for i, groups in enumerate(above_matches):
        if i == 0 and groups[0].strip():
            divided_contents.extend(groups[0].strip().splitlines())
        divided_contents.append(groups[1].strip())
        if below_matches:
            below_content = below_matches.pop(0).strip()
            divided_contents.extend(below_content.splitlines())

    if not divided_contents:
        divided_contents.extend(text.strip().splitlines())

    print(f"表格分割为{len(divided_contents)}段")

    return divided_contents

def divide_text_with_indent(md_path, max_chars=500, use_semantic=True):
    """分割文本为段落
    
    Args:
        md_path: markdown文件路径
        max_chars: 每个段落的最大字符数
        use_semantic: 是否使用语义分割（默认True）
        
    Returns:
        分割后的段落列表
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        try:
            text = f.read()
            # 首先处理表格
            paragraphs = table_divider(text)
            
            if use_semantic:
                # 将段落合并为完整文本
                full_text = '\n\n'.join(paragraphs)
                # 使用语义分割器重新分割文本
                segments = divide_text_semantically(full_text, max_chars)
                print(f"语义分割共分割为{len(segments)}段")
            else:
                # 使用原始的[first_line_indent]分割方式
                segments = []
                segment = ''
                for paragraph in paragraphs:
                    if paragraph.startswith('[first_line_indent]'):
                        if segment:
                            segments.append(segment)
                        segment = paragraph
                    else:
                        segment += '\n' + paragraph
                if segment:
                    segments.append(segment)
                print(f"根据缩进分割共分割为{len(segments)}段")
            
            return segments
            
        except Exception as e:
            print(f"分割文本时出现错误：{e}")
            return []


if __name__ == '__main__':
    
    test_num = int(input("输入测试编号："))

    if test_num == 1:

        # 测试代码--1
        def create_test_files(test_folder):
            os.makedirs(test_folder, exist_ok=True)
            example_texts = [
                "[first_line_indent]陈华[^1] 张海燕\n\n[first_line_indent]腹腔镜手术可用于治疗卵巢囊肿切除、宫外孕、子宫切除、子宫肌瘤、子宫内膜异位症、盆腔肿物等疾病，是目前妇科常用的手术方式。然而，腹腔镜术后常出现腹胀这一并发症，给患者带来了诸多困扰，如腹胀不适、消化不良、便秘甚至肠梗阻等症状，这不仅影响了患者的生活质量，还可能延长住院时间。那么，为何腹腔镜术后会出现腹胀？腹腔镜术后腹胀有哪些危害？解决腹腔镜术后腹胀的方法又有哪些？针对患者经常提出的疑问，本文将为大家一一解答。\n\n[first_line_indent]一、腹腔镜术后为什么会出现腹胀？",
                "[first_line_indent]这是一个示例文本，包含多个段落。\n\n[first_line_indent]这是第二段，内容较为简短。\n\n[first_line_indent]这是第三段，进一步的示例内容。"
            ]

            for i, text in enumerate(example_texts):
                file_path = os.path.join(test_folder, f'test_file_{i + 1}.md')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)

        test_folder = 'divided_test'
        create_test_files(test_folder)
        test_files = os.listdir(test_folder)

        for file_name in test_files:
            source_file = os.path.join(test_folder, file_name)
            if file_name.endswith('.md'):
                output_file = os.path.splitext(source_file)[0] + '_divided.txt'
                divided_segments = divide_text_with_indent(source_file)
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    for i, segment in enumerate(divided_segments):
                        out_f.write(f"段落 {i + 1}:\n{segment}\n\n")
                print(f"已处理文件: {file_name}, 输出文件: {output_file}")
    
    elif test_num == 2:
        # 测试代码--2
        test_folder = 'divided_test_2'

        # 删除之前测试产生的文件（保留源文件）
        if os.path.exists(test_folder):
            for item in os.listdir(test_folder):
                item_path = os.path.join(test_folder, item)
                if os.path.isfile(item_path) and not item_path.endswith('.md'):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            print(f"已删除{test_folder}中除源文件外的所有文件")

        # 创建测试文件夹并生成新的测试文件
        def create_test_files(test_folder):
            os.makedirs(test_folder, exist_ok=True)
            example_texts = [
                "[first_line_indent]这是测试文件2的示例文本，包含多个段落。\n\n[first_line_indent]这是第二段，内容较为简短。\n\n[first_line_indent]这是第三段，进一步的示例内容。"
            ]

            for i, text in enumerate(example_texts):
                file_path = os.path.join(test_folder, f'test_file_{i + 1}.md')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)

        create_test_files(test_folder)
        test_files = os.listdir(test_folder)

        for file_name in test_files:
            source_file = os.path.join(test_folder, file_name)
            if file_name.endswith('.md'):
                output_file = os.path.splitext(source_file)[0] + '_divided.txt'
                divided_segments = divide_text_with_indent(source_file)
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    for i, segment in enumerate(divided_segments):
                        out_f.write(f"段落 {i + 1}:\n{segment}\n\n")
                print(f"已处理文件: {file_name}, 输出文件: {output_file}")

    else:
        print("无效的测试编号")
