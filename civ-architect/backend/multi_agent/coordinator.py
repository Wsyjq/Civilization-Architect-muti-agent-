"""
协作者

管理多Agent轮次执行、消息收集和分发
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import asyncio
import numpy as np

from backend.multi_agent.agent_runtime import (
    AgentRuntime,
    AgentAction,
    get_agent_runtime,
    create_agent_runtime,
    clear_all_runtimes
)
from backend.multi_agent.message_broker import (
    MessageBroker,
    Message,
    get_message_broker,
    reset_message_broker
)
from backend.multi_agent.agent_prompts import build_system_prompt, build_action_prompt


@dataclass
class CycleResult:
    """一轮执行的结果"""
    cycle_num: int
    actions: Dict[str, AgentAction]  # agent_id -> action
    messages: List[Message]
    total_output: float
    macro_variables: Dict[str, float]
    duration_ms: float


class Coordinator:
    """
    协作者

    管理多Agent系统的执行流程：
    1. 并行调用所有Agent的think()
    2. 收集和路由消息
    3. 计算产出和宏观变量
    """

    def __init__(
        self,
        agents: List[Any],  # Agent模型列表
        adjacency_matrix: np.ndarray,
        architecture_type: str,
        config: Any = None
    ):
        self.agents = agents
        self.adjacency_matrix = adjacency_matrix
        self.architecture_type = architecture_type
        self.config = config

        # 创建Agent运行时
        self._runtimes: Dict[str, AgentRuntime] = {}
        for agent in agents:
            runtime = create_agent_runtime(agent)
            self._runtimes[agent.id] = runtime

        # 消息代理
        self._broker = get_message_broker()
        self._broker.set_adjacency_matrix(adjacency_matrix, [a.id for a in agents])

        # 设置Agent名称解析
        self._broker.set_agent_name_resolver(self._resolve_agent_name)

        # 回合/循环计数
        self.round_num = 1
        self.cycle_num = 0
        self.total_rounds = 10

        # 总产出
        self.total_output = 0.0

        # 宏观变量历史
        self.energy_level_history: List[float] = []
        self.cohesion_history: List[float] = []
        self.fidelity_history: List[float] = []
        self.social_capital_history: List[float] = []

    def _resolve_agent_name(self, agent_id: str) -> str:
        """解析Agent名称"""
        for agent in self.agents:
            if agent.id == agent_id:
                return agent.name
        return agent_id

    def _get_connected_agents(self, agent_id: str) -> Set[str]:
        """获取与指定Agent有连接的其他Agent"""
        for i, agent in enumerate(self.agents):
            if agent.id == agent_id:
                break
        else:
            return set()

        # 从邻接矩阵获取连接
        connected = set()
        adj = self.adjacency_matrix
        n = len(self.agents)

        for j in range(n):
            if adj[i, j] > 0 or adj[j, i] > 0:
                connected.add(self.agents[j].id)

        return connected

    def _build_context(self) -> Dict[str, Any]:
        """构建游戏上下文"""
        return {
            "round_num": self.round_num,
            "total_rounds": self.total_rounds,
            "cycle_num": self.cycle_num,
            "total_output": self.total_output,
            "architecture_type": self.architecture_type,
        }

    async def run_cycle(self) -> CycleResult:
        """
        执行一轮

        每个Agent：
        1. 思考（调用LLM）
        2. 发送消息
        3. 更新状态
        """
        import time
        start_time = time.time()

        self.cycle_num += 1
        context = self._build_context()

        # 并行调用所有Agent思考
        think_tasks = []
        for agent in self.agents:
            runtime = self._runtimes.get(agent.id)
            if runtime:
                think_tasks.append(runtime.think(context))

        # 等待所有Agent完成思考
        if think_tasks:
            results = await asyncio.gather(*think_tasks, return_exceptions=True)
        else:
            results = []

        # 收集行动
        actions: Dict[str, AgentAction] = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Agent {self.agents[i].id} think failed: {result}")
                # 使用默认行动
                actions[self.agents[i].id] = AgentAction(
                    agent_id=self.agents[i].id,
                    energy_allocation={"work": 50, "conflict": 20, "comm": 10},
                    messages=[]
                )
            else:
                actions[result.agent_id] = result

        # 路由消息
        self._route_messages(actions)

        # 应用行动结果
        self._apply_actions(actions)

        # 计算产出
        output = self._calculate_output()
        self.total_output += output

        # 计算宏观变量
        macro = self._calculate_macro_variables()
        self._record_history(macro)

        duration_ms = (time.time() - start_time) * 1000

        return CycleResult(
            cycle_num=self.cycle_num,
            actions=actions,
            messages=self._broker.get_all_messages(),
            total_output=output,
            macro_variables=macro,
            duration_ms=duration_ms
        )

    def _route_messages(self, actions: Dict[str, AgentAction]):
        """
        路由消息

        根据架构邻接矩阵将消息发送到接收者
        """
        for agent_id, action in actions.items():
            connected = self._get_connected_agents(agent_id)

            for msg_data in action.messages:
                receiver_id = msg_data.get("receiver_id")
                content = msg_data.get("content", "")
                msg_type = msg_data.get("message_type", "chat")

                if not receiver_id or not content:
                    continue

                # 如果是广播
                if receiver_id == "all":
                    for rid in connected:
                        self._broker.publish(Message(
                            message_id="",  # 将在broker中生成
                            sender_id=agent_id,
                            sender_name=self._resolve_agent_name(agent_id),
                            receiver_id=rid,
                            receiver_name=self._resolve_agent_name(rid),
                            content=content,
                            message_type=msg_type,
                            importance=0.5
                        ))
                    continue

                # 点对点消息
                if receiver_id in connected or receiver_id == "all":
                    self._broker.publish(Message(
                        message_id="",
                        sender_id=agent_id,
                        sender_name=self._resolve_agent_name(agent_id),
                        receiver_id=receiver_id,
                        receiver_name=self._resolve_agent_name(receiver_id),
                        content=content,
                        message_type=msg_type,
                        importance=0.5
                    ))

    def _apply_actions(self, actions: Dict[str, AgentAction]):
        """应用行动结果到Agent状态"""
        for agent_id, action in actions.items():
            # 更新能量分配
            alloc = action.energy_allocation
            for agent in self.agents:
                if agent.id == agent_id:
                    agent.state.energy_work = alloc.get("work", 50)
                    agent.state.energy_conflict = alloc.get("conflict", 20)
                    agent.state.energy_comm = alloc.get("comm", 10)
                    break

    def _calculate_output(self) -> float:
        """计算本轮产出"""
        total = 0.0
        for agent in self.agents:
            # 基本产出 = 工作能量 * 效率
            work_energy = agent.state.energy_work
            efficiency = agent.state.efficiency

            # 内鬼惩罚
            if agent.is_active_traitor:
                efficiency *= 0.5

            # 认知熵惩罚
            clarity = 1 - agent.state.cognitive_entropy * 0.5

            contribution = work_energy * efficiency * clarity / 100
            agent.state.contribution += contribution
            total += contribution

        return total

    def _calculate_macro_variables(self) -> Dict[str, float]:
        """计算宏观变量"""
        n = len(self.agents)
        if n == 0:
            return {"energy_level": 0, "cohesion": 0, "fidelity": 0, "social_capital": 0}

        # 能量水平
        energy_sum = sum(a.state.energy for a in self.agents)
        energy_level = energy_sum / (n * 100)

        # 内聚力（基于平均忠诚度和信任方差）
        loyalties = [a.state.loyalty for a in self.agents]
        avg_loyalty = sum(loyalties) / n
        loyalty_var = sum((l - avg_loyalty) ** 2 for l in loyalties) / n
        cohesion = avg_loyalty * (1 - min(loyalty_var / 0.25, 1) ** 1.5)

        # 忠诚度（fidelity）
        trusts = []
        for a in self.agents:
            trusts.extend(a.trust_matrix_row.values())
        avg_trust = sum(trusts) / len(trusts) if trusts else 0.5
        fidelity = max(0.5, avg_trust * (1 - energy_level * 0.2))

        # 社会资本
        trust_sum = sum(a.get_avg_trust() for a in self.agents)
        social_capital = trust_sum / n + 0.2 * (np.sum(self.adjacency_matrix) / (n * n))

        return {
            "energy_level": energy_level,
            "cohesion": cohesion,
            "fidelity": fidelity,
            "social_capital": social_capital
        }

    def _record_history(self, macro: Dict[str, float]):
        """记录宏观变量历史"""
        self.energy_level_history.append(macro["energy_level"])
        self.cohesion_history.append(macro["cohesion"])
        self.fidelity_history.append(macro["fidelity"])
        self.social_capital_history.append(macro["social_capital"])

    async def run_round(self):
        """执行一回合（多个循环）"""
        cycles_per_round = getattr(self.config, 'cycles_per_round', 3) if self.config else 3

        for _ in range(cycles_per_round):
            await self.run_cycle()

        self.round_num += 1

    def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "round": self.round_num,
            "cycle": self.cycle_num,
            "total_output": self.total_output,
            "energy_level": self.energy_level_history[-1] if self.energy_level_history else 0,
            "cohesion": self.cohesion_history[-1] if self.cohesion_history else 0,
            "fidelity": self.fidelity_history[-1] if self.fidelity_history else 0,
            "social_capital": self.social_capital_history[-1] if self.social_capital_history else 0,
        }

    def cleanup(self):
        """清理资源"""
        clear_all_runtimes()
        reset_message_broker()


# 便捷函数
async def create_coordinator(
    agents: List[Any],
    adjacency_matrix: np.ndarray,
    architecture_type: str,
    config: Any = None
) -> Coordinator:
    """创建协作者"""
    coordinator = Coordinator(agents, adjacency_matrix, architecture_type, config)
    return coordinator
