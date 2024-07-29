import re
import os

# 从配置文件导入配置
max_length = 500  # 假设最大长度为500字符
has_review_table = True  # 假设配置文件中表明有review表格

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

# 以[first_line_indent]占位符分割文本
def divide_text_with_indent(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        try:
            text = f.read()
            paragraphs = table_divider(text)
            
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
        except Exception as e:
            print(f"分割文本时出现错误：{e}")
        
    print(f"根据缩进分割共分割为{len(segments)}段")
    return segments


if __name__ == '__main__':
    
    # 测试代码
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
