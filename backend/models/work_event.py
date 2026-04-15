"""
工作事件模型

定义工作事件的类型、结构和状态
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import uuid


class WorkEventType(Enum):
    """工作事件类型"""
    ROUTINE_TASK = "routine_task"           # 常规任务
    CRISIS = "crisis"                       # 突发危机
    RESOURCE_ALLOCATION = "resource"         # 资源分配
    TRAITOR_EXPOSED = "traitor"             # 内鬼暴露
    COLLABORATION = "collaboration"         # 协作机会


class EventSeverity(Enum):
    """事件严重程度"""
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    CRITICAL = 0.9


class EventStatus(Enum):
    """事件状态"""
    PENDING = "pending"       # 待处理
    IN_PROGRESS = "in_progress"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败


@dataclass
class WorkEvent:
    """工作事件"""
    id: str = field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8]}")
    event_type: WorkEventType = WorkEventType.ROUTINE_TASK
    title: str = ""
    description: str = ""
    severity: float = 0.5  # 0-1

    # 时间压力
    time_pressure: float = 0.5  # 0-1
    deadline: Optional[int] = None  # 截止回合

    # 参与要求
    required_agents: int = 3
    recommended_roles: List[str] = field(default_factory=list)

    # 当前状态
    status: EventStatus = EventStatus.PENDING

    # 关联的工作组
    coordinator_id: Optional[str] = None  # 协调者
    worker_ids: List[str] = field(default_factory=list)  # 执行者
    helper_ids: List[str] = field(default_factory=list)  # 协助者

    # 事件影响
    energy_impact: float = 0.0     # 对能级的影响
    cohesion_impact: float = 0.0  # 对凝聚力的影响
    fidelity_impact: float = 0.0  # 对保真度的影响
    social_impact: float = 0.0    # 对社会资本的影响

    # 结果
    outcome_quality: float = 0.0  # 方案质量 0-1
    collaboration_score: float = 0.0  # 协作评分 0-1
    output_bonus: float = 1.0    # 产出奖励系数

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "time_pressure": self.time_pressure,
            "deadline": self.deadline,
            "required_agents": self.required_agents,
            "recommended_roles": self.recommended_roles,
            "status": self.status.value,
            "coordinator_id": self.coordinator_id,
            "worker_ids": self.worker_ids,
            "helper_ids": self.helper_ids,
            "energy_impact": self.energy_impact,
            "cohesion_impact": self.cohesion_impact,
            "fidelity_impact": self.fidelity_impact,
            "social_impact": self.social_impact,
            "outcome_quality": self.outcome_quality,
            "collaboration_score": self.collaboration_score,
            "output_bonus": self.output_bonus
        }


@dataclass
class WorkInteraction:
    """工作交互"""
    id: str = field(default_factory=lambda: f"INT-{uuid.uuid4().hex[:8]}")
    event_id: str = ""
    round_num: int = 0

    # 发言者
    speaker_id: str = ""
    speaker_name: str = ""
    speaker_role: str = ""  # coordinator/worker/helper

    # 内容
    content: str = ""
    action_type: str = ""  # propose/agree/refuse/confirm/request/question

    # 质量评估
    work_quality: float = 0.0  # 对工作的正面贡献
    coordination_quality: float = 0.0  # 协调质量
    collaboration_value: float = 0.0  # 协作价值

    # 时间戳
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "round_num": self.round_num,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "speaker_role": self.speaker_role,
            "content": self.content,
            "action_type": self.action_type,
            "work_quality": self.work_quality,
            "coordination_quality": self.coordination_quality,
            "collaboration_value": self.collaboration_value,
            "timestamp": self.timestamp
        }


@dataclass
class WorkSession:
    """完整工作会话"""
    id: str = field(default_factory=lambda: f"WS-{uuid.uuid4().hex[:8]}")
    event: WorkEvent = None
    round_num: int = 0

    # 参与者和角色
    participants: List[str] = field(default_factory=list)  # 所有参与者 ID
    coordinator_id: Optional[str] = None
    worker_ids: List[str] = field(default_factory=list)
    helper_ids: List[str] = field(default_factory=list)

    # 交互历史
    interactions: List[WorkInteraction] = field(default_factory=list)

    # 最终方案
    final_plan: Dict = field(default_factory=dict)
    plan_approved: bool = False

    # 评估结果
    verdict: Optional[Dict] = None

    def add_interaction(self, interaction: WorkInteraction):
        """添加交互"""
        self.interactions.append(interaction)

    def get_interactions_by_round(self, round_num: int) -> List[WorkInteraction]:
        """获取指定轮次的交互"""
        return [i for i in self.interactions if i.round_num == round_num]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event": self.event.to_dict() if self.event else None,
            "round_num": self.round_num,
            "participants": self.participants,
            "coordinator_id": self.coordinator_id,
            "worker_ids": self.worker_ids,
            "helper_ids": self.helper_ids,
            "interactions": [i.to_dict() for i in self.interactions],
            "final_plan": self.final_plan,
            "plan_approved": self.plan_approved,
            "verdict": self.verdict
        }
