"""
SQLite 持久化模块

持久化消息记录与游戏结果，数据库文件位于 data/game.db
"""

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "game.db"
)

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            civilization_id TEXT,
            sender_id TEXT,
            receiver_id TEXT,
            content TEXT,
            round_num INTEGER DEFAULT 0,
            timestamp TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_messages_civ ON messages(civilization_id);
        CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(sender_id, receiver_id);

        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            username TEXT,
            architecture_type TEXT,
            total_rounds INTEGER,
            current_round INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            total_output REAL DEFAULT 0,
            created_at TEXT,
            ended_at TEXT,
            final_result TEXT
        );
    """)
    conn.commit()


# ---------- 消息 ----------

def save_message_db(message_id: str, civilization_id: str, sender_id: str,
                    receiver_id: str, content: str, round_num: int,
                    timestamp: Optional[str] = None):
    """持久化一条消息"""
    with _lock:
        _get_conn().execute(
            "INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?,?,?)",
            (message_id, civilization_id, sender_id, receiver_id,
             content, round_num, timestamp or datetime.now().isoformat()),
        )
        _get_conn().commit()


def load_messages_db(civilization_id: Optional[str] = None,
                     round_num: Optional[int] = None,
                     agent_id: Optional[str] = None,
                     limit: int = 500) -> List[Dict[str, Any]]:
    """从数据库读取消息"""
    sql = "SELECT * FROM messages WHERE 1=1"
    params: list = []
    if civilization_id:
        sql += " AND civilization_id=?"
        params.append(civilization_id)
    if round_num is not None:
        sql += " AND round_num=?"
        params.append(round_num)
    if agent_id:
        sql += " AND (sender_id=? OR receiver_id=?)"
        params.extend([agent_id, agent_id])
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with _lock:
        rows = _get_conn().execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ---------- 游戏存档 ----------

def save_game_db(game_id: str, username: str, architecture_type: str,
                 total_rounds: int, current_round: int = 0,
                 status: str = "running", total_output: float = 0.0,
                 final_result: Optional[dict] = None):
    """创建或更新游戏存档"""
    with _lock:
        conn = _get_conn()
        existing = conn.execute(
            "SELECT game_id FROM games WHERE game_id=?", (game_id,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE games SET current_round=?, status=?, total_output=?,
                   ended_at=?, final_result=? WHERE game_id=?""",
                (current_round, status, total_output,
                 datetime.now().isoformat() if status == "ended" else None,
                 json.dumps(final_result, ensure_ascii=False) if final_result else None,
                 game_id),
            )
        else:
            conn.execute(
                """INSERT INTO games (game_id, username, architecture_type,
                   total_rounds, current_round, status, total_output, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (game_id, username, architecture_type, total_rounds,
                 current_round, status, total_output, datetime.now().isoformat()),
            )
        conn.commit()


def load_game_db(game_id: str) -> Optional[Dict[str, Any]]:
    """读取单个游戏存档"""
    with _lock:
        row = _get_conn().execute(
            "SELECT * FROM games WHERE game_id=?", (game_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("final_result"):
        d["final_result"] = json.loads(d["final_result"])
    return d


def list_games_db(limit: int = 50) -> List[Dict[str, Any]]:
    """列出最近的游戏存档"""
    with _lock:
        rows = _get_conn().execute(
            "SELECT * FROM games ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
