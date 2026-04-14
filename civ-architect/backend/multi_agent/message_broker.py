"""
消息中间件

处理Agent间的消息路由、存储和过滤
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable
from datetime import datetime
from collections import defaultdict
import threading


@dataclass
class MessageFilter:
    """消息过滤器"""
    sender_ids: Optional[Set[str]] = None  # 只接收来自这些ID的消息
    receiver_id: Optional[str] = None      # 只接收发给此ID的消息
    message_types: Optional[set] = None     # 只接收这些类型的消息
    after_timestamp: Optional[datetime] = None  # 只接收此时间之后的
    min_importance: Optional[float] = None  # 最低重要性


class Message:
    """消息（简化版，避免循环导入）"""

    def __init__(
        self,
        message_id: str,
        sender_id: str,
        sender_name: str,
        receiver_id: str,
        receiver_name: str,
        content: str,
        message_type: str = "chat",
        importance: float = 0.5,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None
    ):
        self.message_id = message_id
        self.sender_id = sender_id
        self.sender_name = sender_name
        self.receiver_id = receiver_id
        self.receiver_name = receiver_name
        self.content = content
        self.message_type = message_type
        self.importance = importance
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "receiver_id": self.receiver_id,
            "receiver_name": self.receiver_name,
            "content": self.content,
            "message_type": self.message_type,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class MessageBroker:
    """
    消息中间件

    提供：
    - 消息发布/订阅
    - 消息路由（点对点、广播）
    - 消息存储和查询
    - 架构感知的消息传递
    """

    def __init__(self):
        # 消息存储
        self._messages: List[Message] = []
        self._lock = threading.Lock()

        # 订阅者回调
        self._subscribers: Dict[str, List[Callable[[Message], None]]] = defaultdict(list)

        # 每个Agent的消息队列
        self._agent_queues: Dict[str, List[Message]] = defaultdict(list)

        # 架构信息（用于路由）
        self._adjacency_matrix: Optional[Dict] = None
        self._agent_positions: Dict[str, Dict] = {}

    def set_adjacency_matrix(self, adj_matrix, agent_ids: List[str]):
        """设置邻接矩阵用于架构感知路由"""
        self._adjacency_matrix = {
            "matrix": adj_matrix,
            "agent_ids": agent_ids
        }

    def set_agent_positions(self, positions: Dict[str, Dict]):
        """设置Agent位置信息"""
        self._agent_positions = positions

    def subscribe(self, agent_id: str, callback: Callable[[Message], None]):
        """订阅消息"""
        self._subscribers[agent_id].append(callback)

    def unsubscribe(self, agent_id: str, callback: Callable[[Message], None]):
        """取消订阅"""
        if agent_id in self._subscribers:
            self._subscribers[agent_id].remove(callback)

    def publish(self, message: Message):
        """
        发布消息

        消息会根据接收者和架构进行路由
        """
        with self._lock:
            # 存储消息
            self._messages.append(message)

            # 根据接收者加入队列
            if message.receiver_id:
                self._agent_queues[message.receiver_id].append(message)

            # 广播给订阅者
            if message.receiver_id in self._subscribers:
                for callback in self._subscribers[message.receiver_id]:
                    try:
                        callback(message)
                    except Exception:
                        pass

    def broadcast(self, sender_id: str, content: str, agent_ids: List[str],
                  message_type: str = "chat", importance: float = 0.5):
        """
        广播消息给多个接收者

        Args:
            sender_id: 发送者ID
            content: 消息内容
            agent_ids: 接收者ID列表
            message_type: 消息类型
            importance: 重要性
        """
        import uuid
        sender_name = self._get_agent_name(sender_id)

        for receiver_id in agent_ids:
            if receiver_id != sender_id:  # 不发给自己
                receiver_name = self._get_agent_name(receiver_id)
                msg = Message(
                    message_id=str(uuid.uuid4())[:8],
                    sender_id=sender_id,
                    sender_name=sender_name,
                    receiver_id=receiver_id,
                    receiver_name=receiver_name,
                    content=content,
                    message_type=message_type,
                    importance=importance
                )
                self.publish(msg)

    def send_to_connected(
        self,
        sender_id: str,
        content: str,
        connected_ids: List[str],
        message_type: str = "chat",
        importance: float = 0.5
    ):
        """
        发送给有连接关系的Agent（架构感知）

        Args:
            sender_id: 发送者ID
            content: 消息内容
            connected_ids: 有连接的其他Agent ID列表
            message_type: 消息类型
            importance: 重要性
        """
        self.broadcast(sender_id, content, connected_ids, message_type, importance)

    def get_messages(self, agent_id: str, filter: Optional[MessageFilter] = None) -> List[Message]:
        """
        获取指定Agent的消息

        Args:
            agent_id: Agent ID
            filter: 可选的过滤器

        Returns:
            消息列表
        """
        with self._lock:
            messages = list(self._agent_queues.get(agent_id, []))

        if filter:
            messages = self._apply_filter(messages, filter)

        return messages

    def pop_messages(self, agent_id: str, filter: Optional[MessageFilter] = None) -> List[Message]:
        """
        获取并清除指定Agent的消息

        Args:
            agent_id: Agent ID
            filter: 可选的过滤器

        Returns:
            消息列表
        """
        with self._lock:
            messages = list(self._agent_queues.get(agent_id, []))
            if filter:
                messages = self._apply_filter(messages, filter)
                # 保留不匹配的消息
                remaining = [m for m in self._agent_queues[agent_id] if m not in messages]
                self._agent_queues[agent_id] = remaining
            else:
                self._agent_queues[agent_id] = []

        return messages

    def _apply_filter(self, messages: List[Message], filter: MessageFilter) -> List[Message]:
        """应用过滤器"""
        result = messages

        if filter.sender_ids:
            result = [m for m in result if m.sender_id in filter.sender_ids]

        if filter.receiver_id:
            result = [m for m in result if m.receiver_id == filter.receiver_id]

        if filter.message_types:
            result = [m for m in result if m.message_type in filter.message_types]

        if filter.after_timestamp:
            result = [m for m in result if m.timestamp > filter.after_timestamp]

        if filter.min_importance is not None:
            result = [m for m in result if m.importance >= filter.min_importance]

        return result

    def _get_agent_name(self, agent_id: str) -> str:
        """获取Agent名称（需要外部注入）"""
        # 默认返回ID
        return agent_id

    def set_agent_name_resolver(self, resolver: Callable[[str], str]):
        """设置Agent名称解析器"""
        self._get_agent_name = resolver

    def get_all_messages(self) -> List[Message]:
        """获取所有消息（用于调试）"""
        with self._lock:
            return list(self._messages)

    def get_message_count(self) -> int:
        """获取消息总数"""
        with self._lock:
            return len(self._messages)

    def clear(self):
        """清除所有消息"""
        with self._lock:
            self._messages.clear()
            self._agent_queues.clear()


# 全局消息代理实例
_broker: Optional[MessageBroker] = None


def get_message_broker() -> MessageBroker:
    """获取全局消息代理"""
    global _broker
    if _broker is None:
        _broker = MessageBroker()
    return _broker


def reset_message_broker():
    """重置消息代理（用于新游戏）"""
    global _broker
    _broker = MessageBroker()
