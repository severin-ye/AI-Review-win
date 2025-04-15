from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
from openai import OpenAI

from ...models import Event, Character
from ...utils.har_utils import HARProcessor
from .rewriter import GeneratedScene, SceneOutline

@dataclass
class RefinementSuggestion:
    """优化建议"""
    scene_id: str  # 相关场景ID
    content: str  # 建议内容
    category: str  # 建议类别 (plot/character/style/logic)
    importance: float  # 重要性评分
    specific_location: Optional[str] = None  # 具体位置

@dataclass
class RefinedScene:
    """优化后的场景"""
    original: GeneratedScene  # 原始场景
    refined_content: str  # 优化后的内容
    suggestions: List[RefinementSuggestion]  # 优化建议列表
    confidence: float  # 优化后的置信度

class Refiner:
    """Refiner 模块，负责优化和细化剧本内容"""
    
    def __init__(self, llm_client: OpenAI):
        """初始化 Refiner
        
        Args:
            llm_client: OpenAI 客户端
        """
        self.llm = llm_client
        self.har = HARProcessor(llm_client)
        
        # 内容分析提示模板
        self.analysis_prompt = """
请分析以下剧本场景，提出优化建议。重点关注：
1. 情节连贯性和合理性
2. 人物塑造和对话真实性
3. 场景细节和氛围营造
4. 叙事节奏和结构

场景内容：
{content}

支持信息：
{support_text}

请以JSON格式输出建议，例如：
{
    "suggestions": [
        {
            "category": "plot/character/style/logic",
            "content": "具体的优化建议",
            "importance": 0.9,
            "location": "具体位置描述（可选）"
        }
    ]
}
"""

        # 内容优化提示模板
        self.refinement_prompt = """
请根据以下优化建议对剧本内容进行改写。要求：
1. 保持原有内容的核心要素
2. 针对性地解决提出的问题
3. 确保修改后的内容更加流畅自然

原始内容：
{content}

优化建议：
{suggestions}

支持信息：
{support_text}

请生成优化后的完整内容。
"""
    
    def analyze_scene(
        self,
        scene: GeneratedScene,
        support_text: Optional[str] = None
    ) -> List[RefinementSuggestion]:
        """分析场景并生成优化建议
        
        Args:
            scene: 待分析的场景
            support_text: 支持文本
            
        Returns:
            List[RefinementSuggestion]: 优化建议列表
        """
        # 构建提示
        prompt = self.analysis_prompt.format(
            content=scene.content,
            support_text=support_text or ""
        )
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专注于剧本分析和优化的助手。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            suggestions = []
            
            for sugg in result.get("suggestions", []):
                suggestions.append(RefinementSuggestion(
                    scene_id=scene.outline.id,
                    content=sugg["content"],
                    category=sugg["category"],
                    importance=sugg.get("importance", 0.5),
                    specific_location=sugg.get("location")
                ))
            
            return suggestions
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"场景分析失败: {e}")
            return []
    
    def refine_scene(
        self,
        scene: GeneratedScene,
        suggestions: List[RefinementSuggestion],
        support_text: Optional[str] = None
    ) -> RefinedScene:
        """根据优化建议优化场景内容
        
        Args:
            scene: 原始场景
            suggestions: 优化建议列表
            support_text: 支持文本
            
        Returns:
            RefinedScene: 优化后的场景
        """
        if not suggestions:
            return RefinedScene(
                original=scene,
                refined_content=scene.content,
                suggestions=[],
                confidence=scene.confidence
            )
        
        # 构建提示
        prompt = self.refinement_prompt.format(
            content=scene.content,
            suggestions="\n".join(
                f"{i+1}. [{s.category}] {s.content}" + 
                (f" ({s.specific_location})" if s.specific_location else "")
                for i, s in enumerate(suggestions)
            ),
            support_text=support_text or ""
        )
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专注于剧本优化和改写的助手。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 获取优化后的内容
        refined_content = response.choices[0].message.content
        
        # 使用 HAR 进行事实验证
        if support_text:
            har_result = self.har.process(refined_content, support_text)
            refined_content = har_result.refined_text
            confidence = har_result.confidence
        else:
            confidence = 0.8  # 默认置信度
        
        return RefinedScene(
            original=scene,
            refined_content=refined_content,
            suggestions=suggestions,
            confidence=confidence
        )
    
    def refine_script(
        self,
        scenes: List[GeneratedScene],
        support_text: Optional[str] = None
    ) -> List[RefinedScene]:
        """优化完整剧本
        
        Args:
            scenes: 场景列表
            support_text: 支持文本
            
        Returns:
            List[RefinedScene]: 优化后的场景列表
        """
        refined_scenes = []
        
        for scene in scenes:
            # 分析场景并生成优化建议
            suggestions = self.analyze_scene(scene, support_text)
            
            # 根据建议优化场景
            refined = self.refine_scene(scene, suggestions, support_text)
            refined_scenes.append(refined)
        
        return refined_scenes 