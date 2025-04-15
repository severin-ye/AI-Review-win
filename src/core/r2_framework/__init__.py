from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
from openai import OpenAI

from ...models import Event, Character, CausalGraph
from ...utils.har_utils import HARProcessor
from ...utils.cpc_utils import CPCProcessor
from .reader import Reader
from .rewriter import Rewriter, GeneratedScene
from .refiner import Refiner, RefinedScene

@dataclass
class R2Result:
    """R² 框架处理结果"""
    events: List[Event]  # 提取的事件列表
    characters: List[Character]  # 提取的角色列表
    causal_graph: CausalGraph  # 构建的因果图
    generated_scenes: List[GeneratedScene]  # 生成的场景列表
    refined_scenes: List[RefinedScene]  # 优化后的场景列表
    confidence: float  # 整体置信度

class R2Framework:
    """R² (Read-Rewrite-Refine) 框架
    
    一个基于因果推理的剧本生成和优化框架，包含三个核心组件：
    1. Reader: 从文本中提取事件和角色信息
    2. Rewriter: 基于因果图生成剧本内容
    3. Refiner: 优化和细化剧本内容
    """
    
    def __init__(self, llm_client: OpenAI):
        """初始化 R² 框架
        
        Args:
            llm_client: OpenAI 客户端
        """
        self.llm = llm_client
        self.reader = Reader(llm_client)
        self.rewriter = Rewriter(llm_client)
        self.refiner = Refiner(llm_client)
        self.cpc = CPCProcessor(llm_client)
    
    def process(
        self,
        text: str,
        support_text: Optional[str] = None
    ) -> R2Result:
        """执行完整的处理流程
        
        Args:
            text: 输入文本
            support_text: 支持文本（用于事实验证）
            
        Returns:
            R2Result: 处理结果
        """
        # 1. 读取阶段：提取事件和角色信息
        events = self.reader.extract_events(text, support_text)
        characters = self.reader.extract_characters(text)
        
        # 2. 构建因果图
        causal_graph = self.reader.build_causal_graph(events)
        
        # 3. 生成剧本
        generated_scenes = self.rewriter.generate_script(
            causal_graph,
            characters,
            support_text
        )
        
        # 4. 优化剧本
        refined_scenes = self.refiner.refine_script(
            generated_scenes,
            support_text
        )
        
        # 5. 计算整体置信度
        confidence = sum(
            scene.confidence for scene in refined_scenes
        ) / len(refined_scenes) if refined_scenes else 0.0
        
        return R2Result(
            events=events,
            characters=characters,
            causal_graph=causal_graph,
            generated_scenes=generated_scenes,
            refined_scenes=refined_scenes,
            confidence=confidence
        )
    
    def process_batch(
        self,
        texts: List[str],
        support_text: Optional[str] = None
    ) -> List[R2Result]:
        """批量处理多个文本
        
        Args:
            texts: 输入文本列表
            support_text: 支持文本
            
        Returns:
            List[R2Result]: 处理结果列表
        """
        return [
            self.process(text, support_text)
            for text in texts
        ]
    
    def export_results(
        self,
        result: R2Result,
        output_format: str = "json"
    ) -> str:
        """导出处理结果
        
        Args:
            result: 处理结果
            output_format: 输出格式 ("json" 或 "text")
            
        Returns:
            str: 格式化的输出内容
        """
        if output_format == "json":
            return json.dumps({
                "events": [event.to_dict() for event in result.events],
                "characters": [char.to_dict() for char in result.characters],
                "causal_graph": result.causal_graph.to_dict(),
                "scenes": [
                    {
                        "original": {
                            "outline": scene.original.outline.__dict__,
                            "content": scene.original.content,
                            "confidence": scene.original.confidence
                        },
                        "refined": {
                            "content": scene.refined_content,
                            "suggestions": [s.__dict__ for s in scene.suggestions],
                            "confidence": scene.confidence
                        }
                    }
                    for scene in result.refined_scenes
                ],
                "confidence": result.confidence
            }, ensure_ascii=False, indent=2)
        else:
            # 文本格式输出
            output = []
            output.append("# 事件列表")
            for event in result.events:
                output.append(str(event))
            
            output.append("\n# 角色列表")
            for char in result.characters:
                output.append(str(char))
            
            output.append("\n# 场景列表")
            for scene in result.refined_scenes:
                output.append(f"\n## {scene.original.outline.title}")
                output.append(f"目标: {scene.original.outline.goal}")
                output.append(f"描述: {scene.original.outline.description}")
                output.append("\n### 优化建议")
                for sugg in scene.suggestions:
                    output.append(f"- [{sugg.category}] {sugg.content}")
                output.append("\n### 最终内容")
                output.append(scene.refined_content)
            
            output.append(f"\n总体置信度: {result.confidence:.2f}")
            
            return "\n".join(output) 