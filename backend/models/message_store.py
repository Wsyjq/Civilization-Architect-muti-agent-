"""
消息存储模块

用于存储和管理消息记录
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class MessageRecord:
    """消息记录"""
    id: str
    sender_id: str
    receiver_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    round_num: int = 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "round_num": self.round_num
        }


class MessageStore:
    """消息存储"""

    def __init__(self):
        self.messages: Dict[str, MessageRecord] = {}
        self.agent_messages: Dict[str, List[str]] = {}  # agent_id -> message_ids
        self.round_messages: Dict[int, List[str]] = {}  # round -> message_ids
        self.civilization_messages: Dict[str, List[str]] = {}  # civilization_id -> message_ids
    
    def add_message(self, message: MessageRecord, civilization_id: str = None):
        """添加消息

        Args:
            message: 消息记录
            civilization_id: 文明ID（可选）
        """
        self.messages[message.id] = message

        # 记录到 Agent 的消息列表
        for agent_id in [message.sender_id, message.receiver_id]:
            if agent_id not in self.agent_messages:
                self.agent_messages[agent_id] = []
            self.agent_messages[agent_id].append(message.id)

        # 记录到回合的消息列表
        if message.round_num not in self.round_messages:
            self.round_messages[message.round_num] = []
        self.round_messages[message.round_num].append(message.id)

        # 记录到文明的消息列表
        if civilization_id:
            if civilization_id not in self.civilization_messages:
                self.civilization_messages[civilization_id] = []
            self.civilization_messages[civilization_id].append(message.id)
    
    def get_message(self, message_id: str) -> Optional[MessageRecord]:
        """获取消息"""
        return self.messages.get(message_id)
    
    def get_agent_messages(self, agent_id: str) -> List[MessageRecord]:
        """获取 Agent 的所有消息"""
        message_ids = self.agent_messages.get(agent_id, [])
        return [self.messages[mid] for mid in message_ids if mid in self.messages]
    
    def get_round_messages(self, round_num: int) -> List[MessageRecord]:
        """获取指定回合的所有消息"""
        message_ids = self.round_messages.get(round_num, [])
        return [self.messages[mid] for mid in message_ids if mid in self.messages]

    def get_messages_by_civilization(
        self,
        civilization_id: str,
        round_num: int = None,
        limit: int = 50
    ) -> List[MessageRecord]:
        """
        获取指定文明的消息

        Args:
            civilization_id: 文明ID
            round_num: 回合号（可选）
            limit: 返回数量限制

        Returns:
            消息列表
        """
        message_ids = self.civilization_messages.get(civilization_id, [])
        messages = [self.messages[mid] for mid in message_ids if mid in self.messages]

        # 按回合筛选
        if round_num is not None:
            messages = [m for m in messages if m.round_num == round_num]

        # 限制数量
        return messages[:limit]

    def save_message(self, message) -> None:
        """
        保存消息（支持Message或MessageRecord对象）

        Args:
            message: 消息对象
        """
        from backend.models.message import Message

        if isinstance(message, Message):
            # 从Message对象创建MessageRecord
            msg_record = MessageRecord(
                id=message.message_id,
                sender_id=message.sender_id,
                receiver_id=message.receiver_id,
                content=message.natural_language.message if message.natural_language else str(message.structured) if message.structured else "",
                timestamp=message.timestamp if isinstance(message.timestamp, datetime) else datetime.now(),
                round_num=message.round_num
            )
            self.add_message(msg_record, message.civilization_id)
        elif isinstance(message, MessageRecord):
            self.add_message(message)

    def to_dict(self) -> dict:
        return {
            "messages": {k: v.to_dict() for k, v in self.messages.items()},
            "total_count": len(self.messages)
        }


# 全局消息存储实例
_message_store: Optional[MessageStore] = None


def get_message_store() -> MessageStore:
    """获取全局消息存储实例"""
    global _message_store
    if _message_store is None:
        _message_store = MessageStore()
    return _message_store


def reset_message_store():
    """重置消息存储"""
    global _message_store
    _message_store = MessageStore()
