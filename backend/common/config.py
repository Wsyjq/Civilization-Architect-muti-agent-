"""
游戏配置模块

定义游戏的全局配置参数
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnergyConfig:
    """能量配置"""
    default_work: float = 70.0
    default_conflict: float = 15.0
    default_comm: float = 15.0

    personality_threshold: float = 0.6

    high_selfishness_work_bonus: float = 5.0
    high_selfishness_conflict_bonus: float = 10.0

    high_altruism_work_bonus: float = 5.0

    high_authority_comm_bonus: float = 5.0

    work_min: float = 30.0
    work_max: float = 90.0
    conflict_min: float = 0.0
    conflict_max: float = 30.0
    comm_min: float = 10.0
    comm_max: float = 40.0


@dataclass
class TraitorConfig:
    """内鬼配置"""
    activate_tendency_threshold: float = 0.3
    opportunity_base: float = 0.2
    opportunity_trust_weight: float = 0.3
    opportunity_entropy_weight: float = 0.5
    activate_probability_multiplier: float = 0.1

    slack_base_rate: float = 0.2
    slack_tendency_multiplier: float = 0.3

    steal_rate_multiplier: float = 0.1

    injection_base_strength: float = 0.1
    injection_loyalty_delta: float = 0.05


@dataclass
class StateUpdateConfig:
    """状态更新配置"""
    entropy_recovery_base: float = 0.05

    core_position_stress: float = 0.3
    middle_position_stress: float = 0.2
    edge_position_stress: float = 0.1

    mental_load_threshold: float = 0.6
    high_load_entropy_increase: float = 0.1


@dataclass
class GameConfig:
    """游戏配置"""

    # 文明配置
    num_civilizations: int = 3
    agents_per_civilization: int = 5

    # 回合配置
    max_rounds: int = 100
    round_timeout: int = 300  # 秒

    # 资源配置
    initial_resources: Dict[str, float] = field(default_factory=lambda: {
        "energy": 100.0,
        "material": 100.0,
        "knowledge": 50.0
    })

    # Agent 配置
    min_agents: int = 3
    max_agents: int = 20

    # 内鬼配置
    traitor_ratio: float = 0.2  # 内鬼比例

    # LLM 配置
    llm_provider: str = "deepseek"  # openai, claude, deepseek, ollama
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500

    # 游戏模式
    enable_llm_dialogue: bool = True
    enable_traitor_mechanic: bool = True
    enable_cognitive_entropy: bool = True

    # 随机种子
    default_seed: Optional[int] = None

    # 能量配置
    energy: EnergyConfig = field(default_factory=EnergyConfig)

    # 内鬼配置
    traitor: TraitorConfig = field(default_factory=TraitorConfig)

    # 状态更新配置
    state_update: StateUpdateConfig = field(default_factory=StateUpdateConfig)

    def to_dict(self) -> dict:
        return {
            "num_civilizations": self.num_civilizations,
            "agents_per_civilization": self.agents_per_civilization,
            "max_rounds": self.max_rounds,
            "round_timeout": self.round_timeout,
            "initial_resources": self.initial_resources,
            "min_agents": self.min_agents,
            "max_agents": self.max_agents,
            "traitor_ratio": self.traitor_ratio,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "enable_llm_dialogue": self.enable_llm_dialogue,
            "enable_traitor_mechanic": self.enable_traitor_mechanic,
            "enable_cognitive_entropy": self.enable_cognitive_entropy,
            "default_seed": self.default_seed
        }


# 默认配置实例
default_config = GameConfig()
