from typing import Dict, List, Optional, Tuple
import networkx as nx
from .event import Event, EventRelation

class CausalGraph:
    """因果图模型类，用于表示事件之间的因果关系"""
    
    def __init__(self):
        """初始化因果图"""
        self.graph = nx.DiGraph()  # 有向图
        self.events: Dict[str, Event] = {}  # 事件字典
        self.relations: List[EventRelation] = []  # 关系列表
    
    def add_event(self, event: Event) -> None:
        """添加事件节点
        
        Args:
            event: 要添加的事件
        """
        self.events[event.id] = event
        self.graph.add_node(event.id, event=event)
    
    def add_relation(self, relation: EventRelation) -> None:
        """添加事件关系（边）
        
        Args:
            relation: 要添加的关系
        """
        source_id = relation.source_event.id
        target_id = relation.target_event.id
        
        # 确保两个事件都存在
        if source_id not in self.events:
            self.add_event(relation.source_event)
        if target_id not in self.events:
            self.add_event(relation.target_event)
        
        # 添加边
        self.graph.add_edge(
            source_id,
            target_id,
            relation=relation
        )
        self.relations.append(relation)
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """获取事件
        
        Args:
            event_id: 事件ID
            
        Returns:
            Event or None: 找到的事件或None
        """
        return self.events.get(event_id)
    
    def get_relation(self, source_id: str, target_id: str) -> Optional[EventRelation]:
        """获取两个事件之间的关系
        
        Args:
            source_id: 源事件ID
            target_id: 目标事件ID
            
        Returns:
            EventRelation or None: 找到的关系或None
        """
        if self.graph.has_edge(source_id, target_id):
            return self.graph[source_id][target_id]["relation"]
        return None
    
    def get_predecessors(self, event_id: str) -> List[Event]:
        """获取事件的前驱事件列表
        
        Args:
            event_id: 事件ID
            
        Returns:
            List[Event]: 前驱事件列表
        """
        return [self.events[pred_id] for pred_id in self.graph.predecessors(event_id)]
    
    def get_successors(self, event_id: str) -> List[Event]:
        """获取事件的后继事件列表
        
        Args:
            event_id: 事件ID
            
        Returns:
            List[Event]: 后继事件列表
        """
        return [self.events[succ_id] for succ_id in self.graph.successors(event_id)]
    
    def remove_cycles(self) -> List[Tuple[str, str]]:
        """移除图中的环
        
        Returns:
            List[Tuple[str, str]]: 被移除的边列表
        """
        removed_edges = []
        
        # 按权重排序所有边
        edges = [(u, v) for u, v in self.graph.edges()]
        edge_weights = [(u, v, self.graph[u][v]["relation"].weight) for u, v in edges]
        sorted_edges = sorted(edge_weights, key=lambda x: x[2], reverse=True)
        
        # 临时图用于检测环
        temp_graph = nx.DiGraph()
        
        for u, v, w in sorted_edges:
            temp_graph.add_edge(u, v)
            if not nx.is_directed_acyclic_graph(temp_graph):
                # 如果添加这条边会形成环，则移除它
                temp_graph.remove_edge(u, v)
                removed_edges.append((u, v))
                # 同时从原图中移除
                self.graph.remove_edge(u, v)
        
        return removed_edges
    
    def get_all_paths(self, source_id: str, target_id: str) -> List[List[str]]:
        """获取两个事件之间的所有路径
        
        Args:
            source_id: 源事件ID
            target_id: 目标事件ID
            
        Returns:
            List[List[str]]: 路径列表，每个路径是事件ID的列表
        """
        return list(nx.all_simple_paths(self.graph, source_id, target_id))
    
    def to_dict(self) -> dict:
        """将图转换为字典格式
        
        Returns:
            dict: 图的字典表示
        """
        return {
            "events": {k: v.to_dict() for k, v in self.events.items()},
            "relations": [r.to_dict() for r in self.relations]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CausalGraph':
        """从字典创建图实例
        
        Args:
            data: 图数据字典
            
        Returns:
            CausalGraph: 创建的图实例
        """
        graph = cls()
        
        # 首先创建所有事件
        events = {
            event_id: Event.from_dict(event_data)
            for event_id, event_data in data["events"].items()
        }
        
        # 添加所有事件到图中
        for event in events.values():
            graph.add_event(event)
        
        # 添加所有关系
        for rel_data in data["relations"]:
            relation = EventRelation.from_dict(rel_data, events)
            graph.add_relation(relation)
        
        return graph
    
    def get_topological_sort(self) -> List[Event]:
        """获取事件的拓扑排序
        
        Returns:
            List[Event]: 排序后的事件列表
        """
        try:
            sorted_ids = list(nx.topological_sort(self.graph))
            return [self.events[event_id] for event_id in sorted_ids]
        except nx.NetworkXUnfeasible:
            raise ValueError("图中存在环，无法进行拓扑排序") 