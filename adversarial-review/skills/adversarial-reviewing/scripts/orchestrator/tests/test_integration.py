"""Integration tests for FSM lifecycle."""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator.__main__ import handle_init, handle_confirm, handle_next
from orchestrator.state import load_state
from orchestrator.types import State


def _make_delimiters():
    from orchestrator.types import Delimiters
    hex_val = "a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8"
    return Delimiters(
        begin=f"===REVIEW_TARGET_{hex_val}_START===",
        end=f"===REVIEW_TARGET_{hex_val}_END===",
        hex=hex_val,
    )


class TestEndToEnd:
    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.__main__.budget_mod")
    @patch("orchestrator.__main__._generate_delimiters")
    def test_init_creates_scope_dispatch(self, mock_delim, mock_budget,
                                         mock_cache, tmp_path, capsys, skill_dir):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "prompts").mkdir()
        (cache_dir / "outputs").mkdir()

        mock_cache.init_cache.return_value = {
            "cache_dir": str(cache_dir), "session_hex": "abc",
        }
        mock_budget.init_budget.return_value = {"limit": 150000}
        mock_delim.return_value = _make_delimiters()

        handle_init(["--quick", "/tmp/target"], skill_dir=skill_dir)

        output = json.loads(capsys.readouterr().out)
        assert "cache_dir" in output
        assert "delimiters" in output

        dispatch = json.loads((cache_dir / "dispatch.json").read_text())
        assert dispatch["action"] == "ask_user"

        state = load_state(cache_dir)
        assert state.current_state == State.CONFIRM_SCOPE

    @patch("orchestrator.__main__.cache")
    def test_confirm_writes_agent_dispatch(self, mock_cache, tmp_path, skill_dir):
        from orchestrator.types import Delimiters, FsmConfig, FsmState
        from orchestrator.state import save_state

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "prompts").mkdir()
        (cache_dir / "outputs").mkdir()

        from orchestrator.types import AgentConfig
        state = FsmState(
            current_state=State.CONFIRM_SCOPE,
            delimiters=_make_delimiters(),
            config=FsmConfig(
                profile="code",
                agents=[
                    AgentConfig(prefix="SEC", file="security-auditor.md"),
                    AgentConfig(prefix="CORR", file="correctness-verifier.md"),
                ],
                budget_limit=150000, max_iterations=2, min_iterations=1,
                flags={},
            ),
        )
        save_state(state, cache_dir)

        mock_cache.populate_templates.return_value = {}
        mock_cache.populate_references.return_value = {}

        handle_confirm(["--cache-dir", str(cache_dir)], skill_dir=skill_dir)

        dispatch = json.loads((cache_dir / "dispatch.json").read_text())
        assert dispatch["phase"] == "self-refinement"
        assert len(dispatch["agents"]) == 2
        assert dispatch["agents"][0]["id"] == "SEC"

        new_state = load_state(cache_dir)
        assert new_state.current_state == State.SELF_REFINEMENT


class TestAgentControlIntegration:
    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.__main__.budget_mod")
    def test_full_init_creates_reasoning_and_compaction_dirs(
        self, mock_budget, mock_cache, tmp_path, skill_dir, capsys
    ):
        """Verify init creates reasoning/ and compaction/ directories."""
        from orchestrator.__main__ import handle_init
        from orchestrator.types import AgentConfig

        cache_dir = str(tmp_path / "cache")
        mock_cache.init_cache.return_value = {"cache_dir": cache_dir}
        mock_budget.init_budget.return_value = {}
        os.makedirs(os.path.join(cache_dir, "prompts"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "outputs"), exist_ok=True)

        with patch("orchestrator.__main__._generate_delimiters") as mock_delim:
            from orchestrator.types import Delimiters
            mock_delim.return_value = Delimiters(
                begin="===REVIEW_TARGET_a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8_START===",
                end="===REVIEW_TARGET_a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8_END===",
                hex="a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8",
            )
            handle_init(["--profile", "code", "/tmp/target"], skill_dir=skill_dir)

        assert os.path.isdir(os.path.join(cache_dir, "reasoning"))
        assert os.path.isdir(os.path.join(cache_dir, "compaction"))

    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    def test_confirm_writes_v3_dispatch_with_dispatch_path(
        self, mock_compose, mock_profile, mock_cache, tmp_path, skill_dir
    ):
        """Verify confirm produces dispatch.json v3.0 with subagent_type/dispatch_path."""
        from orchestrator.__main__ import handle_confirm
        from orchestrator.dispatch import read_dispatch
        from orchestrator.types import AgentConfig, FsmState, FsmConfig, State, Delimiters
        from orchestrator.state import save_state

        mock_cache.populate_templates.return_value = {}
        mock_cache.populate_references.return_value = {}
        mock_compose.return_value = "test prompt content"
        mock_profile.return_value = {
            "agents": [
                {"prefix": "SEC", "file": "security-auditor.md"},
            ]
        }

        cache_dir = str(tmp_path / "cache")
        os.makedirs(os.path.join(cache_dir, "prompts"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "reasoning"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "compaction"), exist_ok=True)

        state = FsmState(
            current_state=State.CONFIRM_SCOPE,
            config=FsmConfig(
                profile="code",
                agents=[AgentConfig(
                    prefix="SEC", file="security-auditor.md",
                    tools=["Read"], effort="high", max_turns=15,
                )],
                budget_limit=350000, max_iterations=3,
            ),
            delimiters=Delimiters(
                begin="===REVIEW_TARGET_a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8_START===",
                end="===REVIEW_TARGET_a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8_END===",
                hex="a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8",
            ),
            budget_remaining=350000,
        )
        save_state(state, cache_dir)

        handle_confirm(["--cache-dir", cache_dir], skill_dir=skill_dir)

        dispatch = read_dispatch(cache_dir)
        assert dispatch["dispatch_version"] == "3.0"
        assert len(dispatch["agents"]) == 1
        assert dispatch["agents"][0]["subagent_type"] == "review-specialist"
        assert "dispatch_path" in dispatch["agents"][0]
        assert os.path.isdir(dispatch["agents"][0]["dispatch_path"])
        # prompt_file/output_file should not be in v3 agent entries
        assert "prompt_file" not in dispatch["agents"][0]
        assert "output_file" not in dispatch["agents"][0]

    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    def test_confirm_writes_v3_dispatch_with_dispatch_dirs(
        self, mock_compose, mock_profile, mock_cache, tmp_path, skill_dir
    ):
        """Verify v3 dispatch creates dispatch directories with expected files."""
        from orchestrator.__main__ import handle_confirm
        from orchestrator.dispatch import read_dispatch
        from orchestrator.types import AgentConfig, FsmState, FsmConfig, State, Delimiters
        from orchestrator.state import save_state

        mock_cache.populate_templates.return_value = {}
        mock_cache.populate_references.return_value = {}
        mock_compose.return_value = "test prompt"
        mock_profile.return_value = {
            "agents": [{"prefix": "SEC", "file": "sec.md"}]
        }

        cache_dir = str(tmp_path / "cache")
        os.makedirs(os.path.join(cache_dir, "prompts"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "reasoning"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "compaction"), exist_ok=True)

        state = FsmState(
            current_state=State.CONFIRM_SCOPE,
            config=FsmConfig(
                profile="code",
                agents=[AgentConfig(prefix="SEC", file="sec.md",
                                    tools=["Read"], effort="high", max_turns=15)],
                budget_limit=350000, max_iterations=3,
            ),
            delimiters=Delimiters(
                begin="===REVIEW_TARGET_a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8_START===",
                end="===REVIEW_TARGET_a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8_END===",
                hex="a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8",
            ),
            budget_remaining=350000,
        )
        save_state(state, cache_dir)

        handle_confirm(["--cache-dir", cache_dir], skill_dir=skill_dir)

        dispatch = read_dispatch(cache_dir)
        assert dispatch["dispatch_version"] == "3.0"
        agent_entry = dispatch["agents"][0]
        dispatch_path = agent_entry["dispatch_path"]
        # Dispatch directory should contain the expected files
        assert os.path.isfile(os.path.join(dispatch_path, "dispatch-config.yaml"))
        assert os.path.isfile(os.path.join(dispatch_path, "agent-instructions.md"))
        assert os.path.isfile(os.path.join(dispatch_path, "common-instructions.md"))
        assert os.path.isfile(os.path.join(dispatch_path, "finding-template.md"))
        assert os.path.isfile(os.path.join(dispatch_path, "source-files.md"))
        assert os.path.isfile(os.path.join(dispatch_path, "output.md"))

    def test_telemetry_module_functions_without_init(self):
        """Verify telemetry functions don't crash when called without init."""
        from orchestrator.telemetry import start_span, end_span, record_metric, flush
        import orchestrator.telemetry as tel
        old_tracer = tel._tracer
        tel._tracer = None
        try:
            ctx = start_span("test", {})
            end_span(ctx, {})
            record_metric("m", 1.0, {})
            flush()
        finally:
            tel._tracer = old_tracer

    def test_agent_config_roundtrip_through_full_stack(self, skill_dir):
        """Verify AgentConfig parsed from config.yml survives full roundtrip."""
        from orchestrator.config import parse_args, resolve_config
        from orchestrator.types import AgentConfig

        args = parse_args(["--profile", "code", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)

        # Config.yml should produce agents with control fields
        assert len(cfg.agents) == 5
        sec = next(a for a in cfg.agents if a.prefix == "SEC")
        assert isinstance(sec, AgentConfig)
        assert sec.tools == ["Read"]
        assert sec.effort == "high"
        assert sec.max_turns == 20
