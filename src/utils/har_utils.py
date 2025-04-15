from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
from openai import OpenAI

@dataclass
class HARConfig:
    """HAR 算法配置"""
    max_iterations: int = 3  # 最大迭代次数
    min_confidence: float = 0.8  # 最小置信度阈值
    support_text_window: int = 1000  # 支持文本窗口大小

@dataclass
class HARResult:
    """HAR 算法结果"""
    refined_text: str  # 细化后的文本
    confidence: float  # 置信度
    iterations: int  # 迭代次数
    hallucinations: List[Dict[str, Any]]  # 检测到的幻觉列表

class HARProcessor:
    """幻觉感知细化（Hallucination-aware Refinement）处理器"""
    
    def __init__(self, llm_client: OpenAI, config: Optional[HARConfig] = None):
        """初始化 HAR 处理器
        
        Args:
            llm_client: OpenAI 客户端
            config: HAR 配置
        """
        self.llm = llm_client
        self.config = config or HARConfig()
        
        # 幻觉检测提示模板
        self.detection_prompt = """
请仔细分析以下文本，找出可能的幻觉内容（与事实不符、逻辑矛盾或缺乏支持的内容）。
对于每个发现的幻觉，请提供：
1. 幻觉文本位置
2. 原因说明
3. 修改建议

文本内容：
{text}

支持文本（用于事实核验）：
{support_text}

请以JSON格式输出，例如：
{{
    "hallucinations": [
        {{
            "text": "发现的幻觉文本",
            "position": "开始位置,结束位置",
            "reason": "为什么认为这是幻觉",
            "suggestion": "建议的修改内容"
        }}
    ]
}}
"""

        # 细化提示模板
        self.refinement_prompt = """
请根据以下信息对文本进行改写和优化：

原始文本：
{text}

需要修改的问题：
{issues}

相关上下文：
{context}

请生成修改后的完整文本，确保：
1. 修正所有指出的问题
2. 保持文本流畅性和连贯性
3. 与上下文保持一致

输出格式：
{{
    "refined_text": "修改后的文本",
    "confidence": 0.95  // 对修改结果的置信度（0-1）
}}
"""
    
    def detect_hallucination(self, text: str, support_text: str) -> Dict[str, Any]:
        """检测文本中的幻觉内容
        
        Args:
            text: 待检测文本
            support_text: 支持文本（用于事实核验）
            
        Returns:
            Dict: 检测结果
        """
        # 构建提示
        prompt = self.detection_prompt.format(
            text=text,
            support_text=support_text
        )
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4",  # 使用 GPT-4 以获得更好的分析能力
            messages=[
                {"role": "system", "content": "你是一个专注于文本分析和事实核验的助手。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 解析响应
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except json.JSONDecodeError:
            return {"hallucinations": []}
    
    def refine_content(self, text: str, issues: List[Dict[str, Any]], context: str) -> Dict[str, Any]:
        """根据检测到的问题优化内容
        
        Args:
            text: 原始文本
            issues: 检测到的问题列表
            context: 相关上下文
            
        Returns:
            Dict: 优化结果
        """
        # 构建提示
        prompt = self.refinement_prompt.format(
            text=text,
            issues=json.dumps(issues, ensure_ascii=False, indent=2),
            context=context
        )
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专注于文本优化和改写的助手。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 解析响应
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except json.JSONDecodeError:
            return {
                "refined_text": text,
                "confidence": 0.0
            }
    
    def process(self, text: str, support_text: str) -> HARResult:
        """执行 HAR 算法的完整流程
        
        Args:
            text: 待处理文本
            support_text: 支持文本
            
        Returns:
            HARResult: 处理结果
        """
        current_text = text
        all_hallucinations = []
        iterations = 0
        
        while iterations < self.config.max_iterations:
            # 检测幻觉
            detection_result = self.detect_hallucination(current_text, support_text)
            hallucinations = detection_result.get("hallucinations", [])
            
            # 如果没有检测到幻觉，或者迭代次数达到上限，结束处理
            if not hallucinations:
                break
            
            # 记录检测到的幻觉
            all_hallucinations.extend(hallucinations)
            
            # 优化内容
            refinement_result = self.refine_content(
                current_text,
                hallucinations,
                support_text
            )
            
            # 更新当前文本
            current_text = refinement_result.get("refined_text", current_text)
            confidence = refinement_result.get("confidence", 0.0)
            
            # 如果置信度达到阈值，结束处理
            if confidence >= self.config.min_confidence:
                break
            
            iterations += 1
        
        return HARResult(
            refined_text=current_text,
            confidence=confidence,
            iterations=iterations,
            hallucinations=all_hallucinations
        ) 