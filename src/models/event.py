from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

@dataclass
class Event:
    """事件模型类，用于表示从文本中提取的事件"""
    
    id: str  # 事件唯一标识符
    content: str  # 事件内容
    time: Optional[str] = None  # 事件发生时间
    place: Optional[str] = None  # 事件发生地点
    characters: List[str] = None  # 相关角色列表
    importance: float = 1.0  # 事件重要性评分 (0-1)
    metadata: Dict = None  # 额外元数据
    
    def __post_init__(self):
        """初始化后的处理"""
        if self.characters is None:
            self.characters = []
        if self.metadata is None:
            self.metadata = {}
            
    def to_dict(self) -> dict:
        """将事件转换为字典格式"""
        return {
            "id": self.id,
            "content": self.content,
            "time": self.time,
            "place": self.place,
            "characters": self.characters,
            "importance": self.importance,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """从字典创建事件实例"""
        return cls(**data)
    
    def __str__(self) -> str:
        """返回事件的字符串表示"""
        parts = [f"事件: {self.content}"]
        if self.time:
            parts.append(f"时间: {self.time}")
        if self.place:
            parts.append(f"地点: {self.place}")
        if self.characters:
            parts.append(f"角色: {', '.join(self.characters)}")
        return " | ".join(parts)

@dataclass
class EventRelation:
    """事件关系类，用于表示两个事件之间的因果关系"""
    
    source_event: Event  # 源事件
    target_event: Event  # 目标事件
    relation_type: str  # 关系类型 (cause, sequence, etc.)
    weight: float  # 关系强度 (0-1)
    description: Optional[str] = None  # 关系描述
    
    def to_dict(self) -> dict:
        """将关系转换为字典格式"""
        return {
            "source_event_id": self.source_event.id,
            "target_event_id": self.target_event.id,
            "relation_type": self.relation_type,
            "weight": self.weight,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict, event_map: Dict[str, Event]) -> 'EventRelation':
        """从字典创建关系实例
        
        Args:
            data: 关系数据字典
            event_map: 事件ID到事件实例的映射
        """
        source_event = event_map[data["source_event_id"]]
        target_event = event_map[data["target_event_id"]]
        return cls(
            source_event=source_event,
            target_event=target_event,
            relation_type=data["relation_type"],
            weight=data["weight"],
            description=data.get("description")
        ) 