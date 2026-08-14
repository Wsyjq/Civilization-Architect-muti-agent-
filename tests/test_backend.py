"""
后端核心模块单元测试与 API 集成测试

运行: pytest tests/ -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.architecture import (
    ArchitectureAnalyzer,
    ArchitectureConfig,
    create_architecture,
)
from backend.models.agent import ArchitectureType
from backend.models.message_store import MessageRecord, MessageStore
from backend.core.macro_variables import (
    MacroVariables,
    initialize_macro_variables,
    calculate_all_macro_variables,
)
from backend.core.engine import GameEngine, Civilization
from backend.common.config import default_config


# ---------- 架构模块 ----------

class TestArchitecture:
    @pytest.mark.parametrize("arch_type", [
        ArchitectureType.TREE, ArchitectureType.STAR, ArchitectureType.MESH
    ])
    def test_create_architecture(self, arch_type):
        config = create_architecture(arch_type, 10)
        assert isinstance(config, ArchitectureConfig)
        assert len(config.adjacency_matrix) == 10
        assert all(len(row) == 10 for row in config.adjacency_matrix)

    def test_mesh_fully_connected(self):
        config = create_architecture(ArchitectureType.MESH, 5)
        matrix = config.adjacency_matrix
        for i in range(5):
            for j in range(5):
                if i != j:
                    assert matrix[i][j] > 0, f"网状架构节点{i}-{j}应连通"

    def test_star_has_center(self):
        config = create_architecture(ArchitectureType.STAR, 5)
        matrix = config.adjacency_matrix
        center_degree = sum(1 for v in matrix[0] if v > 0)
        assert center_degree == 4, "星形架构中心节点应连接所有其他节点"

    def test_accessibility_range(self):
        for arch_type in ArchitectureType:
            acc = ArchitectureAnalyzer.calculate_accessibility(arch_type, 10)
            assert acc > 0


# ---------- 消息存储 ----------

class TestMessageStore:
    def test_add_and_get(self):
        store = MessageStore()
        msg = MessageRecord(id="m1", sender_id="A1", receiver_id="A2",
                            content="hello", round_num=1)
        store.add_message(msg, civilization_id="CIV-TEST")
        assert store.get_message("m1") is msg
        assert len(store.get_agent_messages("A1")) == 1
        assert len(store.get_round_messages(1)) == 1
        assert len(store.get_messages_by_civilization("CIV-TEST")) == 1

    def test_round_filter(self):
        store = MessageStore()
        for i in range(3):
            store.add_message(
                MessageRecord(id=f"m{i}", sender_id="A1", receiver_id="A2",
                              content=str(i), round_num=i),
                civilization_id="CIV-TEST",
            )
        msgs = store.get_messages_by_civilization("CIV-TEST", round_num=2)
        assert len(msgs) == 1 and msgs[0].content == "2"


# ---------- 宏观变量 ----------

class TestMacroVariables:
    def test_initialize(self):
        mv = initialize_macro_variables("CIV-TEST")
        assert isinstance(mv, MacroVariables)
        d = mv.to_dict()
        for key in ("civilization_id", "resources", "stability",
                    "productivity", "cohesion"):
            assert key in d

    def test_update_clamps(self):
        mv = initialize_macro_variables("CIV-TEST")
        mv.update({"stability": 999.0})
        assert mv.stability <= 1.0
        mv.update({"stability": -999.0})
        assert mv.stability >= 0.0


# ---------- 游戏引擎集成 ----------

class TestGameEngine:
    @pytest.mark.parametrize("arch_type", [
        ArchitectureType.TREE, ArchitectureType.STAR, ArchitectureType.MESH
    ])
    def test_full_game_flow(self, arch_type):
        engine = GameEngine(
            num_civilizations=1,
            architecture_types=[arch_type],
            agents_per_civilization=10,
            total_rounds=2,
            seed=42,
        )
        engine.initialize()
        assert len(engine.civilizations) == 1

        civ = engine.civilizations[0]
        assert isinstance(civ, Civilization)
        assert len(civ.agents) == 10

        engine.run_round(civ)
        assert civ.state.round >= 1
        assert civ.state.total_output > 0
        assert len(civ.state.cycle_outputs) > 0
        assert len(civ.state.energy_level_history) > 0
        assert len(civ.state.cohesion_history) > 0
        assert len(civ.state.fidelity_history) > 0
        assert len(civ.state.social_capital_history) > 0


# ---------- HTTP API 集成 ----------

class TestAPI:
    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from server import app
        return TestClient(app)

    def test_health(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200 and r.json()["status"] == "ok"

    def test_game_lifecycle(self, client):
        r = client.post("/api/v1/game/start", json={
            "username": "pytest", "architecture_type": "tree",
            "total_rounds": 2, "seed": 42,
        })
        assert r.status_code == 200
        game_id = r.json()["game_id"]
        assert len(r.json()["agents"]) == 10

        r = client.get(f"/api/v1/game/{game_id}/status")
        assert r.status_code == 200

        r = client.post(f"/api/v1/game/{game_id}/run-round", json={})
        assert r.status_code == 200
        assert r.json()["total_output"] > 0

        r = client.post(f"/api/v1/game/{game_id}/end")
        assert r.status_code == 200

    def test_invalid_game_id(self, client):
        r = client.get("/api/v1/game/INVALID/status")
        assert r.status_code == 404

    def test_invalid_architecture(self, client):
        r = client.post("/api/v1/game/start", json={
            "username": "x", "architecture_type": "circle",
        })
        assert r.status_code == 422

    def test_communication_endpoints(self, client):
        r = client.post("/api/v1/game/start", json={
            "username": "comm", "architecture_type": "mesh",
            "total_rounds": 1, "seed": 1,
        })
        game_id = r.json()["game_id"]
        r = client.post(f"/api/v1/game/{game_id}/run-round", json={})
        civ_id = r.json()["messages"][0]["sender_id"].rsplit("_A", 1)[0]

        assert client.get(f"/api/v1/messages?civilization_id={civ_id}").status_code == 200
        assert client.get(f"/api/v1/civilizations/{civ_id}/activity").status_code == 200
        assert client.get(f"/api/v1/civilizations/{civ_id}/timeline").status_code == 200
        assert client.get("/api/v1/civilizations/NOPE/activity").status_code == 404
