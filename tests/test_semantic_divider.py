import unittest
from src.utils.semantic_divider import SemanticDivider

class TestSemanticDivider(unittest.TestCase):
    def setUp(self):
        self.divider = SemanticDivider(max_chars=2000)
        self.test_text = """腹腔镜术后腹胀怎么办？

![陈华](C:/Users/6seve/CodeLib_win/AI-Review-win/hide_file/temp_files/（3月）腹腔镜术后腹胀怎么办？__media/media/image1.png){width="1.3138888888888889in" height="1.9388888888888889in"}

[first_line_indent]陈华[1] 张海燕

[first_line_indent]腹腔镜手术可用于治疗卵巢囊肿切除、宫外孕、子宫切除、子宫肌瘤、子宫内膜异位症、盆腔肿物等疾病，是目前妇科常用的手术方式。然而，腹腔镜术后常出现腹胀这一并发症，给患者带来了诸多困扰，如腹胀不适、消化不良、便秘甚至肠梗阻等症状，这不仅影响了患者的生活质量，还可能延长住院时间。那么，为何腹腔镜术后会出现腹胀？腹腔镜术后腹胀有哪些危害？解决腹腔镜术后腹胀的方法又有哪些？针对患者经常提出的疑问，本文将为大家一一解答。

[first_line_indent]一、腹腔镜术后为什么会出现腹胀？

[first_line_indent]引起腹腔镜术后腹胀的原因主要有以下几个因素：

[first_line_indent]（一）手术过程中通过建立人工气腹和手术通道以获得清晰"术野[2]"，导致腹腔留有二氧化碳气体。

[first_line_indent]（二）术中麻醉药物及术后镇痛泵的使用对胃肠蠕动具有一定的抑制作用，从而可能导致产气增多，进一步加重肠胀气。

[first_line_indent]（三）肠胀气使得肠腔处于膨胀状态，这会降低胃肠蠕动功能。

[first_line_indent]（四）术后切口疼痛，或者患者呻吟、哽咽等不良情绪可能导致吞咽空气。

[first_line_indent]（五）电解质失衡。

[first_line_indent]二、腹腔镜术后腹胀有哪些危害？

[first_line_indent]（一）消化不良

[first_line_indent]肠动力减弱导致食物排空慢，胃排入肠道的食物残渣在肠道内堆积，可能引起腹胀、腹痛等消化不良症状。

[first_line_indent]（二）腹胀不适

[first_line_indent]患者腹腔镜术后逐渐出现明显的腹胀，伴有胀痛，甚至因手术体位和残留的二氧化碳气体刺激膈肌，引起肩、背部、肋骨的酸痛。

[first_line_indent]（三）便秘

[first_line_indent]由于肠动力减弱，食物残渣在结肠停留的时间延长，水分被更多地吸收，导致大便干结，增加便秘的风险。

[first_line_indent]（四）肠梗阻

[first_line_indent]当肠动力极度减弱时，肠壁肌群功能异常，肠道内的食物残渣无法正常排空，若不及时干预，可能会出现肠梗阻的情况。

[first_line_indent]三、如何解决腹腔镜术后腹胀的问题？

[first_line_indent]腹腔镜术后腹胀是由于术后患者气血不足，胃肠蠕动功能减弱所致。我们采用针灸结合脏腑推拿的方式取得了良好的疗效，具体方法如下。

（一）针灸疗：

[first_line_indent]针灸选穴足三里、三阴交、上巨虚等穴位，这些穴位配合使用可增强胃肠蠕动功能，促使术后排气排便，从而有助于缓解患者的腹胀症状。三阴交属于足太阴脾经穴位，还可调理脾胃虚弱。

[first_line_indent]（二）脏腑推拿手法

[first_line_indent]通过脏腑推拿手法调整脏腑的功能状态，促使内脏韧带的伸展和缓解张力，促进胃肠蠕动功能。

[first_line_indent]（三）饮食护理

[first_line_indent]术前指导患者食用清淡饮食，忌食油腻及容易产生气体的食物；术后指导患者食用清淡流质饮食。

[first_line_indent]总之，腹腔镜术后腹胀是常见的并发症之一，但通过针灸结合脏腑手法的调理，可以缓解腹胀症状，提高患者的生活质量。当然，在进行针灸和脏腑手法治疗时，应该选择专业的中医师进行操作，以确保治疗效果和安全性。

[1]: 陈华，医学硕士，副主任医师，河北省沧州中西医结合医院推拿康复科主任。现任河北省中医康复学会推拿分会副主任委员，河北省社区中西医结合康复医学会副主任委员。

[2]: 术野是医学术语，就是指手术时视力所及的范围，术野与视野、照射野等是一样的概念。"""

    def test_semantic_division(self):
        """测试语义分割功能"""
        print("\n" + "=" * 50)
        print("测试语义分割功能")
        print("=" * 50 + "\n")

        # 1. 获取自然段落
        paragraphs = self.divider._split_into_natural_paragraphs(self.test_text)
        
        print(f"原始自然段落（共 {len(paragraphs)} 段）:")
        for i, para in enumerate(paragraphs, 1):
            print("-" * 50)
            print(f"段落 {i} ({len(para)}字):")
            print(para)
            print("-" * 50)

        # 2. 分析段落特征
        features = self.divider._analyze_paragraphs(paragraphs)
        
        print("\n段落分析结果:")
        print("-" * 50)
        for i, feature in enumerate(features, 1):
            print(f"段落 {i}:")
            print(f"类型: {feature['type']}")
            print("-" * 50)

        # 3. 获取最终分割结果
        semantic_blocks = self.divider.split_text(self.test_text)
        
        print("\n语义分割结果:")
        print("-" * 50)
        for i, block in enumerate(semantic_blocks, 1):
            print(f"语义块 {i} ({len(block)}字):")
            print(block)
            print("-" * 50)

        # 4. 验证结果
        for block in semantic_blocks:
            self.assertLessEqual(len(block), self.divider.max_chars)

if __name__ == '__main__':
    unittest.main() 