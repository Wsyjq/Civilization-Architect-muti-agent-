"""
上帝 Agent 模块

负责初始化和配置 Agent
"""

from typing import List, Dict
import random

from backend.models.agent import Agent, Personality, AgentState, ArchitectureType


class GodAgent:
    """
    上帝 Agent 类

    负责创建和管理 Agent 群体
    """

    def __init__(self, seed: int = None):
        """
        初始化上帝 Agent

        Args:
            seed: 随机种子
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def generate_agents(self, n: int, civilization_id: str) -> List[Agent]:
        """
        生成 Agent 群体

        Args:
            n: Agent 数量
            civilization_id: 文明ID

        Returns:
            Agent 列表
        """
        return initialize_agents(
            civilization_id=civilization_id,
            num_agents=n,
            arch_type=ArchitectureType.STAR,  # 默认使用星形架构
            seed=self.seed
        )


def initialize_agents(
    civilization_id: str,
    num_agents: int,
    arch_type: ArchitectureType,
    seed: int = None
) -> List[Agent]:
    """
    初始化 Agent 群体

    Args:
        civilization_id: 文明ID
        num_agents: Agent 数量
        arch_type: 架构类型
        seed: 随机种子

    Returns:
        Agent 列表
    """
    if seed:
        random.seed(seed)

    # Agent名称和描述
    names = [
        "领导者", "老实人", "野心家", "社交达人", "分析师",
        "守护者", "创新者", "协调者", "执行者", "观察者",
        "谋士", "探险家", "工匠", "传令官", "审计员"
    ]

    descriptions = [
        "天生领袖，决策果断，善于统筹全局",
        "踏实可靠，从不抱怨，执行力强",
        "志向远大，城府较深，善于隐藏意图",
        "人缘极好，擅长调解，沟通能力强",
        "逻辑严密，洞察敏锐，善于发现问题",
        "忠诚坚定，守护正义，值得信赖",
        "思维活跃，打破常规，追求突破",
        "圆滑周到，左右逢源，善于平衡",
        "执行力强，雷厉风行，效率至上",
        "安静内敛，观察入微，心思缜密",
        "足智多谋，擅长策划，深思熟虑",
        "敢于冒险，探索未知，追求新鲜",
        "手艺精湛，追求完美，注重细节",
        "传达准确，执行高效，忠诚度高",
        "谨慎小心，审计严格，风险意识强"
    ]

    agents = []
    for i in range(num_agents):
        # 随机性格
        personality = Personality(
            authority=random.uniform(0.2, 0.9),
            selfishness=random.uniform(0.1, 0.9),
            resilience=random.uniform(0.3, 0.9),
            altruism=random.uniform(0.2, 0.8),
            sociability=random.uniform(0.3, 0.9),
            risk_appetite=random.uniform(0.2, 0.8),
            intelligence=random.uniform(0.3, 0.95),
            loyalty_base=random.uniform(0.4, 0.95),
        )

        # 状态
        state = AgentState(
            energy=100.0,
            cognitive_entropy=0.1 + 0.05 * (1 - personality.resilience),
            loyalty=personality.loyalty_base,
            contribution=0.0,
            efficiency=0.5,
        )

        name = names[i] if i < len(names) else f"Agent {i+1}"
        desc = descriptions[i] if i < len(descriptions) else "普通成员"

        agent = Agent(
            id=f"{civilization_id}_A{i+1}",
            name=name,
            civilization_id=civilization_id,
            description=desc,
            personality=personality,
            state=state,
        )

        # 分配内鬼倾向（少数人有较高内鬼倾向）
        if random.random() < 0.2:  # 20%的概率
            agent.traitor_tendency = random.uniform(0.3, 0.7)
            agent.is_traitor = True

        agents.append(agent)

    # 设置架构位置
    _assign_positions(agents, arch_type)

    return agents


def _assign_positions(agents: List[Agent], arch_type: ArchitectureType):
    """分配架构位置"""
    if not agents:
        return

    if arch_type == ArchitectureType.STAR:
        # 星形：第一个是核心，其他是边缘
        agents[0].position = "core"
        agents[0].level = 0
        agents[0].centrality = 1.0
        for agent in agents[1:]:
            agent.position = "edge"
            agent.level = 1
            agent.centrality = 0.3

    elif arch_type == ArchitectureType.TREE:
        # 树形：层级结构
        agents[0].position = "core"
        agents[0].level = 0
        agents[0].centrality = 1.0
        mid = len(agents) // 2
        for i in range(1, min(mid, len(agents))):
            agents[i].position = "middle"
            agents[i].level = 1
            agents[i].centrality = 0.6
        for i in range(mid, len(agents)):
            agents[i].position = "edge"
            agents[i].level = 2
            agents[i].centrality = 0.3

    elif arch_type == ArchitectureType.MESH:
        # 网状：所有节点平等
        for agent in agents:
            agent.position = "middle"
            agent.level = 1
            agent.centrality = 0.7

    else:
        # 其他架构：随机分配
        for agent in agents:
            pos = random.choice(["core", "middle", "edge"])
            agent.position = pos
            agent.level = {"core": 0, "middle": 1, "edge": 2}[pos]
            agent.centrality = {"core": 0.8, "middle": 0.5, "edge": 0.3}[pos]
