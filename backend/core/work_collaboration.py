"""
工作协作管理器

协调工作事件生成、角色分配、交互生成和结果评估
"""

import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from backend.models.agent import Agent
from backend.models.work_event import WorkEvent, WorkSession, WorkInteraction, WorkEventType, EventStatus
from backend.core.work_event_generator import WorkEventGenerator
from backend.core.work_interaction_generator import WorkInteractionGenerator


class WorkCollaborationManager:
    """工作协作管理器"""

    def __init__(self, seed: int = None):
        """初始化管理器"""
        self.rng = random.Random(seed)
        self.event_generator = WorkEventGenerator(seed=seed)
        self.interaction_generator = WorkInteractionGenerator(rng=self.rng)
        self.current_session: Optional[WorkSession] = None
        self.session_history: List[WorkSession] = []

    def process_work_collaboration(
        self,
        agents: List[Agent],
        game_state: Dict,
        traitor_active: bool = False
    ) -> Dict:
        """
        处理完整的工作协作流程

        Args:
            agents: 所有可用Agent
            game_state: 游戏状态字典
            traitor_active: 是否有活跃内鬼

        Returns:
            协作结果字典，包含评估和产出影响
        """
        # 1. 生成工作事件
        event = self.event_generator.generate_event(game_state, traitor_active)

        # 2. 分配角色
        coordinator, workers, helpers = self._assign_roles(agents, event)

        # 3. 生成工作会话（多轮交互）
        session = self.interaction_generator.generate_work_session(
            event=event,
            agents=agents,
            coordinator=coordinator,
            workers=workers,
            helpers=helpers
        )

        self.current_session = session
        self.session_history.append(session)

        # 4. 更新事件结果
        event.outcome_quality = session.verdict.get("overall_quality", 0.5)
        event.collaboration_score = session.verdict.get("collaboration_score", 0.5)
        event.output_bonus = self._calculate_output_bonus(event, session)

        # 5. 应用事件影响到Agent状态
        self._apply_event_impacts(agents, event, coordinator, workers, helpers)

        return {
            "event": event,
            "session": session,
            "output_bonus": event.output_bonus,
            "quality": event.outcome_quality,
            "collaboration_score": event.collaboration_score,
            "coordinator": coordinator,
            "workers": workers,
            "helpers": helpers
        }

    def _assign_roles(
        self,
        agents: List[Agent],
        event: WorkEvent
    ) -> Tuple[Agent, List[Agent], List[Agent]]:
        """
        根据Agent性格和能力分配角色

        Returns:
            (coordinator, workers, helpers)
        """
        # 计算每个Agent的角色得分
        coordinator_scores = []
        worker_scores = []
        helper_scores = []

        for agent in agents:
            # 协调者分 = 权威感 × 智力 × (1 - 工作量)
            coord_score = (
                agent.personality.authority *
                agent.personality.intelligence *
                (1 - agent.state.energy_work / 100)
            )

            # 执行者分 = 效率 × 韧性 × (1 - 忙碌度)
            worker_score = (
                agent.state.efficiency *
                agent.personality.resilience *
                (1 - agent.state.cognitive_entropy)
            )

            # 协助者分 = 利他 × 社交 × (1 - 私心)
            helper_score = (
                agent.personality.altruism *
                agent.personality.sociability *
                (1 - agent.personality.selfishness)
            )

            coordinator_scores.append((agent, coord_score))
            worker_scores.append((agent, worker_score))
            helper_scores.append((agent, helper_score))

        # 选择协调者（最高分）
        coordinator_scores.sort(key=lambda x: x[1], reverse=True)
        coordinator = coordinator_scores[0][0]

        # 选择执行者（排除协调者，按分数排序）
        available_workers = [(a, s) for a, s in worker_scores if a.id != coordinator.id]
        available_workers.sort(key=lambda x: x[1], reverse=True)
        num_workers = min(event.required_agents - 1, len(available_workers))
        workers = [a for a, _ in available_workers[:num_workers]]

        # 选择协助者（排除已选中的）
        available_helpers = [
            (a, s) for a, s in helper_scores
            if a.id != coordinator.id and a not in workers
        ]
        available_helpers.sort(key=lambda x: x[1], reverse=True)
        num_helpers = min(2, len(available_helpers))
        helpers = [a for a, _ in available_helpers[:num_helpers]]

        # 更新事件的参与者ID
        event.coordinator_id = coordinator.id
        event.worker_ids = [w.id for w in workers]
        event.helper_ids = [h.id for h in helpers]

        return coordinator, workers, helpers

    def _calculate_output_bonus(self, event: WorkEvent, session: WorkSession) -> float:
        """计算产出奖励系数"""
        base_bonus = 1.0
        quality = event.outcome_quality
        collaboration = event.collaboration_score

        # 高质量协作获得奖励
        if quality > 0.7 and collaboration > 0.6:
            return 1.3
        elif quality > 0.5:
            return 1.1
        elif quality < 0.3:
            return 0.7
        else:
            return 0.9

    def _apply_event_impacts(
        self,
        agents: List[Agent],
        event: WorkEvent,
        coordinator: Agent,
        workers: List[Agent],
        helpers: List[Agent]
    ):
        """应用事件影响到Agent状态"""
        bonus = event.output_bonus

        # 协调者获得额外贡献值
        coordinator.state.contribution += 0.5 * bonus

        # 执行者根据工作质量获得贡献
        for worker in workers:
            quality_factor = event.outcome_quality
            worker.state.contribution += 0.3 * quality_factor * bonus

        # 协助者获得少量贡献
        for helper in helpers:
            helper.state.contribution += 0.1 * bonus

        # 事件影响（如能量、凝聚力等）由调用方在engine中处理
        event.status = EventStatus.COMPLETED if event.outcome_quality > 0.4 else EventStatus.FAILED


def create_work_collaboration_manager(seed: int = None) -> WorkCollaborationManager:
    """创建工作协作管理器实例"""
    return WorkCollaborationManager(seed=seed)
