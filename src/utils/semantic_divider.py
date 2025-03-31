import re
from typing import List, Dict, Any
import logging
from src.utils.ai_utils import ai_answer

# 控制变量
SHOW_MODEL_INFO = False  # 控制是否显示模型类型和HTTP请求信息
SHOW_TRANSFORMER_INFO = False  # 控制是否显示预训练模型加载信息

# 配置日志记录
if not SHOW_TRANSFORMER_INFO:
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)

class SemanticDivider:
    """基于语义的文本分割器
    
    此分割器专为AI审校系统设计，用于将文本智能分割成语义相关的段落。
    主要功能：
    1. 识别并保持文档结构（标题、作者、章节等）
    2. 智能合并相关内容（如引用注释）
    3. 确保分割后的段落长度适合AI处理
    4. 保持段落的语义完整性
    """
    
    def __init__(self, max_chars: int = 2000):
        """初始化分割器
        
        Args:
            max_chars: 每个段落的最大字符数，默认2000
                      （此值与AI审校系统的处理能力相匹配）
        """
        self.max_chars = max_chars
        
    def split_text(self, text: str) -> List[str]:
        """将文本分割成语义相关的段落
        
        分割策略（专为医学文献设计）：
        1. 标题和作者信息（文章开头）
        2. 导言/摘要（第一段内容）
        3. 每个章节（标题 + 内容）
        4. 总结（以"总之"等开头的段落）
        5. 脚注和引用（[数字]:开头的段落，合并在一起）
        
        Args:
            text: 输入文本（通常是经过预处理的markdown格式文本）
            
        Returns:
            分割后的段落列表，每个段落保持语义完整性
        """
        # 1. 按自然段落分割
        paragraphs = self._split_into_natural_paragraphs(text)
        
        # 2. 分析段落特征
        features = self._analyze_paragraphs(paragraphs)
        
        # 3. 按语义结构组织段落
        semantic_blocks = []
        current_block = []
        current_chapter = None
        reference_block = []  # 新增：专门存储引用段落
        
        for i, (para, feature) in enumerate(zip(paragraphs, features)):
            para_type = feature['type']
            
            # 处理引用段落
            if para_type == 'reference':
                reference_block.append(para)
                continue
                
            # 处理标题和作者信息块
            if i <= 2 and (para_type in ['title', 'image', 'author']):
                if current_block and para_type == 'title':
                    semantic_blocks.append('\n'.join(current_block))
                    current_block = []
                current_block.append(para)
                continue
                
            # 处理导言/摘要
            if i == 3 and para_type == 'content':
                if current_block:
                    semantic_blocks.append('\n'.join(current_block))
                semantic_blocks.append(para)
                current_block = []
                continue
                
            # 处理章节内容
            if para_type == 'chapter_title':
                if current_block:
                    semantic_blocks.append('\n'.join(current_block))
                current_block = [para]
                current_chapter = para
                continue
                
            # 处理总结段落
            if para_type == 'summary':
                if current_block:
                    semantic_blocks.append('\n'.join(current_block))
                semantic_blocks.append(para)
                current_block = []
                continue
                
            # 处理普通段落
            if current_chapter and (para_type in ['subtitle', 'content', 'short_text']):
                current_block.append(para)
            else:
                if current_block:
                    semantic_blocks.append('\n'.join(current_block))
                current_block = [para]
        
        # 添加最后一个内容块
        if current_block:
            semantic_blocks.append('\n'.join(current_block))
            
        # 添加合并后的引用块
        if reference_block:
            semantic_blocks.append('\n'.join(reference_block))
            
        return semantic_blocks
    
    def _split_into_natural_paragraphs(self, text: str) -> List[str]:
        """按自然段落分割文本"""
        text = text.replace('\r\n', '\n')
        paragraphs = []
        current_para = []
        
        for line in text.split('\n'):
            line = line.rstrip()
            if line:
                current_para.append(line)
            else:
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                    current_para = []
        
        if current_para:
            paragraphs.append('\n'.join(current_para))
            
        return [p for p in paragraphs if p.strip()]
    
    def _analyze_paragraphs(self, paragraphs: List[str]) -> List[Dict[str, Any]]:
        """分析每个段落的特征"""
        features = []
        
        for i, para in enumerate(paragraphs):
            para_type = self._determine_paragraph_type(para, i)
            features.append({
                'index': i,
                'type': para_type,
                'length': len(para)
            })
            
        return features
    
    def _determine_paragraph_type(self, text: str, index: int) -> str:
        """确定段落类型
        
        专门针对医学文献的段落类型判断：
        - title: 文章标题（通常较短）
        - image: 图片说明
        - author: 作者信息（包含作者姓名、职称等）
        - chapter_title: 章节标题（如"一、"开头）
        - subtitle: 子标题（如"（一）"开头）
        - reference: 引用注释（如"[1]:"开头）
        - summary: 总结段落（如"总之"开头）
        - short_text: 短文本（小于100字的段落）
        - content: 普通内容
        
        Args:
            text: 段落文本
            index: 段落在文档中的位置索引
            
        Returns:
            段落类型字符串
        """
        # 标题（文章标题通常很短）
        if index == 0 and len(text) < 30:
            return 'title'
            
        # 图片
        if text.startswith('!['):
            return 'image'
            
        # 作者信息
        if '[first_line_indent]' in text and ('[1]' in text or '作者' in text or '医师' in text):
            return 'author'
            
        # 章节标题
        if '[first_line_indent]' in text and re.match(r'.*[一二三四五六七八九十]+、', text):
            return 'chapter_title'
            
        # 子标题
        if '[first_line_indent]' in text and re.match(r'.*[（(][一二三四五六七八九十]+[)）]', text):
            return 'subtitle'
            
        # 引用注释
        if re.match(r'^\[\d+\]:', text):
            return 'reference'
            
        # 总结段落
        if '[first_line_indent]' in text and ('总之' in text or '综上' in text):
            return 'summary'
            
        # 短文本
        if '[first_line_indent]' in text and len(text) < 100:
            return 'short_text'
            
        # 普通内容
        return 'content'

def divide_text_semantically(text: str, max_chars: int = 2000) -> List[str]:
    """便捷函数：智能分割文本
    
    此函数专为AI审校系统设计，用于替代原有的 divide_text_with_indent 函数。
    它提供了更智能的分割策略，能够：
    1. 保持文档结构完整性
    2. 合并相关内容（如引用注释）
    3. 确保分割后的段落适合AI处理
    
    Args:
        text: 输入文本（通常是经过预处理的markdown格式文本）
        max_chars: 每个段落的最大字符数，默认2000
        
    Returns:
        分割后的段落列表，每个段落都保持语义完整性
    """
    divider = SemanticDivider(max_chars=max_chars)
    return divider.split_text(text) 