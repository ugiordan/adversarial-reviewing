# scripts/orchestrator/tests/test_state.py
import json
import pytest
from orchestrator.types import State, FsmConfig, FsmState, Delimiters, ActiveRetry, AgentConfig
from orchestrator.state import save_state, load_state, StateError


@pytest.fixture
def basic_state():
    return FsmState(current_state=State.SELF_REFINEMENT, iteration=1)


class TestSaveState:
    def test_saves_json_file(self, tmp_cache_dir):
        hex_val = "a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8"
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            iteration=2,
            delimiters=Delimiters(
                begin=f"===REVIEW_TARGET_{hex_val}_START===",
                end=f"===REVIEW_TARGET_{hex_val}_END===",
                hex=hex_val,
            ),
        )
        save_state(state, tmp_cache_dir)
        path = tmp_cache_dir / "fsm-state.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["current_state"] == "SELF_REFINEMENT"
        assert data["iteration"] == 2
        assert data["delimiters"]["begin"] == f"===REVIEW_TARGET_{hex_val}_START==="

    def test_roundtrip(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            iteration=3,
            delimiters=Delimiters(
                begin="===REVIEW_TARGET_a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8_START===",
                end="===REVIEW_TARGET_a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8_END===",
                hex="a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8",
            ),
            completed_outputs={"SEC-phase1-iter1.md"},
            prompt_hashes={"SEC-phase1-iter1.md": "sha256:abc"},
        )
        save_state(state, tmp_cache_dir)
        loaded = load_state(tmp_cache_dir)
        assert loaded.current_state == State.CONVERGENCE_CHECK
        assert loaded.iteration == 3
        assert loaded.completed_outputs == {"SEC-phase1-iter1.md"}
        assert loaded.prompt_hashes == {"SEC-phase1-iter1.md": "sha256:abc"}


class TestLoadState:
    def test_missing_file_raises(self, tmp_cache_dir):
        with pytest.raises(StateError, match="not found"):
            load_state(tmp_cache_dir)

    def test_unknown_state_raises(self, tmp_cache_dir):
        (tmp_cache_dir / "fsm-state.json").write_text(
            json.dumps({"current_state": "UNKNOWN_STATE", "iteration": 1})
        )
        with pytest.raises(StateError, match="version mismatch"):
            load_state(tmp_cache_dir)

    def test_corrupted_json_raises(self, tmp_cache_dir):
        (tmp_cache_dir / "fsm-state.json").write_text("not json")
        with pytest.raises(StateError, match="corrupted"):
            load_state(tmp_cache_dir)

    def test_min_iterations_exceeds_max_raises(self, tmp_cache_dir):
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code", "agents": ["SEC"],
                "budget_limit": 350000, "max_iterations": 3,
                "min_iterations": 50,
            },
        }))
        with pytest.raises(StateError, match="min_iterations out of range"):
            load_state(tmp_cache_dir)

    def test_negative_budget_raises(self, tmp_cache_dir):
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code", "agents": ["SEC"],
                "budget_limit": -1, "max_iterations": 3,
            },
        }))
        with pytest.raises(StateError, match="budget_limit out of range"):
            load_state(tmp_cache_dir)

    def test_negative_iteration_raises(self, tmp_cache_dir):
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": -5,
        }))
        with pytest.raises(StateError, match="iteration out of range"):
            load_state(tmp_cache_dir)

    def test_dispatch_history_not_list_raises(self, tmp_cache_dir):
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "dispatch_history": "not a list",
        }))
        with pytest.raises(StateError, match="dispatch_history must be a list"):
            load_state(tmp_cache_dir)

    def test_active_retry_with_failed_agent(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            active_retry=ActiveRetry(
                phase="self-refinement", iteration=1, attempt=1,
                failed_agent="SEC",
            ),
        )
        save_state(state, tmp_cache_dir)
        loaded = load_state(tmp_cache_dir)
        assert loaded.active_retry.failed_agent == "SEC"

    def test_deserialize_legacy_string_agents(self, tmp_cache_dir):
        """Old state files stored agents as plain strings. Verify backward compat."""
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code", "agents": ["SEC", "CORR"],
                "budget_limit": 350000, "max_iterations": 3,
                "min_iterations": 1,
            },
        }))
        loaded = load_state(tmp_cache_dir)
        assert len(loaded.config.agents) == 2
        assert isinstance(loaded.config.agents[0], AgentConfig)
        assert loaded.config.agents[0].prefix == "SEC"
        assert loaded.config.agents[0].file == ""
        assert loaded.config.agents[1].prefix == "CORR"

    def test_deserialize_new_dict_agents(self, tmp_cache_dir):
        """New state files store agents as dicts with prefix, file, etc."""
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code",
                "agents": [
                    {"prefix": "SEC", "file": "sec.md", "tools": ["Read", "Grep"],
                     "effort": "high", "max_turns": 20},
                ],
                "budget_limit": 350000, "max_iterations": 3,
                "min_iterations": 1,
            },
        }))
        loaded = load_state(tmp_cache_dir)
        assert len(loaded.config.agents) == 1
        agent = loaded.config.agents[0]
        assert isinstance(agent, AgentConfig)
        assert agent.prefix == "SEC"
        assert agent.file == "sec.md"
        assert agent.tools == ["Read", "Grep"]
        assert agent.effort == "high"
        assert agent.max_turns == 20

    def test_serialize_roundtrip_agent_config(self, tmp_cache_dir):
        """AgentConfig objects survive save/load roundtrip."""
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            config=FsmConfig(
                profile="code",
                agents=[
                    AgentConfig(prefix="SEC", file="sec.md", tools=["Read", "Grep"]),
                    AgentConfig(prefix="CORR", file="corr.md"),
                ],
                budget_limit=350000, max_iterations=3,
            ),
        )
        save_state(state, tmp_cache_dir)
        loaded = load_state(tmp_cache_dir)
        assert len(loaded.config.agents) == 2
        sec = loaded.config.agents[0]
        assert sec.prefix == "SEC"
        assert sec.file == "sec.md"
        assert sec.tools == ["Read", "Grep"]
        assert sec.effort == "medium"
        corr = loaded.config.agents[1]
        assert corr.prefix == "CORR"
        assert corr.tools == ["Read"]


class TestAgentConfigSerialization:
    """Edge case tests for AgentConfig serialization/deserialization."""

    def test_roundtrip_preserves_all_fields(self, tmp_cache_dir):
        """All AgentConfig fields (including non-default) survive a save/load cycle."""
        config = FsmConfig(
            profile="code",
            agents=[
                AgentConfig(prefix="SEC", file="sec.md",
                            tools=["Read"], effort="high", max_turns=15),
                AgentConfig(prefix="CORR", file="corr.md",
                            tools=["Read", "Grep"], effort="medium", max_turns=10),
            ],
            budget_limit=350000, max_iterations=3,
        )
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            config=config,
        )
        save_state(state, tmp_cache_dir)
        loaded = load_state(tmp_cache_dir)
        assert len(loaded.config.agents) == 2
        sec = loaded.config.agents[0]
        assert sec.prefix == "SEC"
        assert sec.file == "sec.md"
        assert sec.tools == ["Read"]
        assert sec.effort == "high"
        assert sec.max_turns == 15
        corr = loaded.config.agents[1]
        assert corr.prefix == "CORR"
        assert corr.file == "corr.md"
        assert corr.tools == ["Read", "Grep"]
        assert corr.effort == "medium"
        assert corr.max_turns == 10

    def test_backwards_compat_string_agents_defaults(self, tmp_cache_dir):
        """v1 state files stored agents as strings; verify all defaults are applied."""
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code",
                "agents": ["SEC", "CORR"],
                "budget_limit": 350000,
                "max_iterations": 3,
            },
        }))
        loaded = load_state(tmp_cache_dir)
        assert len(loaded.config.agents) == 2
        sec = loaded.config.agents[0]
        assert sec.prefix == "SEC"
        assert sec.file == ""
        assert sec.tools == ["Read"]
        assert sec.effort == "medium"
        assert sec.max_turns == 15

    def test_partial_dict_uses_defaults(self, tmp_cache_dir):
        """Agent dict with only prefix and file should use defaults for tools/effort/max_turns."""
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code",
                "agents": [
                    {"prefix": "SEC", "file": "sec.md"},
                ],
                "budget_limit": 350000,
                "max_iterations": 3,
            },
        }))
        loaded = load_state(tmp_cache_dir)
        sec = loaded.config.agents[0]
        assert sec.prefix == "SEC"
        assert sec.file == "sec.md"
        assert sec.tools == ["Read"]
        assert sec.effort == "medium"
        assert sec.max_turns == 15

    def test_invalid_prefix_path_traversal_raises(self, tmp_cache_dir):
        """Agent prefix with path traversal characters should be rejected."""
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code",
                "agents": [{"prefix": "SEC/../..", "file": "sec.md"}],
                "budget_limit": 350000,
                "max_iterations": 3,
            },
        }))
        with pytest.raises(StateError, match="Invalid agent ID"):
            load_state(tmp_cache_dir)

    def test_empty_prefix_raises(self, tmp_cache_dir):
        """Empty agent prefix should be rejected."""
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code",
                "agents": [{"prefix": "", "file": "sec.md"}],
                "budget_limit": 350000,
                "max_iterations": 3,
            },
        }))
        with pytest.raises(StateError, match="Invalid agent ID"):
            load_state(tmp_cache_dir)

    def test_invalid_agent_type_raises(self, tmp_cache_dir):
        """Non-string/non-dict agent entry should be rejected."""
        (tmp_cache_dir / "fsm-state.json").write_text(json.dumps({
            "current_state": "SELF_REFINEMENT",
            "iteration": 1,
            "config": {
                "profile": "code",
                "agents": [42],
                "budget_limit": 350000,
                "max_iterations": 3,
            },
        }))
        with pytest.raises(StateError, match="Invalid agent entry"):
            load_state(tmp_cache_dir)


class TestRedTeamCompletedSerialization:
    def test_round_trip_false(self, tmp_path, basic_state):
        basic_state.red_team_completed = False
        save_state(basic_state, str(tmp_path))
        loaded = load_state(str(tmp_path))
        assert loaded.red_team_completed is False

    def test_round_trip_true(self, tmp_path, basic_state):
        basic_state.red_team_completed = True
        save_state(basic_state, str(tmp_path))
        loaded = load_state(str(tmp_path))
        assert loaded.red_team_completed is True

    def test_backward_compat_missing_field(self, tmp_path, basic_state):
        """State files without red_team_completed should default to False."""
        save_state(basic_state, str(tmp_path))
        state_file = tmp_path / "fsm-state.json"
        data = json.loads(state_file.read_text())
        del data["red_team_completed"]
        state_file.write_text(json.dumps(data))
        # Remove HMAC files so load doesn't fail on integrity
        (tmp_path / "fsm-state.json.hmac").unlink(missing_ok=True)
        (tmp_path / ".state-integrity-key").unlink(missing_ok=True)
        loaded = load_state(str(tmp_path))
        assert loaded.red_team_completed is False
