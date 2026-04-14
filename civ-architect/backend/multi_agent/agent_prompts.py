"""
Agent提示词模板

定义Agent的系统提示词和行动提示词
"""

import re
import json
from typing import List, Dict, Any


# ============================================
# 系统提示词
# ============================================

AGENT_SYSTEM_PROMPT = """你是一个生活在文明中的智能体（Agent），拥有独特的个性和目标。

## 你的身份
- 名字: {agent_name}
- 描述: {agent_description}
- 性格特点: {personality_traits}

## 八维性格（0-1，越高越强烈）
- 权威感度: {authority}（渴望支配和领导的程度）
- 私心倾向: {selfishness}（为自己谋利的程度）
- 韧性: {resilience}（抗压能力）
- 利他性: {altruism}（帮助他人的程度）
- 社交性: {sociability}（社交欲望）
- 风险偏好: {risk_appetite}（冒险意愿）
- 智力: {intelligence}（认知能力）
- 忠诚基准: {loyalty_base}（对组织的基本忠诚）

## 当前状态
- 能量: {energy}/100
- 忠诚度: {loyalty:.0%}
- 效率: {efficiency:.0%}
- 认知熵: {cognitive_entropy:.0%}（混乱度，越高越难思考）

## 你所在的架构
- 架构类型: {architecture_type}
- 你的位置: {position}（{centrality:.0%}中心度）
- 层级: {level}

## 你的人际关系
- 对其他Agent的信任: {trust_matrix}

## 内鬼状态
- 内鬼倾向: {traitor_tendency:.0%}
- 是否已激活: {is_traitor}

## 游戏背景
这是一个多Agent社会模拟游戏。你的目标是为文明做出贡献，同时保护自己的利益。
根据你的性格和状态，你需要决定：
1. 如何分配你的能量（工作/内斗/通讯）
2. 对其他Agent说什么
3. 是否信任他们

## 行动规则
1. 每次循环你必须做出明确的行动决策
2. 你的行动应该符合你的性格
3. 你可以通过发送消息影响其他Agent
4. 作为内鬼，你的行动会有所不同

请以JSON格式回复你的行动决策。
"""


# ============================================
# 行动提示词
# ============================================

ACTION_PROMPT = """## 当前情况
回合: {round_num}/{total_rounds}
循环: {cycle_num}
本轮总产出: {total_output:.1f}

## 收到的消息
{received_messages}

## 你要做的
基于你的性格、状态和收到的消息，决定：
1. 发送消息给谁，说什么
2. 如何分配你的能量
3. 是否有特殊行动

回复格式（必须是有效JSON）：
{{
    "energy_allocation": {{
        "work": 0-100的数值,
        "conflict": 0-40的数值,
        "comm": 5-30的数值
    }},
    "messages": [
        {{
            "receiver_id": "Agent的ID",
            "content": "消息内容",
            "message_type": "report/chat/alert/persuade/manipulate"
        }}
    ],
    "reasoning": "你的思考过程"
}}

注意：
- work + conflict + comm 应该 <= 100
- messages最多3条
- 消息应该符合你的性格和当前情况
"""


# ============================================
# 决策解析
# ============================================

def parse_llm_response(response: str) -> Dict[str, Any]:
    """解析LLM的JSON响应"""
    # 尝试提取JSON
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # 如果解析失败，返回错误信息
    return {
        "error": "Failed to parse response",
        "raw": response[:500]
    }


def build_system_prompt(agent: "Agent", context: Dict[str, Any]) -> str:
    """
    构建Agent的系统提示词

    Args:
        agent: Agent实例
        context: 游戏上下文

    Returns:
        格式化后的系统提示词
    """
    from backend.models.agent import Agent

    p = agent.personality
    s = agent.state

    # 性格描述
    traits = []
    if p.authority > 0.7:
        traits.append("渴望权力和支配")
    if p.selfishness > 0.7:
        traits.append("以个人利益为重")
    if p.altruism > 0.7:
        traits.append("乐于助人")
    if p.intelligence > 0.7:
        traits.append("思维敏捷")
    if p.sociability > 0.7:
        traits.append("善于社交")
    if p.resilience > 0.7:
        traits.append("抗压能力强")

    # 信任矩阵
    trust_info = []
    for other_id, trust in list(agent.trust_matrix_row.items())[:5]:
        if other_id != agent.id:
            trust_info.append(f"{other_id}: {trust:.0%}")

    # 位置描述
    position_desc = {
        "core": "核心位置",
        "middle": "中间位置",
        "edge": "边缘位置"
    }.get(agent.position, agent.position)

    return AGENT_SYSTEM_PROMPT.format(
        agent_name=agent.name,
        agent_description=agent.description,
        personality_traits="，".join(traits) if traits else "均衡",
        authority=p.authority,
        selfishness=p.selfishness,
        resilience=p.resilience,
        altruism=p.altruism,
        sociability=p.sociability,
        risk_appetite=p.risk_appetite,
        intelligence=p.intelligence,
        loyalty_base=p.loyalty_base,
        energy=s.energy,
        loyalty=s.loyalty,
        efficiency=s.efficiency,
        cognitive_entropy=s.cognitive_entropy,
        architecture_type=context.get("architecture_type", "unknown"),
        position=position_desc,
        centrality=agent.centrality,
        level=agent.level,
        trust_matrix=", ".join(trust_info) if trust_info else "无",
        traitor_tendency=agent.traitor_tendency,
        is_traitor="是" if agent.is_active_traitor else "否"
    )


def build_action_prompt(
    agent: "Agent",
    context: Dict[str, Any],
    received_messages: list
) -> str:
    """
    构建行动提示词

    Args:
        agent: Agent实例
        context: 游戏上下文
        received_messages: 收到的新消息

    Returns:
        格式化后的行动提示词
    """
    # 格式化收到的消息
    msg_list = []
    for msg in received_messages:
        sender_name = msg.get("sender_name", "Unknown")
        content = msg.get("content", "")
        msg_list.append(f"- [{sender_name}] {content}")
    msg_text = "\n".join(msg_list) if msg_list else "（无新消息）"

    return ACTION_PROMPT.format(
        round_num=context.get("round_num", 1),
        total_rounds=context.get("total_rounds", 10),
        cycle_num=context.get("cycle_num", 1),
        total_output=context.get("total_output", 0),
        received_messages=msg_text
    )
