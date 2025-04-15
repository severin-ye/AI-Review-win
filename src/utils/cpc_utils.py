from typing import Dict, List, Tuple, Set, Optional
import networkx as nx
from openai import OpenAI
import json

class CPCProcessor:
    """因果图断环（Causal Plot-Graph Construction）处理器"""
    
    def __init__(self, llm_client: OpenAI):
        """初始化 CPC 处理器
        
        Args:
            llm_client: OpenAI 客户端
        """
        self.llm = llm_client
        
        # 因果关系判断提示模板
        self.causal_prompt = """
请分析以下两个事件之间是否存在因果关系。
如果存在，请用"高/中/低"标记关系强度，并说明原因。
如果不存在，请标记为"无"。

事件A：{event_a}
事件B：{event_b}

请以JSON格式输出，例如：
{
    "relation": "高/中/低/无",
    "reason": "关系强度判断的原因",
    "description": "对这种因果关系的具体描述"
}
"""
    
    def analyze_causal_relation(
        self,
        event_a: str,
        event_b: str
    ) -> Tuple[float, Optional[str]]:
        """分析两个事件之间的因果关系强度
        
        Args:
            event_a: 源事件描述
            event_b: 目标事件描述
            
        Returns:
            Tuple[float, Optional[str]]: (关系强度, 关系描述)
            关系强度：0.0表示无关系，0.3表示低，0.6表示中，0.9表示高
        """
        # 构建提示
        prompt = self.causal_prompt.format(
            event_a=event_a,
            event_b=event_b
        )
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专注于分析事件因果关系的助手。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            
            # 将文本关系强度转换为数值
            relation_map = {
                "高": 0.9,
                "中": 0.6,
                "低": 0.3,
                "无": 0.0
            }
            
            strength = relation_map.get(result["relation"], 0.0)
            description = result.get("description") if strength > 0 else None
            
            return strength, description
            
        except (json.JSONDecodeError, KeyError):
            return 0.0, None
    
    def break_cycles(
        self,
        edges: List[Tuple[str, str, float]],
        min_weight: float = 0.3
    ) -> List[Tuple[str, str, float]]:
        """执行断环算法
        
        Args:
            edges: 边列表，每个元素为 (源节点, 目标节点, 权重)
            min_weight: 最小权重阈值，低于此值的边将被优先移除
            
        Returns:
            List[Tuple[str, str, float]]: 保留的边列表
        """
        # 创建临时图
        G = nx.DiGraph()
        
        # 按权重从高到低排序边
        sorted_edges = sorted(edges, key=lambda x: x[2], reverse=True)
        
        # 存储已访问的节点集合
        visited: Set[str] = set()
        
        # 存储最终保留的边
        kept_edges = []
        
        for source, target, weight in sorted_edges:
            # 如果权重低于阈值，跳过
            if weight < min_weight:
                continue
            
            # 临时添加边
            G.add_edge(source, target)
            
            # 检查是否形成环
            try:
                # 尝试进行拓扑排序
                cycle = list(nx.find_cycle(G, source=source))
                # 如果没有抛出异常，说明存在环
                # 移除刚添加的边
                G.remove_edge(source, target)
            except nx.NetworkXNoCycle:
                # 没有环，保留这条边
                kept_edges.append((source, target, weight))
        
        return kept_edges
    
    def get_reachable_set(
        self,
        edges: List[Tuple[str, str, float]]
    ) -> Dict[str, Set[str]]:
        """计算每个节点的可达集合
        
        Args:
            edges: 边列表
            
        Returns:
            Dict[str, Set[str]]: 节点到其可达节点集合的映射
        """
        # 创建图
        G = nx.DiGraph()
        for source, target, _ in edges:
            G.add_edge(source, target)
        
        # 计算每个节点的可达集合
        reachable = {}
        for node in G.nodes():
            reachable[node] = set(nx.descendants(G, node))
        
        return reachable
    
    def sort_events_topologically(
        self,
        edges: List[Tuple[str, str, float]]
    ) -> List[str]:
        """对事件进行拓扑排序
        
        Args:
            edges: 边列表
            
        Returns:
            List[str]: 排序后的事件列表
        """
        # 创建图
        G = nx.DiGraph()
        for source, target, _ in edges:
            G.add_edge(source, target)
        
        try:
            return list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible:
            raise ValueError("图中存在环，无法进行拓扑排序")
    
    def get_event_importance(
        self,
        edges: List[Tuple[str, str, float]]
    ) -> Dict[str, float]:
        """计算每个事件的重要性得分
        
        Args:
            edges: 边列表
            
        Returns:
            Dict[str, float]: 事件到重要性得分的映射
        """
        # 创建图
        G = nx.DiGraph()
        for source, target, weight in edges:
            G.add_edge(source, target, weight=weight)
        
        # 使用 PageRank 算法计算节点重要性
        return nx.pagerank(G, weight='weight') 