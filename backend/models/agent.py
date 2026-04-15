"""
Agent 模型

定义 Agent 的基本属性和行为
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import random


class ArchitectureType(Enum):
    """架构类型"""
    STAR = "star"
    TREE = "tree"
    MESH = "mesh"
    TRIBAL = "tribal"


class TraitorBehavior(Enum):
    """内鬼行为类型"""
    NONE = "none"
    SLACK = "slack"
    STEAL = "steal"
    MANIPULATE = "manipulate"
    SABOTAGE = "sabotage"
    TAMPER = "tamper"  # 篡改信息
    INJECT = "inject"  # 注入错误信息


@dataclass
class Personality:
    """Agent性格属性"""
    authority: float = 0.5      # 权威感
    selfishness: float = 0.5    # 私心
    resilience: float = 0.5    # 韧性
    altruism: float = 0.5       # 利他性
    sociability: float = 0.5    # 社交性
    risk_appetite: float = 0.5  # 风险偏好
    intelligence: float = 0.5   # 智力
    loyalty_base: float = 0.5   # 忠诚基准

    def to_dict(self) -> dict:
        return {
            "authority": self.authority,
            "selfishness": self.selfishness,
            "resilience": self.resilience,
            "altruism": self.altruism,
            "sociability": self.sociability,
            "risk_appetite": self.risk_appetite,
            "intelligence": self.intelligence,
            "loyalty_base": self.loyalty_base,
        }


@dataclass
class AgentState:
    """Agent状态"""
    energy: float = 100.0       # 当前体力值
    cognitive_entropy: float = 0.0  # 认知熵
    loyalty: float = 0.5       # 当前忠诚度
    contribution: float = 0.0   # 累计贡献值
    efficiency: float = 0.5    # 转化效率

    # 能量分配
    energy_work: float = 70.0   # 工作能量
    energy_conflict: float = 15.0  # 内斗能量
    energy_comm: float = 15.0    # 通讯能量

    def reset_energy(self):
        """重置体力值"""
        self.energy = 100.0

    def calculate_mental_load(self, avg_trust: float, position_stress: float) -> float:
        """计算心理负担"""
        base_load = (1 - avg_trust) * 0.4 + self.cognitive_entropy * 0.3 + position_stress * 0.3
        return min(1.0, max(0.0, base_load))

    def to_dict(self) -> dict:
        return {
            "energy": self.energy,
            "cognitive_entropy": self.cognitive_entropy,
            "loyalty": self.loyalty,
            "contribution": self.contribution,
            "efficiency": self.efficiency,
            "energy_work": self.energy_work,
            "energy_conflict": self.energy_conflict,
            "energy_comm": self.energy_comm,
        }


@dataclass
class Agent:
    """Agent 实体"""
    id: str
    name: str
    civilization_id: str
    description: str = ""  # Agent描述

    # 性格属性（使用Personality对象）
    personality: Personality = field(default_factory=Personality)

    # 状态（使用AgentState对象）
    state: AgentState = field(default_factory=AgentState)

    # 架构位置
    position: str = "edge"  # core, middle, edge
    level: int = 0  # 层级
    centrality: float = 0.5  # 中心性

    # 内鬼状态
    is_traitor: bool = False
    is_active_traitor: bool = False  # 是否激活
    traitor_tendency: float = 0.0  # 内鬼倾向
    traitor_behavior: TraitorBehavior = TraitorBehavior.NONE
    private_account: float = 0.0  # 私房钱（内鬼偷窃用）

    # 信任矩阵
    trust_matrix_row: Dict[str, float] = field(default_factory=dict)

    def initialize_trust(self, agent_ids: List[str]):
        """
        初始化信任矩阵

        Args:
            agent_ids: 所有Agent的ID列表
        """
        for agent_id in agent_ids:
            if agent_id != self.id:  # 不信任自己
                # 基础信任值基于忠诚度和性格
                base_trust = self.personality.loyalty_base * 0.5 + 0.25
                # 添加一些随机性
                self.trust_matrix_row[agent_id] = min(1.0, max(0.0, base_trust + random.uniform(-0.1, 0.1)))

    def calculate_efficiency(self, connected_trusts: List[float]) -> float:
        """
        计算效率

        Args:
            connected_trusts: 连接的Agent的信任值列表

        Returns:
            效率值 (0-1)
        """
        if not connected_trusts:
            return 0.5

        # 效率基于平均信任值和自身属性
        avg_trust = sum(connected_trusts) / len(connected_trusts)
        efficiency = (avg_trust * 0.4 +
                     self.personality.intelligence * 0.3 +
                     self.personality.resilience * 0.2 +
                     (1 - self.state.cognitive_entropy) * 0.1)

        self.state.efficiency = min(1.0, max(0.0, efficiency))
        return self.state.efficiency

    def get_avg_trust(self) -> float:
        """获取平均信任值"""
        if not self.trust_matrix_row:
            return 0.5
        return sum(self.trust_matrix_row.values()) / len(self.trust_matrix_row)

    def update_loyalty(self, delta: float):
        """更新忠诚度"""
        self.state.loyalty = max(0.0, min(1.0, self.state.loyalty + delta))

    def update_cognitive_entropy(self, delta: float):
        """更新认知熵"""
        self.state.cognitive_entropy = max(0.0, min(1.0, self.state.cognitive_entropy + delta))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "civilization_id": self.civilization_id,
            "personality": self.personality.to_dict(),
            "state": self.state.to_dict(),
            "position": self.position,
            "level": self.level,
            "centrality": self.centrality,
            "is_traitor": self.is_traitor,
            "is_active_traitor": self.is_active_traitor,
            "traitor_tendency": self.traitor_tendency,
            "private_account": self.private_account,
            "trust_matrix_row": self.trust_matrix_row
        }
