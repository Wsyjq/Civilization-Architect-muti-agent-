"""
LLM 服务模块

支持多种 LLM 供应商：
- OpenAI GPT (GPT-4, GPT-3.5)
- Anthropic Claude (Claude 3/4)
- 本地 LLM (Ollama)

使用工厂模式实现灵活切换
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Iterator
import os
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM 供应商类型"""
    OPENAI = "openai"
    CLAUDE = "claude"
    OLLAMA = "ollama"
    MOCK = "mock"  # 用于测试


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: LLMProvider = LLMProvider.MOCK
    
    # OpenAI 配置
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000
    
    # Claude 配置
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-3-sonnet-20240229"
    claude_temperature: float = 0.7
    claude_max_tokens: int = 2000
    
    # Ollama 配置
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    ollama_temperature: float = 0.7
    
    # 通用配置
    timeout: int = 60
    retry_count: int = 3
    
    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """从环境变量加载配置"""
        config = cls()
        
        # 读取供应商类型
        provider_str = os.getenv("LLM_PROVIDER", "mock").lower()
        try:
            config.provider = LLMProvider(provider_str)
        except ValueError:
            logger.warning(f"未知的 LLM 供应商: {provider_str}，使用 mock")
            config.provider = LLMProvider.MOCK
        
        # OpenAI 配置
        config.openai_api_key = os.getenv("OPENAI_API_KEY")
        config.openai_base_url = os.getenv("OPENAI_BASE_URL")
        config.openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        # Claude 配置
        config.claude_api_key = os.getenv("CLAUDE_API_KEY")
        config.claude_model = os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")
        
        # Ollama 配置
        config.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        config.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "provider": self.provider.value