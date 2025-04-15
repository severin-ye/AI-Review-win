import re
import os
import shutil
from .semantic_divider import divide_text_semantically
import difflib

# ANSI颜色代码
RED = "\033[91m"      # 保留但不用于diff
RESET = "\033[0m"

# 差异对比的颜色方案（8种协调的颜色）
DIFF_COLORS = [
    "\033[38;5;220m",  # 金黄色
    "\033[38;5;39m",   # 天蓝色
    "\033[38;5;48m",   # 翠绿色
    "\033[38;5;147m",  # 淡紫色
    "\033[38;5;208m",  # 橙色
    "\033[38;5;81m",   # 青蓝色
    "\033[38;5;184m",  # 淡黄色
    "\033[38;5;141m",  # 紫罗兰色
]

def highlight_text_segment(full_text: str, target_text: str) -> str:
    """在完整文本中高亮显示目标文本段落
    
    Args:
        full_text: 完整的文本内容
        target_text: 需要高亮显示的文本段落
        
    Returns:
        处理后的带有高亮的文本
    """
    if not target_text or not full_text:
        return full_text
        
    # 清理文本，移除多余的空白字符
    target_text = target_text.strip()
    
    # 使用正则表达式替换，确保精确匹配
    pattern = re.escape(target_text)
    highlighted_text = re.sub(
        pattern,
        f'{RED}\\g<0>{RESET}',  # 本段原文中的标注仍使用红色
        full_text
    )
    
    return highlighted_text

def highlight_diff_pairs(original_text: str, revised_text: str) -> tuple[str, str]:
    """对比两段文本并用不同颜色标注差异部分
    
    Args:
        original_text: 原始文本
        revised_text: 修订后的文本
        
    Returns:
        tuple: (带颜色标注的原始文本, 带颜色标注的修订文本)
    """
    # 清理文本
    original_text = original_text.strip()
    revised_text = revised_text.strip()
    
    # 将文本分割成单词列表
    def split_text(text):
        # 保留标点符号作为单独的token
        return [t for t in re.findall(r'[\w]+|[^\w\s]', text)]
    
    original_words = split_text(original_text)
    revised_words = split_text(revised_text)
    
    # 使用difflib找出差异
    matcher = difflib.SequenceMatcher(None, original_words, revised_words)
    
    # 构建带颜色的文本
    colored_original = []
    colored_revised = []
    color_index = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # 相同部分，不加颜色
            colored_original.extend(original_words[i1:i2])
            colored_revised.extend(revised_words[j1:j2])
        else:
            # 不同部分，使用相同颜色标注对应的修改
            color = DIFF_COLORS[color_index % len(DIFF_COLORS)]
            if tag in ('replace', 'delete'):
                colored_original.extend([f"{color}{w}{RESET}" for w in original_words[i1:i2]])
            if tag in ('replace', 'insert'):
                colored_revised.extend([f"{color}{w}{RESET}" for w in revised_words[j1:j2]])
            if tag != 'equal':
                color_index += 1
    
    # 重新组合文本
    return ' '.join(colored_original), ' '.join(colored_revised)

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
