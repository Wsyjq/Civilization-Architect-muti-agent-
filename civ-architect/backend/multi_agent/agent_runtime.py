"""
Agent运行时

每个Agent的LLM推理引擎
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import uuid
import json

from backend.core.llm_config import get_llm_manager, LLMConfig
from backend.multi_agent.agent_prompts import (
    build_system_prompt,
    build_action_prompt,
    parse_llm_response
)
from backend.multi_agent.message_broker import Message, MessageBroker, get_message_broker


@dataclass
class AgentAction:
    """Agent的行动"""
    agent_id: str
    energy_allocation: Dict[str, float]  # work, conflict, comm
    messages: List[Dict[str, str]]     # 要发送的消息列表
    reasoning: str = ""
    raw_response: str = ""


class AgentRuntime:
    """
    Agent运行时

    为每个Agent提供：
    - LLM推理
    - 消息处理
    - 状态管理
    """

    def __init__(
        self,
        agent_id: str,
        agent,
        llm_config: Optional[LLMConfig] = None,
        message_broker: Optional[MessageBroker] = None
    ):
        self.agent_id = agent_id
        self.agent = agent  # Agent模型实例

        # LLM管理器
        self._llm = get_llm_manager()

        # 消息代理
        self._broker = message_broker or get_message_broker()

        # 对话历史
        self._history: List[Dict[str, Any]] = []

        # Agent名称解析器
        self._broker.set_agent_name_resolver(self._resolve_agent_name)

        # 超时配置
        self.timeout = 120

    def _resolve_agent_name(self, agent_id: str) -> str:
        """解析Agent名称"""
        if agent_id == self.agent_id:
            return self.agent.name
        # 从其他Agent获取名称
        from backend.core.engine import GameEngine
        for civ in getattr(GameEngine, '_instances', {}).values():
            for a in civ.agents:
                if a.id == agent_id:
                    return a.name
        return agent_id

    async def think(self, context: Dict[str, Any]) -> AgentAction:
        """
        Agent思考：决定行动

        Args:
            context: 游戏上下文（回合数、循环数、宏观变量等）

        Returns:
            AgentAction: Agent的决定
        """
        # 构建提示词
        system_prompt = build_system_prompt(self.agent, context)

        # 获取收到的新消息
        received = self._broker.get_messages(self.agent_id)
        received_data = [msg.to_dict() for msg in received]
        action_prompt = build_action_prompt(self.agent, context, received_data)

        # 组合消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": action_prompt}
        ]

        # 添加历史（最近5轮）
        for hist_msg in self._history[-10:]:
            messages.append(hist_msg)

        # 调用LLM
        try:
            response = await self._llm.arun(
                self.agent_id,
                messages,
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            # 超时，使用默认行动
            response = self._get_fallback_action()
        except Exception as e:
            print(f"LLM error for {self.agent_id}: {e}")
            response = self._get_fallback_action()

        # 解析响应
        result = parse_llm_response(response)

        if "error" in result:
            # 解析失败，使用默认行动
            return self._get_fallback_action()

        # 记录到历史
        self._history.append({"role": "assistant", "content": response})
        if len(self._history) > 20:
            self._history = self._history[-20:]

        return AgentAction(
            agent_id=self.agent_id,
            energy_allocation=result.get("energy_allocation", {"work": 50, "conflict": 20, "comm": 10}),
            messages=result.get("messages", []),
            reasoning=result.get("reasoning", ""),
            raw_response=response
        )

    def speak(self, action: AgentAction):
        """
        Agent发送消息

        Args:
            action: AgentAction包含要发送的消息
        """
        for msg_data in action.messages:
            receiver_id = msg_data.get("receiver_id")
            content = msg_data.get("content", "")
            msg_type = msg_data.get("message_type", "chat")

            if receiver_id and content:
                # 检查连接关系
                connected = self._get_connected_agents()
                if receiver_id in connected or receiver_id == "all":
                    self._broker.publish(Message(
                        message_id=str(uuid.uuid4())[:8],
                        sender_id=self.agent_id,
                        sender_name=self.agent.name,
                        receiver_id=receiver_id,
                        receiver_name=self._resolve_agent_name(receiver_id),
                        content=content,
                        message_type=msg_type,
                        importance=0.5
                    ))

    def _get_connected_agents(self) -> List[str]:
        """获取有连接的其他Agent ID"""
        # 需要从游戏引擎获取邻接矩阵信息
        return []  # 暂时返回空，由coordinator处理

    def _get_fallback_action(self) -> AgentAction:
        """获取默认行动（当LLM失败时）"""
        return AgentAction(
            agent_id=self.agent_id,
            energy_allocation={"work": 50, "conflict": 20, "comm": 10},
            messages=[],
            reasoning="LLM调用失败，使用默认行动"
        )

    def listen(self) -> List[Message]:
        """
        获取收到的消息

        Returns:
            消息列表
        """
        return self._broker.pop_messages(self.agent_id)

    def update_state(self, new_state: Dict[str, Any]):
        """
        更新Agent状态（由引擎调用）

        Args:
            new_state: 新的状态数据
        """
        # 更新能量
        if "energy" in new_state:
            self.agent.state.energy = new_state["energy"]

        # 更新忠诚度
        if "loyalty" in new_state:
            self.agent.state.loyalty = new_state["loyalty"]

        # 更新效率
        if "efficiency" in new_state:
            self.agent.state.efficiency = new_state["efficiency"]

    def get_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return list(self._history)


# Agent运行时存储
_agent_runtimes: Dict[str, AgentRuntime] = {}


def get_agent_runtime(agent_id: str) -> Optional[AgentRuntime]:
    """获取Agent运行时"""
    return _agent_runtimes.get(agent_id)


def create_agent_runtime(agent) -> AgentRuntime:
    """为Agent创建运行时"""
    runtime = AgentRuntime(agent.id, agent)
    _agent_runtimes[agent.id] = runtime
    return runtime


def remove_agent_runtime(agent_id: str):
    """移除Agent运行时"""
    if agent_id in _agent_runtimes:
        del _agent_runtimes[agent_id]


def clear_all_runtimes():
    """清除所有运行时"""
    _agent_runtimes.clear()
