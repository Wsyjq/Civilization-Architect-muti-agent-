"""
心理模型 V2

定义 Agent 的心理状态和行为
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class EmotionalState(Enum):
    """情绪状态"""
    NORMAL = "normal"
    HAPPY = "happy"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    FEARFUL = "fearful"
    HOPEFUL = "hopeful"


# 别名，用于兼容性
EmotionType = EmotionalState


class GoalType(Enum):
    """目标类型"""
    SURVIVAL = "survival"
    GROWTH = "growth"
    DOMINATION = "domination"
    COOPERATION = "cooperation"
    KNOWLEDGE = "knowledge"


class Trait(Enum):
    """性格特质"""
    AUTHORITY = "authority"
    SELFISHNESS = "selfishness"
    RESILIENCE = "resilience"
    ALTRUISM = "altruism"
    SOCIABILITY = "sociability"
    RISK_APPETITE = "risk_appetite"
    INTELLIGENCE = "intelligence"
    LOYALTY_BASE = "loyalty_base"


@dataclass
class PsychologyState:
    """心理状态"""
    agent_id: str
    
    # 情绪状态
    emotional_state: EmotionalState = EmotionalState.NORMAL
    emotional_intensity: float = 0.5  # 0-1
    
    # 认知状态
    cognitive_entropy: float = 0.0  # 认知熵
    stress_level: float = 0.0  # 压力水平
    
    # 社会状态
    trust_in_civilization: float = 0.5
    trust_in_neighbors: Dict[str, float] = field(default_factory=dict)
    
    # 行为倾向
    cooperation_willingness: float = 0.5
    betrayal_willingness: float = 0.0
    
    def update_emotion(self, event_impact: float):
        """根据事件更新情绪"""
        self.emotional_intensity = max(0, min(1, self.emotional_intensity + event_impact))
        
        if self.emotional_intensity > 0.8:
            self.emotional_state = EmotionalState.ANGRY if event_impact < 0 else EmotionalState.HAPPY
        elif self.emotional_intensity < 0.2:
            self.emotional_state = EmotionalState.FEARFUL
        else:
            self.emotional_state = EmotionalState.NORMAL
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "emotional_state": self.emotional_state.value,
            "emotional_intensity": self.emotional_intensity,
            "cognitive_entropy": self.cognitive_entropy,
            "stress_level": self.stress_level,
            "trust_in_civilization": self.trust_in_civilization,
            "cooperation_willingness": self.cooperation_willingness,
            "betrayal_willingness": self.betrayal_willingness
        }


class PsychologySystem:
    """心理系统"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.state = PsychologyState(agent_id=agent_id)
        self.traits: Dict[Trait, float] = {}
    
    def set_trait(self, trait: Trait, value: float):
        """设置性格特质"""
        self.traits[trait] = max(0, min(1, value))
    
    def get_trait(self, trait: Trait) -> float:
        """获取性格特质"""
        return self.traits.get(trait, 0.5)
    
    def update_emotion(self, event_impact: float):
        """更新情绪"""
        self.state.update_emotion(event_impact)
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "state": self.state.to_dict(),
            "traits": {t.value: v for t, v in self.traits.items()}
        }
