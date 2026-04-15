"""
工作事件生成器

根据游戏状态动态生成工作事件
"""

import random
from typing import List, Dict, Optional
from backend.models.work_event import WorkEvent, WorkEventType, EventSeverity


class WorkEventGenerator:
    """工作事件生成器"""

    # 事件模板
    EVENT_TEMPLATES = {
        WorkEventType.ROUTINE_TASK: [
            {
                "title": "完成本轮生产目标",
                "description": "本轮需要完成基础生产任务，维持文明运转",
                "severity": 0.3,
                "time_pressure": 0.3,
                "energy_impact": 0.1,
                "cohesion_impact": 0.0,
                "fidelity_impact": 0.0,
                "social_impact": 0.0
            },
            {
                "title": "提升团队效率",
                "description": "优化工作流程，提高整体产出效率",
                "severity": 0.4,
                "time_pressure": 0.4,
                "energy_impact": 0.15,
                "cohesion_impact": 0.05,
                "fidelity_impact": 0.0,
                "social_impact": 0.1
            },
            {
                "title": "扩展资源来源",
                "description": "寻找新的资源获取途径，保障长期发展",
                "severity": 0.5,
                "time_pressure": 0.5,
                "energy_impact": 0.2,
                "cohesion_impact": 0.1,
                "fidelity_impact": 0.0,
                "social_impact": 0.15
            }
        ],
        WorkEventType.CRISIS: [
            {
                "title": "产出急剧下降！",
                "description": "本轮产出比上轮下降超过20%，需要立即分析原因并制定对策",
                "severity": 0.8,
                "time_pressure": 0.9,
                "energy_impact": -0.2,
                "cohesion_impact": -0.1,
                "fidelity_impact": -0.1,
                "social_impact": -0.15
            },
            {
                "title": "通讯系统故障",
                "description": "部分 Agent 之间的通讯出现障碍，信息传递不畅",
                "severity": 0.7,
                "time_pressure": 0.7,
                "energy_impact": -0.1,
                "cohesion_impact": 0.0,
                "fidelity_impact": -0.25,
                "social_impact": -0.1
            },
            {
                "title": "资源枯竭警告",
                "description": "关键资源储备告急，需要紧急调配或寻找替代方案",
                "severity": 0.85,
                "time_pressure": 0.95,
                "energy_impact": -0.15,
                "cohesion_impact": -0.15,
                "fidelity_impact": 0.0,
                "social_impact": -0.2
            }
        ],
        WorkEventType.RESOURCE_ALLOCATION: [
            {
                "title": "如何分配下轮资源？",
                "description": "资源有限，需要决定优先保障哪些方面的发展",
                "severity": 0.5,
                "time_pressure": 0.5,
                "energy_impact": 0.1,
                "cohesion_impact": 0.1,
                "fidelity_impact": 0.0,
                "social_impact": 0.15
            },
            {
                "title": "预算调整决策",
                "description": "需要重新分配预算比例，影响各团队的发展",
                "severity": 0.55,
                "time_pressure": 0.55,
                "energy_impact": 0.05,
                "cohesion_impact": -0.1,
                "fidelity_impact": 0.05,
                "social_impact": -0.05
            }
        ],
        WorkEventType.TRAITOR_EXPOSED: [
            {
                "title": "发现可疑行为！",
                "description": "有 Agent 行为异常，可能存在内鬼活动",
                "severity": 0.9,
                "time_pressure": 0.8,
                "energy_impact": -0.1,
                "cohesion_impact": -0.25,
                "fidelity_impact": -0.2,
                "social_impact": -0.25
            },
            {
                "title": "信息泄露事件",
                "description": "重要信息疑似被泄露，需要追查源头",
                "severity": 0.75,
                "time_pressure": 0.7,
                "energy_impact": -0.05,
                "cohesion_impact": -0.15,
                "fidelity_impact": -0.3,
                "social_impact": -0.2
            }
        ],
        WorkEventType.COLLABORATION: [
            {
                "title": "联合行动机会",
                "description": "多个团队可以联合行动，获得额外效率加成",
                "severity": 0.4,
                "time_pressure": 0.3,
                "energy_impact": 0.2,
                "cohesion_impact": 0.15,
                "fidelity_impact": 0.1,
                "social_impact": 0.2
            },
            {
                "title": "经验分享会议",
                "description": "组织跨团队经验分享，提高整体能力",
                "severity": 0.35,
                "time_pressure": 0.25,
                "energy_impact": 0.15,
                "cohesion_impact": 0.2,
                "fidelity_impact": 0.15,
                "social_impact": 0.25
            }
        ]
    }

    def __init__(self, seed: int = None):
        """初始化事件生成器"""
        self.rng = random.Random(seed)

    def generate_event(
        self,
        game_state: Dict,
        traitor_active: bool = False
    ) -> WorkEvent:
        """
        根据游戏状态生成工作事件

        Args:
            game_state: 游戏状态字典，包含宏观变量等
            traitor_active: 是否有活跃内鬼

        Returns:
            生成的工作事件
        """
        # 根据游戏状态选择事件类型
        event_type = self._select_event_type(game_state, traitor_active)

        # 从模板中选择事件
        template = self._select_template(event_type, game_state)

        # 创建事件
        event = WorkEvent(
            event_type=event_type,
            title=template["title"],
            description=template["description"],
            severity=template["severity"],
            time_pressure=template["time_pressure"],
            energy_impact=template["energy_impact"],
            cohesion_impact=template["cohesion_impact"],
            fidelity_impact=template["fidelity_impact"],
            social_impact=template["social_impact"],
            required_agents=3
        )

        # 根据事件类型调整
        event = self._adjust_event_by_type(event, game_state)

        return event

    def _select_event_type(
        self,
        game_state: Dict,
        traitor_active: bool
    ) -> WorkEventType:
        """根据游戏状态选择事件类型"""
        weights = {
            WorkEventType.ROUTINE_TASK: 0.3,
            WorkEventType.CRISIS: 0.2,
            WorkEventType.RESOURCE_ALLOCATION: 0.15,
            WorkEventType.TRAITOR_EXPOSED: 0.0,
            WorkEventType.COLLABORATION: 0.15
        }

        # 如果有活跃内鬼，增加内鬼事件概率
        if traitor_active:
            weights[WorkEventType.TRAITOR_EXPOSED] = 0.2
            weights[WorkEventType.CRISIS] += 0.1

        # 根据宏观变量调整权重
        if game_state.get("energy_level", 0.5) < 0.3:
            weights[WorkEventType.CRISIS] += 0.15
            weights[WorkEventType.ROUTINE_TASK] -= 0.1

        if game_state.get("cohesion", 0.5) < 0.4:
            weights[WorkEventType.RESOURCE_ALLOCATION] += 0.1

        # 归一化权重
        total = sum(weights.values())
        normalized_weights = {k: v / total for k, v in weights.items()}

        # 随机选择
        roll = self.rng.random()
        cumulative = 0
        for event_type, weight in normalized_weights.items():
            cumulative += weight
            if roll < cumulative:
                return event_type

        return WorkEventType.ROUTINE_TASK

    def _select_template(
        self,
        event_type: WorkEventType,
        game_state: Dict
    ) -> Dict:
        """从模板中选择具体事件"""
        templates = self.EVENT_TEMPLATES.get(event_type, [])
        if not templates:
            templates = self.EVENT_TEMPLATES[WorkEventType.ROUTINE_TASK]

        return self.rng.choice(templates)

    def _adjust_event_by_type(
        self,
        event: WorkEvent,
        game_state: Dict
    ) -> WorkEvent:
        """根据游戏状态调整事件参数"""
        # 根据严重程度调整参与人数
        if event.severity > 0.7:
            event.required_agents = 5
        elif event.severity > 0.5:
            event.required_agents = 4
        else:
            event.required_agents = 3

        # 危机事件需要协调者
        if event.event_type == WorkEventType.CRISIS:
            event.recommended_roles = ["coordinator", "analyst"]

        # 资源分配需要财务人员
        elif event.event_type == WorkEventType.RESOURCE_ALLOCATION:
            event.recommended_roles = ["coordinator", "executor"]

        # 协作机会鼓励多方参与
        elif event.event_type == WorkEventType.COLLABORATION:
            event.required_agents = 4

        return event

    def generate_batch(
        self,
        game_state: Dict,
        traitor_active: bool = False,
        count: int = 1
    ) -> List[WorkEvent]:
        """批量生成事件"""
        events = []
        for _ in range(count):
            events.append(self.generate_event(game_state, traitor_active))
        return events
