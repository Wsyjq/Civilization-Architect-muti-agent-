"""
工作交互生成器

基于 LLM 生成多轮工作对话
"""

import random
from typing import List, Dict, Optional
from datetime import datetime

from backend.models.agent import Agent
from backend.models.work_event import WorkEvent, WorkSession, WorkInteraction
from backend.core.llm_service import get_llm_service


class WorkInteractionGenerator:
    """工作交互生成器"""

    def __init__(self, rng: random.Random = None):
        """初始化生成器"""
        self.rng = rng or random.Random()
        self.llm = get_llm_service()

    def generate_work_session(
        self,
        event: WorkEvent,
        agents: List[Agent],
        coordinator: Agent,
        workers: List[Agent],
        helpers: List[Agent]
    ) -> WorkSession:
        """
        生成完整的工作会话

        Args:
            event: 工作事件
            agents: 所有可用 Agent
            coordinator: 协调者
            workers: 执行者列表
            helpers: 协助者列表

        Returns:
            完整的工作会话
        """
        session = WorkSession(
            event=event,
            round_num=0,
            participants=[coordinator.id] + [w.id for w in workers] + [h.id for h in helpers],
            coordinator_id=coordinator.id,
            worker_ids=[w.id for w in workers],
            helper_ids=[h.id for h in helpers]
        )

        # 构建参与者和角色映射
        agent_map = {a.id: a for a in agents}

        # 生成多轮交互
        interaction_rounds = 3  # 问题分析、方案讨论、协调确认

        for round_num in range(1, interaction_rounds + 1):
            interactions = self._generate_round_interactions(
                session=session,
                round_num=round_num,
                coordinator=coordinator,
                workers=workers,
                helpers=helpers,
                agent_map=agent_map
            )
            session.interactions.extend(interactions)

        # 生成最终方案
        session.final_plan = self._generate_final_plan(session)
        session.verdict = self._evaluate_session(session)

        return session

    def _generate_round_interactions(
        self,
        session: WorkSession,
        round_num: int,
        coordinator: Agent,
        workers: List[Agent],
        helpers: List[Agent],
        agent_map: Dict[str, Agent]
    ) -> List[WorkInteraction]:
        """生成一轮交互"""
        interactions = []
        event = session.event

        # 根据轮次决定交互模式
        if round_num == 1:
            # 第一轮：问题分析
            # 分析师发言
            analyst = self._find_agent_by_trait(workers, 'intelligence')
            if analyst:
                content = self._generate_analysis(coordinator, event, session.interactions)
                interactions.append(self._create_interaction(
                    session, round_num, analyst, content, "propose"
                ))

            # 协调者总结
            content = self._generate_coordinator_summary(coordinator, event, interactions)
            interactions.append(self._create_interaction(
                session, round_num, coordinator, content, "confirm"
            ))

            # 工人补充
            worker = workers[0] if workers else coordinator
            content = self._generate_worker_input(worker, event, session.interactions)
            interactions.append(self._create_interaction(
                session, round_num, worker, content, "propose"
            ))

        elif round_num == 2:
            # 第二轮：方案讨论
            # 协调者提出方案
            content = self._generate_proposal(coordinator, event, session.interactions)
            interactions.append(self._create_interaction(
                session, round_num, coordinator, content, "propose"
            ))

            # 工人评估
            worker = workers[0] if workers else coordinator
            content = self._generate_evaluation(worker, event, session.interactions)
            interactions.append(self._create_interaction(
                session, round_num, worker, content, "agree"
            ))

            # 协助者建议
            if helpers:
                helper = helpers[0]
                content = self._generate_helper_suggestion(helper, event, session.interactions)
                interactions.append(self._create_interaction(
                    session, round_num, helper, content, "request"
                ))

        else:
            # 第三轮：协调确认
            # 协调者确认分工
            content = self._generate_assignment_confirm(coordinator, event, session.interactions)
            interactions.append(self._create_interaction(
                session, round_num, coordinator, content, "confirm"
            ))

            # 工人确认
            worker = workers[0] if workers else coordinator
            content = self._generate_worker_confirm(worker, event, session.interactions)
            interactions.append(self._create_interaction(
                session, round_num, worker, content, "agree"
            ))

        return interactions

    def _create_interaction(
        self,
        session: WorkSession,
        round_num: int,
        agent: Agent,
        content: str,
        action_type: str
    ) -> WorkInteraction:
        """创建交互对象"""
        # 确定角色
        if agent.id == session.coordinator_id:
            role = "coordinator"
        elif agent.id in session.worker_ids:
            role = "worker"
        else:
            role = "helper"

        # 评估质量
        quality = self._evaluate_interaction_quality(content, action_type, agent)

        return WorkInteraction(
            event_id=session.event.id,
            round_num=round_num,
            speaker_id=agent.id,
            speaker_name=agent.name,
            speaker_role=role,
            content=content,
            action_type=action_type,
            work_quality=quality["work_quality"],
            coordination_quality=quality["coordination_quality"],
            collaboration_value=quality["collaboration_value"],
            timestamp=datetime.now().isoformat()
        )

    def _evaluate_interaction_quality(
        self,
        content: str,
        action_type: str,
        agent: Agent
    ) -> Dict[str, float]:
        """评估交互质量"""
        base_quality = 0.5 + 0.3 * agent.personality.intelligence

        if action_type in ["propose", "agree"]:
            work_quality = base_quality + 0.2
        elif action_type == "confirm":
            work_quality = base_quality + 0.1
        else:
            work_quality = base_quality - 0.1

        coordination = 0.5 + 0.2 * agent.personality.authority

        collaboration = (
            0.5 +
            0.2 * agent.personality.altruism +
            0.2 * agent.personality.sociability
        )

        return {
            "work_quality": max(0, min(1, work_quality)),
            "coordination_quality": max(0, min(1, coordination)),
            "collaboration_value": max(0, min(1, collaboration))
        }

    def _find_agent_by_trait(self, agents: List[Agent], trait: str) -> Optional[Agent]:
        """找到具有特定性格特征的 Agent"""
        if not agents:
            return None
        return max(agents, key=lambda a: getattr(a.personality, trait, 0))

    def _generate_analysis(
        self,
        agent: Agent,
        event: WorkEvent,
        previous_interactions: List[WorkInteraction]
    ) -> str:
        """生成问题分析发言"""
        # 构建上下文
        context = self._build_context(agent, event)

        # 构建对话历史
        history = self._format_history(previous_interactions)

        prompt = f"""你是【{agent.name}】，当前面临一个工作事件需要分析。

【你的性格特点】
- 智力: {agent.personality.intelligence:.0%}
- 权威感: {agent.personality.authority:.0%}
- 私心: {agent.personality.selfishness:.0%}
- 利他: {agent.personality.altruism:.0%}

【当前事件】
标题: {event.title}
描述: {event.description}
严重程度: {event.severity:.0%}

{context}

请生成一段符合你性格的问题分析发言。要求：
1. 50-100字，口语化自然
2. 体现你的智力分析能力
3. 指出问题的关键点
4. 不要敷衍，要有实质性分析"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                use_mock_on_failure=True
            )
            return response.strip()
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return self._fallback_analysis(agent, event)

    def _generate_coordinator_summary(
        self,
        agent: Agent,
        event: WorkEvent,
        interactions: List[WorkInteraction]
    ) -> str:
        """生成协调者总结"""
        context = self._build_context(agent, event)

        prompt = f"""你是【{agent.name}】，作为协调者，你需要总结团队的分析。

【你的性格特点】
- 权威感: {agent.personality.authority:.0%}
- 智力: {agent.personality.intelligence:.0%}
- 社交: {agent.personality.sociability:.0%}

【当前事件】
标题: {event.title}
描述: {event.description}

{context}

请生成一段协调者风格的总结发言。要求：
1. 50-100字
2. 体现领导力和协调能力
3. 确认团队的分析方向
4. 口语化自然"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                use_mock_on_failure=True
            )
            return response.strip()
        except Exception as e:
            return self._fallback_coordinator(agent, event)

    def _generate_proposal(
        self,
        agent: Agent,
        event: WorkEvent,
        previous_interactions: List[WorkInteraction]
    ) -> str:
        """生成方案提议"""
        context = self._build_context(agent, event)
        history = self._format_history(previous_interactions)

        prompt = f"""你是【{agent.name}】，作为协调者，你需要提出一个解决方案。

【你的性格特点】
- 权威感: {agent.personality.authority:.0%}
- 智力: {agent.personality.intelligence:.0%}
- 风险偏好: {agent.personality.risk_appetite:.0%}

【当前事件】
标题: {event.title}
描述: {event.description}
严重程度: {event.severity:.0%}

{context}

【之前的讨论】
{history}

请生成一个具体的工作方案提议。要求：
1. 80-120字
2. 提出明确的行动方案
3. 考虑资源分配和时间安排
4. 符合你的性格特征"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                use_mock_on_failure=True
            )
            return response.strip()
        except Exception as e:
            return self._fallback_proposal(agent, event)

    def _generate_evaluation(
        self,
        agent: Agent,
        event: WorkEvent,
        previous_interactions: List[WorkInteraction]
    ) -> str:
        """生成方案评估"""
        context = self._build_context(agent, event)
        history = self._format_history(previous_interactions)

        prompt = f"""你是【{agent.name}】，作为执行者，你需要评估提出的方案。

【你的性格特点】
- 效率: 基于 {agent.personality.intelligence:.0%} 智力
- 韧性: {agent.personality.resilience:.0%}
- 忠诚: {agent.personality.loyalty_base:.0%}

【当前事件】
标题: {event.title}

{context}

【方案内容】
{history}

请生成一段方案评估发言。要求：
1. 50-100字
2. 分析方案的可行性和风险
3. 提出建设性意见
4. 符合执行者的务实风格"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                use_mock_on_failure=True
            )
            return response.strip()
        except Exception as e:
            return self._fallback_evaluation(agent, event)

    def _generate_helper_suggestion(
        self,
        agent: Agent,
        event: WorkEvent,
        previous_interactions: List[WorkInteraction]
    ) -> str:
        """生成协助者建议"""
        context = self._build_context(agent, event)

        prompt = f"""你是【{agent.name}】，作为协助者，你可以提供额外支持。

【你的性格特点】
- 利他: {agent.personality.altruism:.0%}
- 社交: {agent.personality.sociability:.0%}
- 效率: {agent.personality.intelligence:.0%}

【当前事件】
标题: {event.title}

{context}

请生成一段协助者风格的建议发言。要求：
1. 50-80字
2. 表达协助意愿
3. 提供具体的帮助方案
4. 体现利他精神"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                use_mock_on_failure=True
            )
            return response.strip()
        except Exception as e:
            return self._fallback_helper(agent, event)

    def _generate_assignment_confirm(
        self,
        agent: Agent,
        event: WorkEvent,
        previous_interactions: List[WorkInteraction]
    ) -> str:
        """生成任务分配确认"""
        context = self._build_context(agent, event)

        prompt = f"""你是【{agent.name}】，作为协调者，需要确认最终的任务分配。

【你的性格特点】
- 权威感: {agent.personality.authority:.0%}
- 决断力: {'高' if agent.personality.authority > 0.6 else '中等'}

【当前事件】
标题: {event.title}

{context}

请生成一段任务分配确认发言。要求：
1. 50-100字
2. 明确各人职责
3. 强调执行要点
4. 体现协调者的决断力"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                use_mock_on_failure=True
            )
            return response.strip()
        except Exception as e:
            return self._fallback_assignment(agent, event)

    def _generate_worker_input(
        self,
        agent: Agent,
        event: WorkEvent,
        previous_interactions: List[WorkInteraction]
    ) -> str:
        """生成工人输入"""
        context = self._build_context(agent, event)

        prompt = f"""你是【{agent.name}】，作为执行者，分享你的看法。

【你的性格特点】
- 效率优先: 基于智力 {agent.personality.intelligence:.0%}
- 韧性: {agent.personality.resilience:.0%}
- 私心: {agent.personality.selfishness:.0%}

【当前事件】
标题: {event.title}

{context}

请生成一段执行者风格的工作输入。要求：
1. 40-80字
2. 务实、直接
3. 关注执行细节
4. 符合你的性格特征"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                use_mock_on_failure=True
            )
            return response.strip()
        except Exception as e:
            return self._fallback_worker(agent, event)

    def _generate_worker_confirm(
        self,
        agent: Agent,
        event: WorkEvent,
        previous_interactions: List[WorkInteraction]
    ) -> str:
        """生成工人确认"""
        context = self._build_context(agent, event)

        prompt = f"""你是【{agent.name}】，确认你的任务。

【你的性格特点】
- 忠诚: {agent.personality.loyalty_base:.0%}
- 效率: {agent.personality.intelligence:.0%}

【当前事件】
标题: {event.title}

{context}

请生成一段简洁的任务确认发言。要求：
1. 30-60字
2. 表达接受任务
3. 简述执行计划
4. 体现你的执行力"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                use_mock_on_failure=True
            )
            return response.strip()
        except Exception as e:
            return self._fallback_confirm(agent, event)

    def _generate_final_plan(self, session: WorkSession) -> Dict:
        """生成最终方案"""
        # 简单生成方案摘要
        event = session.event
        coordinator = session.coordinator_id

        return {
            "title": f"{event.title} - 执行方案",
            "coordinator": coordinator,
            "workers": session.worker_ids,
            "helpers": session.helper_ids,
            "task_summary": "根据协作讨论，制定了具体执行方案",
            "expected_outcome": "完成工作任务，提升文明产出"
        }

    def _evaluate_session(self, session: WorkSession) -> Dict:
        """评估会话质量"""
        if not session.interactions:
            return {
                "overall_quality": 0.5,
                "collaboration_score": 0.5,
                "consensus_reached": False
            }

        # 计算平均质量
        avg_work = sum(i.work_quality for i in session.interactions) / len(session.interactions)
        avg_coord = sum(i.coordination_quality for i in session.interactions) / len(session.interactions)
        avg_collab = sum(i.collaboration_value for i in session.interactions) / len(session.interactions)

        overall = (avg_work + avg_coord + avg_collab) / 3
        collaboration = (avg_coord + avg_collab) / 2

        return {
            "overall_quality": overall,
            "collaboration_score": collaboration,
            "consensus_reached": overall > 0.5,
            "work_quality": avg_work,
            "coordination_quality": avg_coord,
            "interaction_count": len(session.interactions)
        }

    def _build_context(self, agent: Agent, event: WorkEvent) -> str:
        """构建上下文描述"""
        return f"""
【你的角色信息】
- 名称: {agent.name}
- 描述: {agent.description}
- 位置: {agent.position} (核心/中层/边缘)
- 中心性: {agent.centrality:.0%}

【当前工作状态】
- 体力: {agent.state.energy:.0f}/100
- 效率: {agent.state.efficiency:.0%}
- 忠诚度: {agent.state.loyalty:.0%}
- 认知熵: {agent.state.cognitive_entropy:.0%}

【事件信息】
- 类型: {event.event_type.value}
- 严重程度: {event.severity:.0%}
- 时间压力: {event.time_pressure:.0%}
"""

    def _format_history(self, interactions: List[WorkInteraction]) -> str:
        """格式化对话历史"""
        if not interactions:
            return "（暂无历史讨论）"

        history = []
        for i in interactions[-6:]:  # 最近6条
            history.append(f"[{i.speaker_name}]({i.speaker_role}): {i.content[:100]}...")

        return "\n".join(history)

    # 备用生成方法（LLM 失败时）
    def _fallback_analysis(self, agent: Agent, event: WorkEvent) -> str:
        """备用分析"""
        return f"根据我的观察，{event.title}的核心问题在于资源配置不合理。建议先从基础数据入手，分析产出下降的具体原因，再制定针对性的解决方案。"

    def _fallback_coordinator(self, agent: Agent, event: WorkEvent) -> str:
        return f"大家的分析很有见地。综合来看，{event.description[:20]}...我认为应该优先处理最紧急的问题。"

    def _fallback_proposal(self, agent: Agent, event: WorkEvent) -> str:
        return f"我建议分三步走：第一步稳定局面，第二步分析根因，第三步制定长期方案。具体分工我来协调，大家配合执行。"

    def _fallback_evaluation(self, agent: Agent, event: WorkEvent) -> str:
        return f"方案整体可行，但需要考虑时间压力。建议简化流程，优先保证核心任务完成。"

    def _fallback_helper(self, agent: Agent, event: WorkEvent) -> str:
        return f"我可以协助处理辅助工作，有需要随时沟通。"

    def _fallback_assignment(self, agent: Agent, event: WorkEvent) -> str:
        return f"好，就这么办。你负责核心执行，我负责协调。有问题随时汇报。"

    def _fallback_worker(self, agent: Agent, event: WorkEvent) -> str:
        return f"明白，我会按计划执行。"

    def _fallback_confirm(self, agent: Agent, event: WorkEvent) -> str:
        return f"收到，保证完成任务。"
