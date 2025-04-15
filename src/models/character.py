from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class Character:
    """角色模型类，用于表示故事中的角色"""
    
    id: str  # 角色唯一标识符
    name: str  # 角色名称
    description: Optional[str] = None  # 角色描述
    attributes: Dict[str, str] = field(default_factory=dict)  # 角色属性
    relationships: Dict[str, 'CharacterRelation'] = field(default_factory=dict)  # 与其他角色的关系
    events: List[str] = field(default_factory=list)  # 相关事件ID列表
    importance: float = 1.0  # 角色重要性评分 (0-1)
    
    def add_relationship(self, target_id: str, relation: 'CharacterRelation'):
        """添加与其他角色的关系"""
        self.relationships[target_id] = relation
    
    def add_event(self, event_id: str):
        """添加相关事件"""
        if event_id not in self.events:
            self.events.append(event_id)
    
    def to_dict(self) -> dict:
        """将角色转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "attributes": self.attributes,
            "relationships": {k: v.to_dict() for k, v in self.relationships.items()},
            "events": self.events,
            "importance": self.importance
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Character':
        """从字典创建角色实例"""
        relationships = data.pop("relationships", {})
        char = cls(**data)
        for target_id, rel_data in relationships.items():
            char.relationships[target_id] = CharacterRelation.from_dict(rel_data)
        return char
    
    def __str__(self) -> str:
        """返回角色的字符串表示"""
        parts = [f"角色: {self.name}"]
        if self.description:
            parts.append(f"描述: {self.description}")
        if self.attributes:
            attrs = [f"{k}: {v}" for k, v in self.attributes.items()]
            parts.append(f"属性: {', '.join(attrs)}")
        return " | ".join(parts)

@dataclass
class CharacterRelation:
    """角色关系类，用于表示两个角色之间的关系"""
    
    relation_type: str  # 关系类型 (friend, enemy, family, etc.)
    description: Optional[str] = None  # 关系描述
    strength: float = 1.0  # 关系强度 (0-1)
    metadata: Dict = field(default_factory=dict)  # 额外元数据
    
    def to_dict(self) -> dict:
        """将关系转换为字典格式"""
        return {
            "relation_type": self.relation_type,
            "description": self.description,
            "strength": self.strength,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CharacterRelation':
        """从字典创建关系实例"""
        return cls(**data)
    
    def __str__(self) -> str:
        """返回关系的字符串表示"""
        parts = [f"关系类型: {self.relation_type}"]
        if self.description:
            parts.append(f"描述: {self.description}")
        parts.append(f"强度: {self.strength}")
        return " | ".join(parts) 