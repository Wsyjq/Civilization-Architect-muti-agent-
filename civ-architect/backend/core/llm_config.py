"""
LLM配置模块

支持OpenAI GPT-4、DeepSeek等多种后端
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage


# Provider默认URL
PROVIDER_DEFAULTS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "anthropic": "https://api.anthropic.com",
    "ollama": "http://localhost:11434/v1",
}


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "deepseek"  # openai, deepseek, anthropic, ollama
    model: str = "deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # 用于代理或自定义端点
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 120  # 秒
    max_retries: int = 3

    # 成本控制
    cache_responses: bool = True  # 缓存响应减少成本

    def _get_default_url(self) -> Optional[str]:
        """获取provider默认URL"""
        return PROVIDER_DEFAULTS.get(self.provider)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量加载配置"""
        provider = os.getenv("LLM_PROVIDER", "deepseek")
        model = os.getenv("LLM_MODEL", "")

        # DeepSeek默认模型
        if provider == "deepseek" and not model:
            model = "deepseek-chat"
        elif provider == "openai" and not model:
            model = "gpt-4"
        elif not model:
            model = "deepseek-chat"

        return cls(
            provider=provider,
            model=model,
            api_key=os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
            timeout=int(os.getenv("LLM_TIMEOUT", "120")),
        )


@dataclass
class AgentLLMConfig:
    """单个Agent的LLM配置"""
    config: LLMConfig
    system_prompt: str = ""
    conversation_history: list = field(default_factory=list)
    max_history: int = 20  # 保留的最大历史消息数


class LLMManager:
    """
    LLM管理器

    为每个Agent创建和管理独立的LLM实例
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        self._llms: Dict[str, ChatOpenAI] = {}

    def get_llm(self, agent_id: str) -> ChatOpenAI:
        """获取指定Agent的LLM实例"""
        if agent_id not in self._llms:
            self._llms[agent_id] = self._create_llm()
        return self._llms[agent_id]

    def _create_llm(self) -> ChatOpenAI:
        """创建新的LLM实例"""
        kwargs = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "timeout": self.config.timeout,
            "max_retries": self.config.max_retries,
        }

        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key

        # 设置base_url
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        else:
            # 使用provider默认URL
            default_url = self.config._get_default_url()
            if default_url:
                kwargs["base_url"] = default_url

        return ChatOpenAI(**kwargs)

    async def arun(self, agent_id: str, messages: list, **kwargs) -> str:
        """
        异步运行LLM

        Args:
            agent_id: Agent ID
            messages: 消息列表
            **kwargs: 传递给LLM的其他参数

        Returns:
            LLM响应文本
        """
        import asyncio
        from functools import partial

        llm = self.get_llm(agent_id)

        # 将消息转换为LangChain格式
        lc_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg["content"]
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))
            else:
                lc_messages.append(msg)

        # 在线程池中运行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(llm.invoke, lc_messages, **kwargs)
        )

        return response.content if hasattr(response, 'content') else str(response)

    def run(self, agent_id: str, messages: list, **kwargs) -> str:
        """同步运行LLM"""
        llm = self.get_llm(agent_id)

        lc_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg["content"]
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))
            else:
                lc_messages.append(msg)

        response = llm.invoke(lc_messages, **kwargs)
        return response.content if hasattr(response, 'content') else str(response)

    def clear_cache(self):
        """清除所有LLM实例缓存"""
        self._llms.clear()


# 全局LLM管理器实例
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """获取全局LLM管理器"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


def configure_llm(config: LLMConfig):
    """配置全局LLM管理器"""
    global _llm_manager
    _llm_manager = LLMManager(config)


async def test_llm_connection() -> bool:
    """测试LLM连接"""
    try:
        manager = get_llm_manager()
        response = await manager.arun(
            "test",
            [{"role": "user", "content": "Say 'Hello' in exactly one word"}]
        )
        return "hello" in response.lower()
    except Exception as e:
        print(f"LLM connection test failed: {e}")
        return False
