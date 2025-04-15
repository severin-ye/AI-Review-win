from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
from openai import OpenAI

from ...models import Event, Character, CausalGraph
from ...utils.har_utils import HARProcessor

@dataclass
class SceneOutline:
    """场景大纲"""
    id: str  # 场景ID
    title: str  # 场景标题
    events: List[Event]  # 相关事件
    characters: List[Character]  # 相关角色
    goal: str  # 场景目标
    description: str  # 场景描述
    importance: float  # 重要性评分

@dataclass
class GeneratedScene:
    """生成的场景"""
    outline: SceneOutline  # 场景大纲
    content: str  # 场景内容
    confidence: float  # 生成置信度

class Rewriter:
    """Rewriter 模块，负责生成剧本内容"""
    
    def __init__(self, llm_client: OpenAI):
        """初始化 Rewriter
        
        Args:
            llm_client: OpenAI 客户端
        """
        self.llm = llm_client
        self.har = HARProcessor(llm_client)
        
        # 场景大纲生成提示模板
        self.outline_generation_prompt = """
请根据以下事件和角色信息，生成一个场景大纲。场景应该：
1. 有明确的目标和冲突
2. 包含关键事件的发展
3. 合理安排角色的互动

事件信息：
{events}

角色信息：
{characters}

请以JSON格式输出，例如：
{
    "title": "场景标题",
    "goal": "场景目标",
    "description": "场景概要描述",
    "importance": 0.9
}
"""

        # 场景内容生成提示模板
        self.scene_generation_prompt = """
请根据以下场景大纲生成具体的剧本内容。内容应该：
1. 符合场景目标和主题
2. 展现人物性格和互动
3. 推动情节发展
4. 注意细节描写和氛围营造

场景大纲：
{outline}

支持信息：
{support_text}

请生成剧本格式的内容，包含场景描述、对话和动作指示。
"""
    
    def generate_scene_outline(
        self,
        events: List[Event],
        characters: List[Character]
    ) -> SceneOutline:
        """生成场景大纲
        
        Args:
            events: 相关事件列表
            characters: 相关角色列表
            
        Returns:
            SceneOutline: 生成的场景大纲
        """
        # 构建事件和角色信息字符串
        events_str = "\n".join(str(event) for event in events)
        chars_str = "\n".join(str(char) for char in characters)
        
        # 构建提示
        prompt = self.outline_generation_prompt.format(
            events=events_str,
            characters=chars_str
        )
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专注于剧本创作的助手。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            
            return SceneOutline(
                id=str(len(events)),  # 使用事件数量作为场景ID
                title=result["title"],
                events=events,
                characters=characters,
                goal=result["goal"],
                description=result["description"],
                importance=result.get("importance", 1.0)
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"场景大纲生成失败: {e}")
            return None
    
    def generate_scene_content(
        self,
        outline: SceneOutline,
        support_text: Optional[str] = None
    ) -> GeneratedScene:
        """生成场景内容
        
        Args:
            outline: 场景大纲
            support_text: 支持文本
            
        Returns:
            GeneratedScene: 生成的场景
        """
        # 构建提示
        prompt = self.scene_generation_prompt.format(
            outline=str(outline),
            support_text=support_text or ""
        )
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专注于剧本创作的助手。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 获取生成的内容
        content = response.choices[0].message.content
        
        # 如果提供了支持文本，使用 HAR 优化内容
        if support_text:
            har_result = self.har.process(content, support_text)
            content = har_result.refined_text
            confidence = har_result.confidence
        else:
            confidence = 0.8  # 默认置信度
        
        return GeneratedScene(
            outline=outline,
            content=content,
            confidence=confidence
        )
    
    def generate_script(
        self,
        causal_graph: CausalGraph,
        characters: List[Character],
        support_text: Optional[str] = None
    ) -> List[GeneratedScene]:
        """生成完整剧本
        
        Args:
            causal_graph: 因果图
            characters: 角色列表
            support_text: 支持文本
            
        Returns:
            List[GeneratedScene]: 生成的场景列表
        """
        generated_scenes = []
        
        # 获取事件的拓扑排序
        sorted_events = causal_graph.get_topological_sort()
        
        # 按重要性对事件进行分组
        current_events = []
        current_chars = set()
        
        for event in sorted_events:
            current_events.append(event)
            current_chars.update(event.characters)
            
            # 当积累了足够的事件或到达最后一个事件时，生成场景
            if len(current_events) >= 3 or event == sorted_events[-1]:
                # 获取相关角色
                scene_chars = [
                    char for char in characters
                    if char.name in current_chars
                ]
                
                # 生成场景大纲
                outline = self.generate_scene_outline(
                    current_events,
                    scene_chars
                )
                
                if outline:
                    # 生成场景内容
                    scene = self.generate_scene_content(
                        outline,
                        support_text
                    )
                    generated_scenes.append(scene)
                
                # 清空当前事件和角色集合
                current_events = []
                current_chars = set()
        
        return generated_scenes 