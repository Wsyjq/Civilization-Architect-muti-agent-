"""
LLM服务模块

提供统一的API调用接口，支持OpenAI格式的API
包含限流、重试、并发控制等机制
"""

import os
import json
import time
import threading
import queue
import requests
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from functools import wraps
from datetime import datetime, timedelta

from backend.core.mock_dialogue_generator import (
    MockDialogueGenerator, 
    AgentPersonality, 
    get_mock_dialogue_generator
)


def _load_env_file(filepath: str = ".env"):
    """手动加载.env文件"""
    if not os.path.exists(filepath):
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

# 加载环境变量
_load_env_file()


@dataclass
class LLMConfig:
    """LLM配置"""
    api_url: str
    api_key: str
    model: str
    timeout: int = 30
    temperature: float = 0.7
    max_tokens: int = 1000
    # 限流配置
    rate_limit_requests: int = 10  # 每分钟最大请求数
    rate_limit_tokens: int = 10000  # 每分钟最大token数
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0  # 初始重试延迟（秒）
    retry_backoff_factor: float = 2.0  # 退避因子
    # 并发控制
    max_concurrent_requests: int = 3  # 最大并发请求数


class RateLimiter:
    """
    令牌桶限流器
    
    控制API请求频率，避免触发429错误
    """
    
    def __init__(self, max_requests: int = 10, max_tokens: int = 10000, window_seconds: int = 60):
        """
        初始化限流器
        
        Args:
            max_requests: 时间窗口内最大请求数
            max_tokens: 时间窗口内最大token数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.max_tokens = max_tokens
        self.window_seconds = window_seconds
        
        self._request_times: List[datetime] = []
        self._token_usage: List[tuple] = []  # (timestamp, tokens)
        self._lock = threading.Lock()
    
    def can_make_request(self, estimated_tokens: int = 100) -> bool:
        """
        检查是否可以发起请求
        
        Args:
            estimated_tokens: 预估token使用量
            
        Returns:
            是否可以发起请求
        """
        with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            # 清理过期的记录
            self._request_times = [t for t in self._request_times if t > window_start]
            self._token_usage = [(t, tokens) for t, tokens in self._token_usage if t > window_start]
            
            # 检查请求数限制
            if len(self._request_times) >= self.max_requests:
                return False
            
            # 检查token限制
            total_tokens = sum(tokens for _, tokens in self._token_usage)
            if total_tokens + estimated_tokens > self.max_tokens:
                return False
            
            return True
    
    def record_request(self, tokens_used: int = 0):
        """
        记录一次请求
        
        Args:
            tokens_used: 实际使用的token数
        """
        with self._lock:
            now = datetime.now()
            self._request_times.append(now)
            if tokens_used > 0:
                self._token_usage.append((now, tokens_used))
    
    def get_wait_time(self, estimated_tokens: int = 100) -> float:
        """
        获取需要等待的时间
        
        Args:
            estimated_tokens: 预估token使用量
            
        Returns:
            需要等待的秒数
        """
        with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            # 清理过期记录
            self._request_times = [t for t in self._request_times if t > window_start]
            self._token_usage = [(t, tokens) for t, tokens in self._token_usage if t > window_start]
            
            wait_time = 0.0
            
            # 检查请求数限制
            if len(self._request_times) >= self.max_requests:
                oldest_request = min(self._request_times)
                wait_time = max(wait_time, (oldest_request + timedelta(seconds=self.window_seconds) - now).total_seconds())
            
            # 检查token限制
            total_tokens = sum(tokens for _, tokens in self._token_usage)
            if total_tokens + estimated_tokens > self.max_tokens:
                # 找到最早的token使用记录
                if self._token_usage:
                    oldest_token_time = min(t for t, _ in self._token_usage)
                    wait_time = max(wait_time, (oldest_token_time + timedelta(seconds=self.window_seconds) - now).total_seconds())
            
            return max(0, wait_time)


class RetryHandler:
    """
    重试处理器
    
    实现指数退避重试策略
    """
    
    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
        """
        初始化重试处理器
        
        Args:
            max_retries: 最大重试次数
            initial_delay: 初始延迟（秒）
            backoff_factor: 退避因子
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数并带重试机制
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                last_exception = e
                response = e.response
                
                # 如果是429错误，根据Retry-After头等待
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        # 使用指数退避
                        wait_time = self.initial_delay * (self.backoff_factor ** attempt)
                    
                    print(f"遇到429限流，等待 {wait_time:.1f} 秒后重试 (尝试 {attempt + 1}/{self.max_retries + 1})")
                    time.sleep(wait_time)
                    continue
                
                # 其他HTTP错误，直接抛出
                raise
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.initial_delay * (self.backoff_factor ** attempt)
                    print(f"请求失败，等待 {wait_time:.1f} 秒后重试 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                # 其他异常直接抛出
                raise
        
        # 所有重试都失败了
        raise last_exception


class RequestQueue:
    """
    请求队列
    
    管理并发请求，控制同时进行的API调用数量
    """
    
    def __init__(self, max_concurrent: int = 3):
        """
        初始化请求队列
        
        Args:
            max_concurrent: 最大并发请求数
        """
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._queue = queue.Queue()
        self._results: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        """
        提交任务并等待执行
        
        Args:
            task_id: 任务ID
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        with self._semaphore:
            return func(*args, **kwargs)
    
    def submit_batch(self, tasks: List[tuple]) -> List[Any]:
        """
        批量提交任务
        
        Args:
            tasks: 任务列表，每个任务为 (task_id, func, args, kwargs)
            
        Returns:
            结果列表
        """
        results = []
        for task_id, func, args, kwargs in tasks:
            try:
                result = self.submit(task_id, func, *args, **kwargs)
                results.append((task_id, result, None))
            except Exception as e:
                results.append((task_id, None, e))
        return results


class LLMService:
    """
    LLM服务类

    提供统一的API调用接口，支持OpenAI格式的API
    包含限流、重试、并发控制等机制
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式（线程安全）"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化LLM服务"""
        if self._initialized:
            return

        self.config = self._load_config()
        
        # 初始化限流器
        self.rate_limiter = RateLimiter(
            max_requests=self.config.rate_limit_requests,
            max_tokens=self.config.rate_limit_tokens
        )
        
        # 初始化重试处理器
        self.retry_handler = RetryHandler(
            max_retries=self.config.max_retries,
            initial_delay=self.config.retry_delay,
            backoff_factor=self.config.retry_backoff_factor
        )
        
        # 初始化请求队列
        self.request_queue = RequestQueue(
            max_concurrent=self.config.max_concurrent_requests
        )
        
        self._initialized = True

    def _load_config(self) -> LLMConfig:
        """从环境变量加载配置"""
        api_url = os.getenv("LLM_API_URL", "")
        api_key = os.getenv("LLM_API_KEY", "")
        model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1000"))
        
        # 限流配置
        rate_limit_requests = int(os.getenv("LLM_RATE_LIMIT_REQUESTS", "10"))
        rate_limit_tokens = int(os.getenv("LLM_RATE_LIMIT_TOKENS", "10000"))
        
        # 重试配置
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        retry_delay = float(os.getenv("LLM_RETRY_DELAY", "1.0"))
        retry_backoff_factor = float(os.getenv("LLM_RETRY_BACKOFF", "2.0"))
        
        # 并发配置
        max_concurrent = int(os.getenv("LLM_MAX_CONCURRENT", "3"))

        if not api_url or not api_key:
            print("警告: LLM API配置未设置，将使用模拟模式")

        return LLMConfig(
            api_url=api_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
            temperature=temperature,
            max_tokens=max_tokens,
            rate_limit_requests=rate_limit_requests,
            rate_limit_tokens=rate_limit_tokens,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff_factor=retry_backoff_factor,
            max_concurrent_requests=max_concurrent
        )

    def is_configured(self) -> bool:
        """检查是否已配置API"""
        return bool(self.config.api_url and self.config.api_key)
    
    def _wait_for_rate_limit(self, estimated_tokens: int = 100):
        """
        等待直到可以发起请求
        
        Args:
            estimated_tokens: 预估token使用量
        """
        while not self.rate_limiter.can_make_request(estimated_tokens):
            wait_time = self.rate_limiter.get_wait_time(estimated_tokens)
            if wait_time > 0:
                print(f"达到API限流，等待 {wait_time:.1f} 秒...")
                time.sleep(min(wait_time, 5))  # 最多等待5秒，然后重新检查
            else:
                time.sleep(0.1)  # 短暂等待后重试

    def _make_api_call(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        实际执行API调用
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            system_prompt: 系统提示词
            
        Returns:
            AI生成的回复文本
        """
        # 构建请求体
        request_messages = []

        # 添加系统提示词
        if system_prompt:
            request_messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 添加用户消息
        request_messages.extend(messages)

        payload = {
            "model": self.config.model,
            "messages": request_messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

        # 支持自定义完整URL或自动添加/chat/completions
        api_endpoint = self.config.api_url
        if not api_endpoint.endswith('/chat/completions'):
            api_endpoint = f"{api_endpoint}/chat/completions"
        
        response = requests.post(
            api_endpoint,
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()

        result = response.json()
        
        # 估算token使用量（简单估算）
        estimated_tokens = len(str(payload)) // 4 + len(str(result)) // 4
        self.rate_limiter.record_request(estimated_tokens)
        
        return result["choices"][0]["message"]["content"]

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        use_mock_on_failure: bool = True
    ) -> str:
        """
        调用聊天完成API（带限流和重试）

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数（覆盖默认配置）
            max_tokens: 最大token数（覆盖默认配置）
            system_prompt: 系统提示词
            use_mock_on_failure: 失败时是否使用模拟回复

        Returns:
            AI生成的回复文本
        """
        # 如果未配置API，返回模拟回复
        if not self.is_configured():
            return self._generate_mock_response(messages)

        try:
            # 等待限流
            self._wait_for_rate_limit()
            
            # 使用重试机制执行API调用
            def api_call():
                return self.request_queue.submit(
                    f"chat_{datetime.now().timestamp()}",
                    self._make_api_call,
                    messages, temperature, max_tokens, system_prompt
                )
            
            return self.retry_handler.execute_with_retry(api_call)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"API限流(429)，已达到最大重试次数")
                if use_mock_on_failure:
                    return self._generate_mock_response(messages)
            raise
        except Exception as e:
            print(f"API调用失败: {e}")
            if use_mock_on_failure:
                return self._generate_mock_response(messages)
            raise

    def chat_completion_batch(
        self,
        requests: List[Dict],
        use_mock_on_failure: bool = True
    ) -> List[str]:
        """
        批量调用聊天完成API
        
        Args:
            requests: 请求列表，每个请求包含 messages, temperature, max_tokens, system_prompt
            use_mock_on_failure: 失败时是否使用模拟回复
            
        Returns:
            回复文本列表
        """
        if not self.is_configured():
            return [self._generate_mock_response(req.get('messages', [])) for req in requests]
        
        results = []
        
        for i, req in enumerate(requests):
            try:
                result = self.chat_completion(
                    messages=req.get('messages', []),
                    temperature=req.get('temperature'),
                    max_tokens=req.get('max_tokens'),
                    system_prompt=req.get('system_prompt'),
                    use_mock_on_failure=use_mock_on_failure
                )
                results.append(result)
                
                # 在请求之间添加小延迟，避免突发流量
                if i < len(requests) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"批量请求第 {i+1}/{len(requests)} 个失败: {e}")
                if use_mock_on_failure:
                    results.append(self._generate_mock_response(req.get('messages', [])))
                else:
                    results.append(None)
        
        return results

    def _generate_mock_response(self, messages: List[Dict[str, str]], 
                                 agent_personality: Dict = None) -> str:
        """
        生成模拟回复（当API未配置或失败时使用）
        
        使用MockDialogueGenerator生成丰富多样的个性化回复

        Args:
            messages: 消息列表
            agent_personality: Agent性格特征字典

        Returns:
            模拟的回复文本
        """
        # 获取最后一条用户消息
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break
        
        # 从系统提示词中提取Agent性格信息
        personality = self._extract_personality_from_messages(messages)
        if agent_personality:
            personality.update(agent_personality)
        
        # 确定消息类型
        message_type = self._detect_message_type(last_message)
        
        # 提取上下文信息
        context = self._extract_context_from_messages(messages)
        
        # 使用MockDialogueGenerator生成个性化回复
        try:
            mock_gen = get_mock_dialogue_generator()
            agent = AgentPersonality(
                name=personality.get('name', 'Agent'),
                authority=personality.get('authority', 0.5),
                selfishness=personality.get('selfishness', 0.5),
                altruism=personality.get('altruism', 0.5),
                sociability=personality.get('sociability', 0.5),
                intelligence=personality.get('intelligence', 0.5),
                risk_appetite=personality.get('risk_appetite', 0.5),
                resilience=personality.get('resilience', 0.5),
                loyalty=personality.get('loyalty', 0.5),
                is_traitor=personality.get('is_traitor', False)
            )
            
            return mock_gen.generate_response(
                agent=agent,
                message_type=message_type,
                context=context,
                receiver_name=personality.get('receiver_name', '同事')
            )
        except Exception as e:
            print(f"模拟回复生成失败: {e}")
            # 回退到简单回复
            return self._generate_simple_fallback_response(last_message)
    
    def _extract_personality_from_messages(self, messages: List[Dict[str, str]]) -> Dict:
        """从消息中提取Agent性格信息"""
        personality = {}
        
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                # 提取性格数值
                import re
                
                # 提取权威感
                auth_match = re.search(r'权威感[:：]\s*(\d+)%', content)
                if auth_match:
                    personality['authority'] = int(auth_match.group(1)) / 100
                
                # 提取私心
                self_match = re.search(r'私心[:：]\s*(\d+)%', content)
                if self_match:
                    personality['selfishness'] = int(self_match.group(1)) / 100
                
                # 提取利他
                alt_match = re.search(r'利他[:：]\s*(\d+)%', content)
                if alt_match:
                    personality['altruism'] = int(alt_match.group(1)) / 100
                
                # 提取社交
                soc_match = re.search(r'社交[:：]\s*(\d+)%', content)
                if soc_match:
                    personality['sociability'] = int(soc_match.group(1)) / 100
                
                # 提取智力
                int_match = re.search(r'智力[:：]\s*(\d+)%', content)
                if int_match:
                    personality['intelligence'] = int(int_match.group(1)) / 100
                
                # 提取风险偏好
                risk_match = re.search(r'风险偏好[:：]\s*(\d+)%', content)
                if risk_match:
                    personality['risk_appetite'] = int(risk_match.group(1)) / 100
                
                # 提取韧性
                res_match = re.search(r'韧性[:：]\s*(\d+)%', content)
                if res_match:
                    personality['resilience'] = int(res_match.group(1)) / 100
                
                # 提取忠诚
                loy_match = re.search(r'忠诚[:：]\s*(\d+)%', content)
                if loy_match:
                    personality['loyalty'] = int(loy_match.group(1)) / 100
                
                # 提取Agent名称
                name_match = re.search(r'【([^】]+)】', content)
                if name_match:
                    personality['name'] = name_match.group(1)
                
                break
        
        return personality
    
    def _detect_message_type(self, message: str) -> str:
        """检测消息类型"""
        if "汇报" in message or "报告" in message or "完成" in message:
            return "report"
        elif "请求" in message or "帮助" in message or "支援" in message:
            return "request"
        elif "状态" in message or "进度" in message:
            return "status"
        elif "警告" in message or "注意" in message or "发现" in message:
            return "alert"
        elif "建议" in message or "说服" in message:
            return "persuade"
        else:
            return "chat"
    
    def _extract_context_from_messages(self, messages: List[Dict[str, str]]) -> Dict:
        """从消息中提取上下文信息"""
        context = {}
        
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                
                # 提取工作量
                import re
                work_match = re.search(r'(\d+)\s*单位', content)
                if work_match:
                    context['work_done'] = int(work_match.group(1))
                
                # 提取贡献值
                contrib_match = re.search(r'贡献.*?([\d.]+)', content)
                if contrib_match:
                    context['contribution'] = float(contrib_match.group(1))
                
                # 提取资源请求量
                req_match = re.search(r'请求.*?([\d.]+)\s*单位', content)
                if req_match:
                    context['request_amount'] = int(req_match.group(1))
                
                # 提取进度
                prog_match = re.search(r'进度.*?([\d.]+)%', content)
                if prog_match:
                    context['progress'] = float(prog_match.group(1)) / 100
                
                break
        
        return context
    
    def _generate_simple_fallback_response(self, last_message: str) -> str:
        """生成简单的回退回复"""
        if "汇报" in last_message or "报告" in last_message:
            return "收到你的汇报，我仔细评估了当前情况。从目前的数据来看，整体进展符合预期，不过有几个细节我想深入了解一下，特别是关于后续执行策略的部分，你觉得我们是否需要做些调整？"
        elif "请求" in last_message or "帮助" in last_message:
            return "我理解你目前的处境，这个请求确实需要认真对待。让我先分析一下可行性和资源调配情况，稍后给你更具体的反馈。在此期间，你可以先整理一下相关的背景信息，方便我们更高效地推进。"
        elif "警告" in last_message or "注意" in last_message:
            return "感谢你的及时提醒，这个警告确实值得重视。我会立即关注相关情况，评估可能的影响范围。为了确保万无一失，建议你继续保持观察，有任何新的发现随时同步给我，我们一起制定应对策略。"
        elif "建议" in last_message or "说服" in last_message:
            return "你的建议很有价值，我从几个角度思考了一下，确实有一些可取之处。不过其中也有几个点我想和你进一步探讨，比如实施的具体时机和可能遇到的阻力，找个时间深入交流一下？"
        else:
            return "我仔细看了你的消息，觉得有几个方面值得深入讨论。目前的局势确实需要持续关注，但单纯观察可能不够，我想听听你更具体的分析和判断，这样我们才能做出更准确的决策。"


# 全局LLM服务实例
llm_service = LLMService()


def get_llm_service() -> LLMService:
    """获取LLM服务实例"""
    return llm_service
