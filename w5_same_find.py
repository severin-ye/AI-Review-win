import re

# 配置变量
same_words = 8
# 调整正则表达式以保留分割符号
split_symbols = r'(?<=\n)|(?<=。)|(?<=？)|(?<=！)|(?<=；)|(?<=，)'

# 分割文本函数，修改以保留分割符号
def split_text(text, symbols=split_symbols):
    # 使用findall代替split，以便保留分割符号
    return [s for s in re.findall(r'[^。\n？！；，]+[。\n？！；，]?', text)]

# 查找最长公共子串的长度
def longest_common_substring_length(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    longest = 0
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0 or j == 0:
                dp[i][j] = 0
            elif s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                longest = max(longest, dp[i][j])
            else:
                dp[i][j] = 0
    return longest

# 主函数
def find_diff_sentences(a, b):
    sentences_a = split_text(a)
    sentences_b = split_text(b)
    
    diff_sentences = []
    matched_a = set()  # 记录已匹配的A中的句子索引
    matched_b = set()  # 记录已匹配的B中的句子索引

    for i, sentence_a in enumerate(sentences_a):
        for j, sentence_b in enumerate(sentences_b):
            # 如果这两个句子已经被匹配过，跳过
            if i in matched_a or j in matched_b:
                continue
            
            if longest_common_substring_length(sentence_a, sentence_b) >= same_words and sentence_a != sentence_b: # 如果两个句子的最长公共子串长度大于等于8，且两个句子不相等
                diff_sentences.append((sentence_a, sentence_b))
                matched_a.add(i)  # 记录A中的句子已匹配
                matched_b.add(j)  # 记录B中的句子已匹配
                break  # 找到匹配后即停止当前循环，以防一个句子匹配多次
    
    return diff_sentences

# 测试数据
if __name__ == "__main__":
    
    a = "今天天气不错。\n我们去公园玩。还有什么事情要做吗？"
    b = "今天天气真好。\n我们去公园玩。还有什么事情要做吗."

    # 执行函数
    diff_sentences = find_diff_sentences(a, b)
    for pair in diff_sentences:
        print(f"A中的句子：{pair[0]}\nB中的句子：{pair[1]}\n")






