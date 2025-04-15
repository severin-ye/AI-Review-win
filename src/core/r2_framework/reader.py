from typing import List, Dict, Any, Optional, Tuple
import json
from openai import OpenAI

from ...models import Event, Character, CausalGraph
from ...utils.har_utils import HARProcessor
from ...utils.cpc_utils import CPCProcessor

class Reader:
    """Reader 模块，负责从文本中提取事件和角色信息"""
    
    def __init__(self, llm_client: OpenAI):
        """初始化 Reader
        
        Args:
            llm_client: OpenAI 客户端
        """
        self.llm = llm_client
        self.har = HARProcessor(llm_client)
        self.cpc = CPCProcessor(llm_client)
        
        # 事件提取提示模板
        self.event_extraction_prompt = """
请从以下文本中提取关键事件信息，并以 JSON 格式输出。每个事件必须包含以下字段：
- id: 事件唯一标识符（如 "event1", "event2" 等）
- content: 事件内容描述
- time: 发生时间（如果有）
- place: 发生地点（如果有）
- characters: 相关角色列表
- importance: 事件重要性（0-1之间的浮点数）
- metadata: 额外信息（可选）

文本内容：
{text}

支持信息：
{support_text}

请以严格的 JSON 格式输出，例如：
{
    "events": [
        {
            "id": "event1",
            "content": "事件描述",
            "time": "发生时间",
            "place": "发生地点",
            "characters": ["角色1", "角色2"],
            "importance": 0.9,
            "metadata": {}
        }
    ]
}
"""

        # 角色提取提示模板
        self.character_extraction_prompt = """
请从以下文本中提取角色信息，并以 JSON 格式输出。每个角色必须包含以下字段：
- id: 角色唯一标识符（如 "char1", "char2" 等）
- name: 角色名称
- description: 角色描述
- attributes: 角色属性（如身份、性格等）
- importance: 重要性评分（0-1之间的浮点数）
- relationships: 与其他角色的关系（可选）

文本内容：
{text}

请以严格的 JSON 格式输出，例如：
{
    "characters": [
        {
            "id": "char1",
            "name": "角色名称",
            "description": "角色描述",
            "attributes": {
                "identity": "身份",
                "personality": "性格特征"
            },
            "importance": 0.9,
            "relationships": {
                "char2": {
                    "relation_type": "关系类型",
                    "description": "关系描述",
                    "strength": 0.8
                }
            }
        }
    ]
}
"""
    
    def extract_events(
        self,
        text: str,
        support_text: Optional[str] = None
    ) -> List[Event]:
        """从文本中提取事件信息
        
        Args:
            text: 输入文本
            support_text: 支持文本（用于事实验证）
            
        Returns:
            List[Event]: 提取的事件列表
        """
        if not text.strip():
            print("输入文本为空")
            return []

        # 构建提示
        prompt = self.event_extraction_prompt.format(
            text=text,
            support_text=support_text or ""
        )
        
        try:
            # 调用 LLM
            response = self.llm.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个专注于事件提取和分析的助手。请以 JSON 格式输出。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            if not response.choices or not response.choices[0].message:
                print("API 返回结果为空")
                return []
                
            content = response.choices[0].message.content
            if not content or not content.strip():
                print("API 返回内容为空")
                return []
                
            # 预处理 JSON 字符串
            content = content.strip()
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON 解析错误: {e}")
                print(f"原始内容: {content}")
                # 尝试修复常见的 JSON 格式问题
                content = content.replace('\n', '').replace('\r', '')
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    print("修复 JSON 格式失败")
                    return []
            
            if not isinstance(result, dict):
                print(f"解析结果不是字典类型: {type(result)}")
                return []
                
            if "events" not in result:
                print("解析结果中缺少 'events' 字段")
                return []
                
            if not isinstance(result["events"], list):
                print("'events' 字段不是列表类型")
                return []
                
            events = []
            for event_data in result["events"]:
                if not isinstance(event_data, dict):
                    print(f"事件数据不是字典类型: {event_data}")
                    continue
                    
                try:
                    # 验证必要字段
                    required_fields = ["id", "content"]
                    if not all(field in event_data for field in required_fields):
                        print(f"事件数据缺少必要字段: {event_data}")
                        continue
                        
                    # 安全地获取和转换字段值
                    event = Event(
                        id=str(event_data.get("id", "")),
                        content=str(event_data.get("content", "")),
                        time=str(event_data.get("time", "")) or None,
                        place=str(event_data.get("place", "")) or None,
                        characters=[str(c) for c in event_data.get("characters", []) if c],
                        importance=float(event_data.get("importance", 1.0)),
                        metadata=event_data.get("metadata", {})
                    )
                    events.append(event)
                except (ValueError, TypeError) as e:
                    print(f"处理事件数据时出错: {e}")
                    continue
            
            return events
            
        except Exception as e:
            print(f"事件提取过程出现未知错误: {str(e)}")
            return []
    
    def extract_characters(
        self,
        text: str
    ) -> List[Character]:
        """从文本中提取角色信息
        
        Args:
            text: 输入文本
            
        Returns:
            List[Character]: 提取的角色列表
        """
        # 构建提示
        prompt = self.character_extraction_prompt.format(text=text)
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system", 
                    "content": "你是一个专注于角色分析的助手。请以 JSON 格式输出。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            content = response.choices[0].message.content
            print(f"API返回内容: {content}")  # 添加调试输出
            result = json.loads(content)
            characters = []
            
            if not isinstance(result, dict) or "characters" not in result:
                print(f"API返回格式错误: {result}")
                return []
            
            for char_data in result["characters"]:
                try:
                    # 创建角色实例
                    char = Character(
                        id=char_data["id"],
                        name=char_data["name"],
                        description=char_data.get("description"),
                        attributes=char_data.get("attributes", {}),
                        importance=char_data.get("importance", 1.0)
                    )
                    
                    # 添加角色关系
                    for target_id, rel_data in char_data.get("relationships", {}).items():
                        char.add_relationship(target_id, rel_data)
                    
                    characters.append(char)
                except KeyError as ke:
                    print(f"角色数据缺少必要字段: {ke}")
                    continue
            
            return characters
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始内容: {response.choices[0].message.content}")
            return []
        except Exception as e:
            print(f"角色提取过程出现未知错误: {e}")
            return []
    
    def build_causal_graph(
        self,
        events: List[Event]
    ) -> CausalGraph:
        """构建事件因果图
        
        Args:
            events: 事件列表
            
        Returns:
            CausalGraph: 构建的因果图
        """
        # 创建因果图
        graph = CausalGraph()
        
        # 添加所有事件
        for event in events:
            graph.add_event(event)
        
        # 分析事件间的因果关系
        for i, event_a in enumerate(events):
            for event_b in events[i+1:]:
                # 使用 CPC 处理器分析因果关系
                strength, description = self.cpc.analyze_causal_relation(
                    event_a.content,
                    event_b.content
                )
                
                # 如果存在因果关系，添加到图中
                if strength > 0:
                    relation = {
                        "source_event": event_a,
                        "target_event": event_b,
                        "relation_type": "cause",
                        "weight": strength,
                        "description": description
                    }
                    graph.add_relation(relation)
        
        # 移除环
        graph.remove_cycles()
        
        return graph 