"""
消息生成器

在游戏循环中生成Agent之间的对话消息
使用LLM生成真实、个性化的对话内容
包含限流控制、批量处理和降级机制
"""

import random
import time
from typing import List, Dict, Optional
from datetime import datetime

from backend.models.agent import Agent
from backend.models.message import Message, MessageType
from backend.models.message_store import MessageStore, get_message_store
from backend.models.psychology_v2 import PsychologySystem, Trait
from backend.core.llm_dialogue_generator import (
    LLMDialogueGenerator, DialogueContext, create_llm_dialogue_generator
)


class MessageGenerator:
    """
    消息生成器

    负责在游戏循环中生成Agent之间的对话
    包含限流控制和批量处理机制
    """

    def __init__(self, civilization_id: str, store: MessageStore = None):
        """
        初始化消息生成器

        Args:
            civilization_id: 文明ID
            store: 消息存储实例
        """
        self.civilization_id = civilization_id
        self.store = store or get_message_store()
        self.dialogue_generator = create_llm_dialogue_generator()
        self.round_num = 0
        self.cycle_num = 0
        
        # 限流控制配置
        self.max_messages_per_cycle = 3  # 每轮循环最多生成的消息数
        self.enable_llm = True  # 是否启用LLM生成
        self.llm_request_delay = 0.5  # LLM请求间隔（秒）

    def set_round_cycle(self, round_num: int, cycle_num: int):
        """设置当前回合和循环"""
        self.round_num = round_num
        self.cycle_num = cycle_num

    def register_agents(self, agents: List[Agent]):
        """
        注册所有Agent，为每个Agent生成个性化提示词

        Args:
            agents: Agent列表
        """
        for agent in agents:
            traits = {
                'authority': agent.personality.authority,
                'selfishness': agent.personality.selfishness,
                'altruism': agent.personality.altruism,
                'sociability': agent.personality.sociability,
                'intelligence': agent.personality.intelligence,
                'risk_appetite': agent.personality.risk_appetite,
                'resilience': agent.personality.resilience,
                'loyalty_base': agent.personality.loyalty_base
            }

            self.dialogue_generator.register_agent(
                agent_id=agent.id,
                agent_name=agent.name,
                personality_traits=traits,
                role_description=agent.description
            )

    def generate_communications(
        self,
        agents: List[Agent],
        adjacency_matrix,
        recent_events: List[str] = None
    ) -> List[Message]:
        """
        生成一轮通讯（带限流控制）

        Args:
            agents: Agent列表
            adjacency_matrix: 邻接矩阵
            recent_events: 近期事件列表

        Returns:
            生成的消息列表
        """
        messages = []
        recent_events = recent_events or []
        
        # 收集所有可能的通讯对
        potential_communications = []
        
        for i, sender in enumerate(agents):
            for j, receiver in enumerate(agents):
                if i == j:
                    continue

                # 检查是否有连接
                if adjacency_matrix[i, j] <= 0:
                    continue

                # 根据Agent状态和关系决定是否发送消息
                if self._should_communicate(sender, receiver):
                    potential_communications.append((sender, receiver))
        
        # 限制每轮循环的消息数量，避免过多API调用
        if len(potential_communications) > self.max_messages_per_cycle:
            # 按优先级排序：内鬼通讯 > 高重要性通讯 > 普通通讯
            potential_communications = self._prioritize_communications(
                potential_communications
            )
            potential_communications = potential_communications[:self.max_messages_per_cycle]
        
        # 生成消息
        for sender, receiver in potential_communications:
            try:
                message = self._generate_message(
                    sender, receiver, agents, recent_events
                )
                if message:
                    messages.append(message)
                    self.store.save_message(message)
                    
                    # 在LLM请求之间添加延迟
                    if self.enable_llm:
                        time.sleep(self.llm_request_delay)
                        
            except Exception as e:
                print(f"生成消息失败 ({sender.name} -> {receiver.name}): {e}")
                continue

        return messages
    
    def _prioritize_communications(
        self,
        communications: List[tuple]
    ) -> List[tuple]:
        """
        按优先级排序通讯对
        
        Args:
            communications: (sender, receiver) 元组列表
            
        Returns:
            排序后的列表
        """
        def get_priority(item):
            sender, receiver = item
            priority = 0
            
            # 内鬼通讯优先级更高（更有趣）
            if sender.is_active_traitor:
                priority += 100
            
            # 高社交性Agent的通讯更有趣
            priority += sender.personality.sociability * 50
            
            # 高重要性关系
            trust_diff = abs(sender.trust_matrix_row.get(receiver.id, 0.5) - 0.5)
            priority += trust_diff * 30
            
            return priority
        
        return sorted(communications, key=get_priority, reverse=True)

    def _should_communicate(self, sender: Agent, receiver: Agent) -> bool:
        """
        判断是否应该发送消息

        Args:
            sender: 发送者
            receiver: 接收者

        Returns:
            是否应该通讯
        """
        # 基于社交性和通讯能量分配
        comm_probability = (
            sender.personality.sociability * 0.3 +
            (sender.state.energy_comm / 100) * 0.4 +
            sender.trust_matrix_row.get(receiver.id, 0.5) * 0.3
        )

        # 内鬼更倾向于与特定目标通讯
        if sender.is_active_traitor:
            if receiver.trust_matrix_row.get(sender.id, 0.5) > 0.6:
                comm_probability += 0.2  # 更容易与信任自己的人通讯

        return random.random() < comm_probability

    def _generate_message(
        self,
        sender: Agent,
        receiver: Agent,
        all_agents: List[Agent],
        recent_events: List[str]
    ) -> Optional[Message]:
        """
        生成单条消息

        Args:
            sender: 发送者
            receiver: 接收者
            all_agents: 所有Agent列表
            recent_events: 近期事件

        Returns:
            消息对象或None
        """
        # 确定消息类型
        message_type = self._determine_message_type(sender, receiver)

        # 确定关系
        relationship = self._determine_relationship(sender, receiver)

        # 获取信任水平
        trust_level = sender.trust_matrix_row.get(receiver.id, 0.5)

        # 创建对话上下文
        context = DialogueContext(
            relationship=relationship,
            trust_level=trust_level,
            recent_events=recent_events,
            communication_purpose=self._get_communication_purpose(message_type),
            stress_level=sender.state.cognitive_entropy
        )

        # 准备结构化数据
        structured_data = self._prepare_structured_data(sender, message_type)

        # 创建发送者的心理系统
        sender_psychology = self._create_psychology_system(sender)

        # 使用LLM生成消息
        try:
            message = self.dialogue_generator.generate_message(
                sender_id=sender.id,
                sender_name=sender.name,
                sender_psychology=sender_psychology,
                receiver_id=receiver.id,
                receiver_name=receiver.name,
                message_type=message_type,
                context=context,
                structured_data=structured_data
            )

            # 设置消息元数据
            message.civilization_id = self.civilization_id
            message.round_num = self.round_num
            message.cycle_num = self.cycle_num
            message.timestamp = datetime.now().isoformat()

            return message

        except Exception as e:
            print(f"生成消息失败: {e}")
            return None

    def _determine_message_type(self, sender: Agent, receiver: Agent) -> MessageType:
        """
        确定消息类型

        Args:
            sender: 发送者
            receiver: 接收者

        Returns:
            消息类型
        """
        trust = sender.trust_matrix_row.get(receiver.id, 0.5)

        # 根据状态和关系选择消息类型
        choices = []

        # 工作汇报（高权威感度）
        if sender.personality.authority > 0.6:
            choices.extend([MessageType.REPORT] * 2)

        # 请求帮助（高私心或低效率）
        if sender.personality.selfishness > 0.6 or sender.state.efficiency < 0.4:
            choices.append(MessageType.REQUEST)

        # 闲聊（高社交性）
        if sender.personality.sociability > 0.6:
            choices.extend([MessageType.CHAT] * 2)

        # 警告（高智力或检测到异常）
        if sender.personality.intelligence > 0.7:
            choices.append(MessageType.ALERT)

        # 说服（有特定目标）
        if sender.personality.authority > 0.5 and trust > 0.5:
            choices.append(MessageType.PERSUADE)

        # 操纵（内鬼行为）
        if sender.is_active_traitor and trust > 0.4:
            choices.append(MessageType.MANIPULATE)

        # 状态同步（默认）
        choices.extend([MessageType.STATUS] * 3)

        return random.choice(choices) if choices else MessageType.CHAT

    def _determine_relationship(self, sender: Agent, receiver: Agent) -> str:
        """
        确定两个Agent之间的关系

        Args:
            sender: 发送者
            receiver: 接收者

        Returns:
            关系类型字符串
        """
        # 基于位置和层级
        if sender.level < receiver.level:
            return "superior"
        elif sender.level > receiver.level:
            return "subordinate"

        # 基于中心性
        if sender.centrality > receiver.centrality + 0.2:
            return "superior"
        elif receiver.centrality > sender.centrality + 0.2:
            return "subordinate"

        # 基于信任
        trust = sender.trust_matrix_row.get(receiver.id, 0.5)
        if trust < 0.3:
            return "enemy"

        return "peer"

    def _get_communication_purpose(self, message_type: MessageType) -> str:
        """获取通讯目的描述"""
        purposes = {
            MessageType.REPORT: "汇报工作进展",
            MessageType.REQUEST: "请求资源或帮助",
            MessageType.STATUS: "同步当前状态",
            MessageType.CHAT: "建立关系或闲聊",
            MessageType.PERSUADE: "说服对方接受观点",
            MessageType.MANIPULATE: "暗中影响对方",
            MessageType.ALERT: "警告潜在危险",
            MessageType.CONFESSION: "坦白或道歉"
        }
        return purposes.get(message_type, "一般交流")

    def _prepare_structured_data(self, sender: Agent, message_type: MessageType) -> Dict:
        """
        准备结构化数据

        Args:
            sender: 发送者
            message_type: 消息类型

        Returns:
            结构化数据字典
        """
        data = {}

        if message_type == MessageType.REPORT:
            data["work_done"] = int(sender.state.energy_work * sender.state.efficiency / 10)
            data["contribution"] = sender.state.contribution
            data["efficiency"] = sender.state.efficiency

        elif message_type == MessageType.STATUS:
            data["progress"] = sender.state.energy / 100
            data["my_status"] = "正常" if sender.state.cognitive_entropy < 0.5 else "疲惫"

        elif message_type == MessageType.REQUEST:
            data["request_amount"] = random.randint(10, 50)
            data["request_reason"] = random.choice([
                "工作需要", "提高效率", "应对紧急情况", "补充资源"
            ])

        elif message_type == MessageType.ALERT:
            data["issues"] = random.choice([
                ["产出下降"], ["通讯异常"], ["有人行为可疑"], ["资源短缺"]
            ])

        return data

    def _create_psychology_system(self, agent: Agent) -> PsychologySystem:
        """
        为Agent创建心理系统

        Args:
            agent: Agent对象

        Returns:
            心理系统对象
        """
        from backend.models.psychology_v2 import PsychologySystem as PS

        psych = PsychologySystem(agent_id=agent.id)

        # 设置性格特质
        psych.state.cognitive_entropy = agent.state.cognitive_entropy
        psych.state.stress_level = agent.state.cognitive_entropy

        # 设置信任
        psych.state.trust_in_civilization = agent.personality.loyalty_base

        # 根据忠诚度设置行为倾向
        if agent.state.loyalty > 0.7:
            psych.state.cooperation_willingness = 0.8
        elif agent.state.loyalty < 0.3:
            psych.state.betrayal_willingness = 0.6

        return psych


def create_message_generator(
    civilization_id: str,
    store: MessageStore = None
) -> MessageGenerator:
    """
    创建消息生成器实例

    Args:
        civilization_id: 文明ID
        store: 消息存储实例

    Returns:
        消息生成器实例
    """
    return MessageGenerator(civilization_id, store)
