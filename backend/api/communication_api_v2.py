"""
通讯系统 API v2

提供消息查询、对话详情、文明活动与时间线接口。
数据来源于全局 MessageStore（由 MessageGenerator 在每轮模拟中写入）。
"""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query

from backend.models.message_store import get_message_store

router = APIRouter()


@router.get("/messages")
async def list_messages(
    civilization_id: Optional[str] = None,
    round_num: Optional[int] = None,
    agent_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    """获取消息列表

    支持按文明、回合、Agent 筛选，按时间倒序返回。
    """
    store = get_message_store()

    if agent_id:
        messages = store.get_agent_messages(agent_id)
    elif civilization_id:
        messages = store.get_messages_by_civilization(
            civilization_id, round_num=round_num, limit=limit
        )
    elif round_num is not None:
        messages = store.get_round_messages(round_num)
    else:
        messages = list(store.messages.values())

    if round_num is not None and not civilization_id:
        messages = [m for m in messages if m.round_num == round_num]

    messages = sorted(messages, key=lambda m: m.timestamp, reverse=True)[:limit]
    return {
        "total": len(messages),
        "messages": [m.to_dict() for m in messages],
    }


@router.get("/conversations/{agent1}/{agent2}")
async def get_conversation(agent1: str, agent2: str) -> Dict[str, Any]:
    """获取两个 Agent 之间的对话详情"""
    store = get_message_store()
    a1_msgs = store.get_agent_messages(agent1)
    conversation = [
        m for m in a1_msgs
        if (m.sender_id == agent1 and m.receiver_id == agent2)
        or (m.sender_id == agent2 and m.receiver_id == agent1)
    ]
    conversation.sort(key=lambda m: m.timestamp)
    return {
        "participants": [agent1, agent2],
        "total": len(conversation),
        "messages": [m.to_dict() for m in conversation],
    }


@router.get("/civilizations/{civilization_id}/activity")
async def get_civilization_activity(civilization_id: str) -> Dict[str, Any]:
    """获取文明活动概览（消息总量、按回合统计、活跃Agent）"""
    store = get_message_store()
    messages = store.get_messages_by_civilization(civilization_id, limit=10000)

    if not messages:
        raise HTTPException(status_code=404, detail="文明不存在或暂无活动记录")

    rounds: Dict[int, int] = {}
    agent_activity: Dict[str, int] = {}
    for m in messages:
        rounds[m.round_num] = rounds.get(m.round_num, 0) + 1
        agent_activity[m.sender_id] = agent_activity.get(m.sender_id, 0) + 1

    return {
        "civilization_id": civilization_id,
        "total_messages": len(messages),
        "messages_by_round": [
            {"round_num": r, "count": c} for r, c in sorted(rounds.items())
        ],
        "most_active_agents": sorted(
            agent_activity.items(), key=lambda x: x[1], reverse=True
        )[:10],
    }


@router.get("/civilizations/{civilization_id}/timeline")
async def get_civilization_timeline(
    civilization_id: str,
    limit_per_round: int = Query(default=20, ge=1, le=200),
) -> Dict[str, Any]:
    """获取文明消息时间线（按回合分组）"""
    store = get_message_store()
    messages = store.get_messages_by_civilization(civilization_id, limit=10000)

    if not messages:
        raise HTTPException(status_code=404, detail="文明不存在或暂无活动记录")

    timeline: Dict[int, List[dict]] = {}
    for m in messages:
        timeline.setdefault(m.round_num, [])
        if len(timeline[m.round_num]) < limit_per_round:
            timeline[m.round_num].append(m.to_dict())

    return {
        "civilization_id": civilization_id,
        "timeline": [
            {"round_num": r, "messages": msgs}
            for r, msgs in sorted(timeline.items())
        ],
    }
