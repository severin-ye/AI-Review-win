from typing import Dict, List, Optional, Tuple, Any
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import json
from pathlib import Path

class GraphVisualizer:
    """图可视化工具"""
    
    @staticmethod
    def plot_graph(
        G: nx.DiGraph,
        title: str = "Causal Graph",
        node_labels: Optional[Dict[str, str]] = None,
        edge_labels: Optional[Dict[Tuple[str, str], str]] = None,
        figsize: Tuple[int, int] = (12, 8),
        save_path: Optional[str] = None
    ) -> None:
        """使用 matplotlib 绘制图
        
        Args:
            G: NetworkX 图对象
            title: 图标题
            node_labels: 节点标签映射
            edge_labels: 边标签映射
            figsize: 图大小
            save_path: 保存路径
        """
        plt.figure(figsize=figsize)
        pos = nx.spring_layout(G)
        
        # 绘制节点
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                             node_size=1000, alpha=0.6)
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, edge_color='gray',
                             arrows=True, arrowsize=20)
        
        # 绘制节点标签
        if node_labels:
            nx.draw_networkx_labels(G, pos, node_labels)
        else:
            nx.draw_networkx_labels(G, pos)
        
        # 绘制边标签
        if edge_labels:
            nx.draw_networkx_edge_labels(G, pos, edge_labels)
        
        plt.title(title)
        plt.axis('off')
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
        plt.close()
    
    @staticmethod
    def create_interactive_graph(
        G: nx.DiGraph,
        title: str = "Causal Graph",
        node_labels: Optional[Dict[str, str]] = None,
        edge_labels: Optional[Dict[Tuple[str, str], str]] = None,
        save_path: Optional[str] = None
    ) -> None:
        """创建交互式图可视化
        
        Args:
            G: NetworkX 图对象
            title: 图标题
            node_labels: 节点标签映射
            edge_labels: 边标签映射
            save_path: 保存路径
        """
        # 创建 pyvis 网络对象
        net = Network(notebook=True, directed=True,
                     height="750px", width="100%",
                     bgcolor="#ffffff", font_color="black")
        
        # 添加节点
        for node in G.nodes():
            label = node_labels.get(node, str(node)) if node_labels else str(node)
            net.add_node(node, label=label, title=label)
        
        # 添加边
        for u, v in G.edges():
            label = edge_labels.get((u, v), "") if edge_labels else ""
            net.add_edge(u, v, label=label)
        
        # 配置物理布局
        net.set_options("""
        var options = {
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 100,
                    "springConstant": 0.08
                },
                "solver": "forceAtlas2Based",
                "minVelocity": 0.75,
                "timestep": 0.5
            }
        }
        """)
        
        if save_path:
            net.save_graph(save_path)

class GraphAnalyzer:
    """图分析工具"""
    
    @staticmethod
    def find_all_paths(
        G: nx.DiGraph,
        source: str,
        target: str
    ) -> List[List[str]]:
        """找出两个节点之间的所有路径
        
        Args:
            G: NetworkX 图对象
            source: 源节点
            target: 目标节点
            
        Returns:
            List[List[str]]: 路径列表
        """
        return list(nx.all_simple_paths(G, source, target))
    
    @staticmethod
    def get_node_centrality(G: nx.DiGraph) -> Dict[str, float]:
        """计算节点的中心性
        
        Args:
            G: NetworkX 图对象
            
        Returns:
            Dict[str, float]: 节点到中心性值的映射
        """
        return nx.betweenness_centrality(G)
    
    @staticmethod
    def get_strongly_connected_components(G: nx.DiGraph) -> List[List[str]]:
        """获取强连通分量
        
        Args:
            G: NetworkX 图对象
            
        Returns:
            List[List[str]]: 强连通分量列表
        """
        return list(nx.strongly_connected_components(G))
    
    @staticmethod
    def get_graph_statistics(G: nx.DiGraph) -> Dict[str, Any]:
        """获取图的统计信息
        
        Args:
            G: NetworkX 图对象
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "density": nx.density(G),
            "average_clustering": nx.average_clustering(G),
            "is_dag": nx.is_directed_acyclic_graph(G)
        }
    
    @staticmethod
    def export_graph(
        G: nx.DiGraph,
        save_path: str,
        node_attrs: Optional[Dict[str, Dict]] = None,
        edge_attrs: Optional[Dict[Tuple[str, str], Dict]] = None
    ) -> None:
        """导出图数据
        
        Args:
            G: NetworkX 图对象
            save_path: 保存路径
            node_attrs: 节点属性
            edge_attrs: 边属性
        """
        data = {
            "nodes": [],
            "edges": []
        }
        
        # 导出节点
        for node in G.nodes():
            node_data = {"id": node}
            if node_attrs and node in node_attrs:
                node_data.update(node_attrs[node])
            data["nodes"].append(node_data)
        
        # 导出边
        for u, v in G.edges():
            edge_data = {"source": u, "target": v}
            if edge_attrs and (u, v) in edge_attrs:
                edge_data.update(edge_attrs[(u, v)])
            data["edges"].append(edge_data)
        
        # 保存为 JSON 文件
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2) 