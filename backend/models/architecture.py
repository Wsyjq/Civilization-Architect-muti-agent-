"""
架构模型

定义文明架构的配置和分析
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

from backend.models.agent import ArchitectureType, Agent


@dataclass
class ArchitectureConfig:
    """架构配置"""
    arch_type: ArchitectureType
    num_agents: int

    # 邻接矩阵
    adjacency_matrix: np.ndarray = None

    # 通达度
    reachability: float = 1.0

    # 平均路径长度
    average_path_length: float = 1.0

    # 每轮循环数
    cycles_per_round: int = 3

    # 效率系数
    efficiency_coefficient: float = 1.0

    # 鲁棒性系数
    robustness_coefficient: float = 0.5

    def __post_init__(self):
        if self.adjacency_matrix is None:
            self.adjacency_matrix = np.zeros((self.num_agents, self.num_agents))


@dataclass
class ArchitectureAnalyzer:
    """架构分析器"""

    @staticmethod
    def calculate_accessibility(arch_type: ArchitectureType, num_agents: int) -> float:
        """计算通达度"""
        base_accessibility = {
            ArchitectureType.STAR: 1.5,
            ArchitectureType.TREE: 0.8,
            ArchitectureType.MESH: 1.0,
            ArchitectureType.TRIBAL: 0.6
        }
        return base_accessibility.get(arch_type, 1.0)

    @staticmethod
    def calculate_robustness(arch_type: ArchitectureType) -> float:
        """计算鲁棒性"""
        base_robustness = {
            ArchitectureType.STAR: 0.1,
            ArchitectureType.TREE: 0.3,
            ArchitectureType.MESH: 0.9,
            ArchitectureType.TRIBAL: 0.6
        }
        return base_robustness.get(arch_type, 0.5)

    @staticmethod
    def assign_agent_positions(config: ArchitectureConfig, agents: List[Agent]) -> List[Agent]:
        """
        分配Agent到架构位置

        Args:
            config: 架构配置
            agents: Agent列表

        Returns:
            分配了位置的Agent列表
        """
        n = len(agents)
        if n == 0:
            return agents

        arch_type = config.arch_type

        if arch_type == ArchitectureType.STAR:
            # 星形架构：第一个是核心，其他是边缘
            agents[0].position = "core"
            agents[0].level = 0
            agents[0].centrality = 1.0
            for agent in agents[1:]:
                agent.position = "edge"
                agent.level = 1
                agent.centrality = 0.3

        elif arch_type == ArchitectureType.TREE:
            # 树形架构：层级结构
            if n >= 1:
                agents[0].position = "core"
                agents[0].level = 0
                agents[0].centrality = 1.0

            mid = n // 2
            for i in range(1, min(mid, n)):
                agents[i].position = "middle"
                agents[i].level = 1
                agents[i].centrality = 0.6

            for i in range(mid, n):
                agents[i].position = "edge"
                agents[i].level = 2
                agents[i].centrality = 0.3

        elif arch_type == ArchitectureType.MESH:
            # 网状架构：所有节点平等，中心性基于连接数
            for agent in agents:
                agent.position = "middle"
                agent.level = 1
                agent.centrality = 0.7

        elif arch_type == ArchitectureType.TRIBAL:
            # 部落架构：随机分配位置
            import random
            for agent in agents:
                pos = random.choice(["core", "middle", "edge"])
                agent.position = pos
                agent.level = {"core": 0, "middle": 1, "edge": 2}[pos]
                agent.centrality = {"core": 0.8, "middle": 0.5, "edge": 0.3}[pos]

        return agents


def create_architecture(arch_type: ArchitectureType, num_agents: int) -> ArchitectureConfig:
    """
    创建架构配置

    Args:
        arch_type: 架构类型
        num_agents: Agent数量

    Returns:
        配置好的架构配置
    """
    n = num_agents
    adj = np.zeros((n, n))

    if arch_type == ArchitectureType.STAR:
        # 星形架构：中心节点连接所有其他节点
        for i in range(1, n):
            adj[0, i] = 1.0
            adj[i, 0] = 1.0

    elif arch_type == ArchitectureType.TREE:
        # 树形架构：层级结构
        if n >= 1:
            # 根节点连接第二层
            if n > 1:
                mid = n // 2
                for i in range(1, min(mid + 1, n)):
                    adj[0, i] = 1.0
                    adj[i, 0] = 1.0

                # 第二层连接第三层
                for i in range(1, min(mid + 1, n)):
                    for j in range(mid, n):
                        if j != i:
                            adj[i, j] = 0.5  # 部分连接
                            adj[j, i] = 0.5

    elif arch_type == ArchitectureType.MESH:
        # 网状架构：所有节点互相连接
        for i in range(n):
            for j in range(n):
                if i != j:
                    adj[i, j] = 1.0

    elif arch_type == ArchitectureType.TRIBAL:
        # 部落架构：形成多个小团体
        import random
        group_size = max(2, n // 3)
        for i in range(n):
            for j in range(n):
                if i != j:
                    # 同组内连接紧密
                    if i // group_size == j // group_size:
                        adj[i, j] = 0.8
                    else:
                        adj[i, j] = 0.2

    # 计算系数
    reachability = ArchitectureAnalyzer.calculate_accessibility(arch_type, n)
    robustness = ArchitectureAnalyzer.calculate_robustness(arch_type)

    # 计算Floyd-Warshall最短路径
    try:
        dist = adj.copy()
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    if dist[i, k] + dist[k, j] < dist[i, j]:
                        dist[i, j] = dist[i, k] + dist[k, j]

        # 平均路径长度
        total_dist = sum(sum(dist[i, j] for j in range(n) if i != j and dist[i, j] < 999)
                         for i in range(n))
        count = sum(1 for i in range(n) for j in range(n) if i != j and dist[i, j] < 999)
        avg_path = total_dist / count if count > 0 else 1.0
    except:
        avg_path = 1.0

    config = ArchitectureConfig(
        arch_type=arch_type,
        num_agents=n,
        adjacency_matrix=adj,
        reachability=reachability,
        average_path_length=avg_path,
        cycles_per_round=3,
        efficiency_coefficient=reachability,
        robustness_coefficient=robustness
    )

    return config
