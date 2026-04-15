"""
宏观变量模块

定义和管理文明的宏观状态变量
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import numpy as np


class ResourceType(Enum):
    """资源类型"""
    ENERGY = "energy"
    MATERIAL = "material"
    KNOWLEDGE = "knowledge"
    POPULATION = "population"


@dataclass
class MacroVariables:
    """宏观变量"""
    civilization_id: str

    # 基础资源
    resources: Dict[ResourceType, float] = field(default_factory=lambda: {
        ResourceType.ENERGY: 100.0,
        ResourceType.MATERIAL: 100.0,
        ResourceType.KNOWLEDGE: 50.0,
        ResourceType.POPULATION: 10.0
    })

    # 文明状态
    stability: float = 0.5  # 稳定性
    productivity: float = 0.5  # 生产力
    cohesion: float = 0.5  # 凝聚力

    # 环境参数
    environment_quality: float = 1.0  # 环境质量
    threat_level: float = 0.0  # 威胁等级

    # 回合信息
    round: int = 0
    total_rounds: int = 100

    def update(self, delta: Dict[str, float]):
        """更新宏观变量"""
        for key, value in delta.items():
            if hasattr(self, key):
                setattr(self, key, max(0, min(1, getattr(self, key) + value)))

    def to_dict(self) -> dict:
        return {
            "civilization_id": self.civilization_id,
            "resources": {k.value: v for k, v in self.resources.items()},
            "stability": self.stability,
            "productivity": self.productivity,
            "cohesion": self.cohesion,
            "environment_quality": self.environment_quality,
            "threat_level": self.threat_level,
            "round": self.round,
            "total_rounds": self.total_rounds
        }


def initialize_macro_variables(civilization_id: str) -> MacroVariables:
    """初始化宏观变量"""
    return MacroVariables(civilization_id=civilization_id)


class ProductionCalculator:
    """生产力计算器"""

    @staticmethod
    def calculate_productivity(agents, macro_vars: MacroVariables) -> float:
        """计算文明生产力"""
        if not agents:
            return 0.0

        # 基础生产力
        total_efficiency = sum(agent.state.efficiency for agent in agents)
        avg_efficiency = total_efficiency / len(agents)

        # 架构加成
        cohesion_bonus = macro_vars.cohesion * 0.2

        # 环境惩罚
        environment_penalty = (1 - macro_vars.environment_quality) * 0.3

        return max(0, min(1, avg_efficiency + cohesion_bonus - environment_penalty))

    @staticmethod
    def calculate_resource_output(macro_vars: MacroVariables, productivity: float) -> Dict[ResourceType, float]:
        """计算资源产出"""
        output = {}
        for resource_type in ResourceType:
            base_amount = macro_vars.resources.get(resource_type, 0)
            output[resource_type] = base_amount * productivity * 0.1
        return output

    @staticmethod
    def calculate_cycle_output(agents, config, game_config) -> Dict[str, float]:
        """
        计算一轮的产出

        Args:
            agents: Agent列表
            config: 架构配置
            game_config: 游戏配置

        Returns:
            包含cycle_output和total_output的字典
        """
        if not agents:
            return {"cycle_output": 0.0, "total_output": 0.0}

        # 计算基础产出
        total_contribution = 0.0
        for agent in agents:
            # 基于能量分配和工作效率计算贡献
            work_ratio = agent.state.energy_work / 100.0
            efficiency = agent.state.efficiency

            # 贡献 = 工作能量 * 效率 * 性格加成
            personality_bonus = (
                agent.personality.authority * 0.2 +
                agent.personality.altruism * 0.2 +
                agent.personality.intelligence * 0.3 +
                (1 - agent.personality.selfishness) * 0.2 +
                agent.personality.resilience * 0.1
            )

            contribution = work_ratio * efficiency * personality_bonus * 10
            agent.state.contribution = contribution
            total_contribution += contribution

        # 架构效率系数
        arch_efficiency = config.efficiency_coefficient

        # 计算内鬼惩罚
        traitor_count = sum(1 for a in agents if a.is_active_traitor)
        traitor_penalty = 1.0 - (traitor_count * 0.1)

        # 循环产出
        cycle_output = total_contribution * arch_efficiency * traitor_penalty

        return {
            "cycle_output": cycle_output,
            "total_output": cycle_output
        }


def calculate_all_macro_variables(agents, config) -> Dict[str, float]:
    """
    计算所有宏观变量

    Args:
        agents: Agent列表
        config: 架构配置

    Returns:
        宏观变量字典
    """
    if not agents:
        return {
            "energy_level": 0.0,
            "cohesion": 0.0,
            "fidelity": 0.0,
            "social_capital": 0.0
        }

    n = len(agents)

    # 能量等级
    total_energy = sum(a.state.energy for a in agents)
    energy_level = (total_energy / n) / 100.0

    # 凝聚力 = 平均忠诚度 * (1 - 忠诚度方差)
    loyalties = [a.state.loyalty for a in agents]
    avg_loyalty = sum(loyalties) / n
    variance = sum((l - avg_loyalty) ** 2 for l in loyalties) / n
    cohesion = avg_loyalty * (1 - min(variance / 0.25, 1) ** 1.5)

    # 保真度
    avg_trust = sum(a.get_avg_trust() for a in agents) / n
    fidelity = max(0.5, avg_trust * config.reachability * (1 - variance))

    # 社会资本
    adj = config.adjacency_matrix
    total_trust = sum(sum(adj[i, j] * agents[i].trust_matrix_row.get(agents[j].id, 0.5)
                          for j in range(n) if adj[i, j] > 0)
                      for i in range(n))
    edge_count = sum(1 for i in range(n) for j in range(n) if adj[i, j] > 0)
    social_capital = (total_trust / edge_count if edge_count > 0 else 0.5) + 0.2 * config.robustness_coefficient

    return {
        "energy_level": energy_level,
        "cohesion": cohesion,
        "fidelity": fidelity,
        "social_capital": social_capital
    }
