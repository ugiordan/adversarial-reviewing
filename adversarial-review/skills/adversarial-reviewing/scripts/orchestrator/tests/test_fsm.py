import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator.__main__ import (
    handle_init, handle_next, handle_confirm, handle_resume,
    _generate_delimiters,
)
from orchestrator.fsm import (
    transition, is_budget_exceeded, _run_compliance_checks,
    process_state, _evaluate_convergence, _discover_new_files,
    _agent_filename, _collect_findings_summary,
    _process_red_team_audit, _process_red_team_check,
    _process_red_team_deep_dive, log_guardrail,
    _write_red_team_dispatch, _write_deep_dive_dispatch,
    _has_deep_dive_dirs,
)
from orchestrator.types import (
    State, FsmState, FsmConfig, Delimiters, ActiveRetry, InvalidTransitionError,
    AgentConfig, RetryDispatchError,
)
from orchestrator.state import save_state, load_state


def _make_config(**overrides):
    defaults = dict(
        profile="code",
        agents=[
            AgentConfig(prefix="SEC", file="sec.md"),
            AgentConfig(prefix="CORR", file="corr.md"),
        ],
        budget_limit=350000, max_iterations=3, min_iterations=2,
        flags={},
    )
    defaults.update(overrides)
    return FsmConfig(**defaults)


def _make_delimiters(hex_val="a1b2c3d4e5f6a7b8a1b2c3d4e5f6a7b8"):
    return Delimiters(
        begin=f"===REVIEW_TARGET_{hex_val}_START===",
        end=f"===REVIEW_TARGET_{hex_val}_END===",
        hex=hex_val,
    )


class TestHandleInit:
    @patch("orchestrator.__main__.resolve_config")
    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.__main__.budget_mod")
    def test_creates_cache_and_returns_json(self, mock_budget, mock_cache,
                                            mock_resolve, tmp_path, capsys):
        mock_resolve.return_value = _make_config()
        mock_cache.init_cache.return_value = {
            "cache_dir": str(tmp_path / "cache"),
            "session_hex": "abc123",
        }
        mock_budget.init_budget.return_value = {"limit": 350000}
        os.makedirs(tmp_path / "cache" / "prompts", exist_ok=True)
        os.makedirs(tmp_path / "cache" / "outputs", exist_ok=True)

        with patch("orchestrator.__main__._generate_delimiters") as mock_delim:
            mock_delim.return_value = _make_delimiters()
            handle_init(
                ["--profile", "code", "/tmp/target"],
                skill_dir=str(tmp_path),
            )

        output = capsys.readouterr().out
        data = json.loads(output)
        assert "cache_dir" in data
        assert "delimiters" in data

    @patch("orchestrator.__main__.resolve_config")
    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.__main__.budget_mod")
    def test_init_writes_scope_confirmation(self, mock_budget, mock_cache,
                                            mock_resolve, tmp_path, capsys):
        mock_resolve.return_value = _make_config()
        cache_dir = str(tmp_path / "cache")
        mock_cache.init_cache.return_value = {"cache_dir": cache_dir}
        mock_budget.init_budget.return_value = {}
        os.makedirs(os.path.join(cache_dir, "prompts"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "outputs"), exist_ok=True)

        with patch("orchestrator.__main__._generate_delimiters") as mock_delim:
            mock_delim.return_value = _make_delimiters()
            handle_init(
                ["--profile", "code", "/tmp/target"],
                skill_dir=str(tmp_path),
            )

        scope_path = os.path.join(cache_dir, "scope-confirmation.md")
        assert os.path.exists(scope_path)
        content = Path(scope_path).read_text()
        assert "code" in content
        assert "/tmp/target" in content

        dispatch = json.loads(Path(os.path.join(cache_dir, "dispatch.json")).read_text())
        assert dispatch["phase"] == "confirm-scope"
        assert dispatch["action"] == "ask_user"

    @patch("orchestrator.__main__.resolve_config")
    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.__main__.budget_mod")
    def test_init_saves_state_in_confirm_scope(self, mock_budget, mock_cache,
                                                mock_resolve, tmp_path, capsys):
        mock_resolve.return_value = _make_config()
        cache_dir = str(tmp_path / "cache")
        mock_cache.init_cache.return_value = {"cache_dir": cache_dir}
        mock_budget.init_budget.return_value = {}
        os.makedirs(os.path.join(cache_dir, "prompts"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "outputs"), exist_ok=True)

        with patch("orchestrator.__main__._generate_delimiters") as mock_delim:
            mock_delim.return_value = _make_delimiters()
            handle_init(
                ["--profile", "code", "/tmp/target"],
                skill_dir=str(tmp_path),
            )

        state = load_state(cache_dir)
        assert state.current_state == State.CONFIRM_SCOPE


class TestHandleConfirm:
    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    def test_confirm_transitions_to_self_refinement(
        self, mock_compose, mock_profile, mock_cache, tmp_cache_dir, skill_dir
    ):
        mock_cache.populate_templates.return_value = {}
        mock_cache.populate_references.return_value = {}
        mock_compose.return_value = "test prompt content"
        mock_profile.return_value = {
            "agents": [
                {"prefix": "SEC", "file": "security-auditor.md"},
                {"prefix": "CORR", "file": "correctness-verifier.md"},
            ]
        }

        state = FsmState(
            current_state=State.CONFIRM_SCOPE,
            config=_make_config(),
            delimiters=_make_delimiters(),
            budget_remaining=350000,
        )
        save_state(state, tmp_cache_dir)

        handle_confirm(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        loaded = load_state(tmp_cache_dir)
        assert loaded.current_state == State.SELF_REFINEMENT

    @patch("orchestrator.__main__.cache")
    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    def test_confirm_writes_dispatch(
        self, mock_compose, mock_profile, mock_cache, tmp_cache_dir, skill_dir
    ):
        mock_cache.populate_templates.return_value = {}
        mock_cache.populate_references.return_value = {}
        mock_compose.return_value = "prompt"
        mock_profile.return_value = {
            "agents": [{"prefix": "SEC", "file": "sec.md"}]
        }

        state = FsmState(
            current_state=State.CONFIRM_SCOPE,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=_make_delimiters(),
            budget_remaining=350000,
        )
        save_state(state, tmp_cache_dir)

        handle_confirm(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        dispatch = json.loads((tmp_cache_dir / "dispatch.json").read_text())
        assert dispatch["phase"] == "self-refinement"
        assert dispatch["iteration"] == 1
        assert len(dispatch["agents"]) == 1
        assert dispatch["agents"][0]["id"] == "SEC"

    def test_confirm_from_wrong_state_exits(self, tmp_cache_dir, skill_dir):
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            config=_make_config(),
            delimiters=_make_delimiters(),
        )
        save_state(state, tmp_cache_dir)

        with pytest.raises(SystemExit):
            handle_confirm(
                ["--cache-dir", str(tmp_cache_dir)],
                skill_dir=skill_dir,
            )


class TestFsmTransitions:
    def test_transition_changes_state(self):
        state = FsmState(current_state=State.PARSE_FLAGS)
        transition(state, State.RESOLVE_SCOPE)
        assert state.current_state == State.RESOLVE_SCOPE

    def test_invalid_transition_raises(self):
        state = FsmState(current_state=State.PARSE_FLAGS)
        with pytest.raises(InvalidTransitionError):
            transition(state, State.DONE)

    def test_transition_from_terminal_raises(self):
        state = FsmState(current_state=State.DONE)
        with pytest.raises(InvalidTransitionError):
            transition(state, State.PARSE_FLAGS)

    def test_convergence_check_iterates(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            iteration=1,
            config=_make_config(),
            budget_consumed=50000,
            budget_remaining=300000,
        )
        save_state(state, tmp_cache_dir)
        loaded = load_state(tmp_cache_dir)
        assert loaded.current_state == State.CONVERGENCE_CHECK
        assert loaded.iteration == 1

    def test_budget_exceeded_skips_challenge(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            iteration=2,
            config=_make_config(budget_limit=150000),
            budget_consumed=160000,
            budget_remaining=0,
        )
        save_state(state, tmp_cache_dir)
        loaded = load_state(tmp_cache_dir)
        assert loaded.budget_consumed > loaded.config.budget_limit

    def test_is_budget_exceeded_true(self):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            config=_make_config(budget_limit=100000),
            budget_consumed=100000,
        )
        assert is_budget_exceeded(state) is True

    def test_is_budget_exceeded_false_under_limit(self):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            config=_make_config(budget_limit=100000),
            budget_consumed=50000,
        )
        assert is_budget_exceeded(state) is False

    def test_is_budget_exceeded_false_no_budget_flag(self):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            config=_make_config(budget_limit=100000, flags={"no_budget": True}),
            budget_consumed=200000,
        )
        assert is_budget_exceeded(state) is False

    def test_is_budget_exceeded_false_zero_limit(self):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            config=_make_config(budget_limit=0),
            budget_consumed=999999,
        )
        assert is_budget_exceeded(state) is False


class TestEvaluateConvergence:
    def test_continue_when_under_limits(self):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            iteration=1,
            config=_make_config(budget_limit=350000, max_iterations=3),
            budget_consumed=50000,
        )
        result = _evaluate_convergence(state, "/tmp", "/tmp")
        assert result == "continue"

    def test_budget_exceeded(self):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            iteration=1,
            config=_make_config(budget_limit=100),
            budget_consumed=200,
        )
        result = _evaluate_convergence(state, "/tmp", "/tmp")
        assert result == "budget_exceeded"

    def test_max_iterations_without_convergence(self):
        state = FsmState(
            current_state=State.CONVERGENCE_CHECK,
            iteration=3,
            config=_make_config(budget_limit=350000, max_iterations=3),
            budget_consumed=50000,
        )
        result = _evaluate_convergence(state, "/tmp", "/tmp")
        assert result == "max_iterations"


class TestHandleNext:
    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    @patch("orchestrator.fsm.budget")
    def test_self_refinement_advances_to_convergence_check(
        self, mock_budget, mock_compose, mock_profile, tmp_cache_dir, skill_dir
    ):
        mock_compose.return_value = "prompt"
        mock_profile.return_value = {
            "agents": [{"prefix": "SEC", "file": "sec.md"}]
        }
        mock_budget.add_consumption.return_value = {
            "consumed": 10000, "remaining": 340000,
        }

        delimiters = _make_delimiters()
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=delimiters,
            budget_remaining=350000,
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
                "timestamp": "2026-04-30T00:00:00Z",
            }],
        )
        prompt_path = str(tmp_cache_dir / "prompts" / "SEC-phase1-iter1.md")
        Path(prompt_path).write_text("prompt content")
        from orchestrator.validation import compute_content_hash
        state.prompt_hashes["SEC-phase1-iter1.md"] = compute_content_hash(
            "prompt content"
        )

        save_state(state, tmp_cache_dir)

        output_path = str(tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md")
        Path(output_path).write_text(
            f"preamble\n{delimiters.begin}\nfindings\n{delimiters.end}\npostamble"
        )

        (tmp_cache_dir / "dispatch.json").write_text(json.dumps({
            "dispatch_version": "1.0", "phase": "self-refinement",
            "iteration": 1, "agents": [],
        }))

        handle_next(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        loaded = load_state(tmp_cache_dir)
        assert loaded.current_state == State.SELF_REFINEMENT
        assert loaded.iteration == 2
        assert loaded.dispatch_history[-1]["iteration"] == 2

    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    @patch("orchestrator.fsm.budget")
    @patch("orchestrator.fsm.convergence")
    def test_convergence_reached_transitions_to_challenge(
        self, mock_conv, mock_budget, mock_compose, mock_profile,
        tmp_cache_dir, skill_dir
    ):
        mock_compose.return_value = "prompt"
        mock_profile.return_value = {
            "agents": [{"prefix": "SEC", "file": "sec.md"}]
        }
        mock_budget.add_consumption.return_value = {
            "consumed": 50000, "remaining": 300000,
        }
        mock_conv.check_convergence.return_value = (True, {"converged": True})

        delimiters = _make_delimiters()
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            iteration=2,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=delimiters,
            budget_remaining=350000,
            dispatch_history=[
                {"phase": "self-refinement", "iteration": 1, "agents": ["SEC"],
                 "timestamp": "2026-04-30T00:00:00Z"},
                {"phase": "self-refinement", "iteration": 2, "agents": ["SEC"],
                 "timestamp": "2026-04-30T00:01:00Z"},
            ],
        )

        for i in [1, 2]:
            p = str(tmp_cache_dir / "prompts" / f"SEC-phase1-iter{i}.md")
            Path(p).write_text(f"prompt iter {i}")
            o = str(tmp_cache_dir / "outputs" / f"SEC-phase1-iter{i}.md")
            Path(o).write_text(
                f"preamble\n{delimiters.begin}\nfindings iter {i}\n{delimiters.end}"
            )

        from orchestrator.validation import compute_content_hash
        state.prompt_hashes["SEC-phase1-iter2.md"] = compute_content_hash(
            "prompt iter 2"
        )

        save_state(state, tmp_cache_dir)
        (tmp_cache_dir / "dispatch.json").write_text(json.dumps({
            "dispatch_version": "1.0", "phase": "self-refinement",
            "iteration": 2, "agents": [],
        }))

        handle_next(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        loaded = load_state(tmp_cache_dir)
        assert loaded.current_state == State.CHALLENGE_ROUND
        assert loaded.challenge_iteration == 1
        assert loaded.self_refinement_iterations == 2

    def test_next_from_invalid_state_exits(self, tmp_cache_dir, skill_dir):
        state = FsmState(
            current_state=State.CONFIRM_SCOPE,
            config=_make_config(),
        )
        save_state(state, tmp_cache_dir)

        with pytest.raises(SystemExit):
            handle_next(
                ["--cache-dir", str(tmp_cache_dir)],
                skill_dir=skill_dir,
            )

    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    @patch("orchestrator.fsm.budget")
    def test_report_phase_transitions_to_done(
        self, mock_budget, mock_compose, mock_profile, tmp_cache_dir, skill_dir
    ):
        mock_compose.return_value = "prompt"
        mock_profile.return_value = {
            "agents": [{"prefix": "SEC", "file": "sec.md"}]
        }

        delimiters = _make_delimiters()
        state = FsmState(
            current_state=State.REPORT,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=delimiters,
            dispatch_history=[{
                "phase": "report",
                "iteration": 1,
                "agents": ["REPORT"],
            }],
        )

        prompt_path = str(tmp_cache_dir / "prompts" / "REPORT.md")
        Path(prompt_path).write_text("report prompt")
        output_path = str(tmp_cache_dir / "outputs" / "REPORT.md")
        Path(output_path).write_text(
            f"{delimiters.begin}\nFinal report\n{delimiters.end}"
        )

        from orchestrator.validation import compute_content_hash
        state.prompt_hashes["REPORT.md"] = compute_content_hash("report prompt")

        save_state(state, tmp_cache_dir)
        (tmp_cache_dir / "dispatch.json").write_text(json.dumps({
            "dispatch_version": "1.0", "phase": "report",
        }))

        handle_next(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        loaded = load_state(tmp_cache_dir)
        assert loaded.current_state == State.DONE

        dispatch = json.loads((tmp_cache_dir / "dispatch.json").read_text())
        assert dispatch["done"] is True

    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    @patch("orchestrator.fsm.budget")
    def test_resolution_transitions_to_report_when_red_team_completed(
        self, mock_budget, mock_compose, mock_profile, tmp_cache_dir, skill_dir
    ):
        mock_compose.return_value = "prompt"
        mock_profile.return_value = {
            "agents": [{"prefix": "SEC", "file": "sec.md"}]
        }

        state = FsmState(
            current_state=State.RESOLUTION,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=_make_delimiters(),
            red_team_completed=True,
        )
        save_state(state, tmp_cache_dir)

        handle_next(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        loaded = load_state(tmp_cache_dir)
        assert loaded.current_state == State.REPORT
        assert "REPORT.md" in loaded.prompt_hashes
        assert loaded.dispatch_history[-1]["phase"] == "report"

    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    @patch("orchestrator.fsm.budget")
    def test_resolution_transitions_to_red_team_when_not_completed(
        self, mock_budget, mock_compose, mock_profile, tmp_cache_dir, skill_dir
    ):
        mock_compose.return_value = "prompt"
        mock_profile.return_value = {
            "agents": [{"prefix": "SEC", "file": "sec.md"}]
        }

        state = FsmState(
            current_state=State.RESOLUTION,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=_make_delimiters(),
            red_team_completed=False,
        )
        save_state(state, tmp_cache_dir)

        handle_next(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        loaded = load_state(tmp_cache_dir)
        assert loaded.current_state == State.RED_TEAM_AUDIT
        assert loaded.dispatch_history[-1]["phase"] == "red-team-audit"


class TestComplianceChecks:
    def test_missing_output_aborts(self, tmp_cache_dir, skill_dir):
        delimiters = _make_delimiters()
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=delimiters,
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
            }],
        )

        with pytest.raises(SystemExit):
            _run_compliance_checks(state, str(tmp_cache_dir))

        assert state.current_state == State.ABORTED
        assert state.error["type"] == "missing_output"

    def test_delimiter_mismatch_triggers_retry(self, tmp_cache_dir, skill_dir):
        delimiters = _make_delimiters()
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=delimiters,
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
            }],
        )

        output_path = tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md"
        output_path.write_text("no delimiters here, just text")

        (tmp_cache_dir / "dispatch.json").write_text(json.dumps({
            "dispatch_version": "1.0", "phase": "self-refinement",
            "iteration": 1,
            "agents": [{"id": "SEC", "description": "SEC",
                       "prompt_file": "p", "output_file": "o"}],
        }))

        with pytest.raises(RetryDispatchError):
            _run_compliance_checks(state, str(tmp_cache_dir))

        assert state.current_state == State.SELF_REFINEMENT
        assert state.active_retry is not None
        assert state.active_retry.attempt == 1

    def test_delimiter_mismatch_after_retry_aborts(self, tmp_cache_dir, skill_dir):
        delimiters = _make_delimiters()
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=delimiters,
            active_retry=ActiveRetry(
                phase="self-refinement", iteration=1, attempt=1
            ),
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
            }],
        )

        output_path = tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md"
        output_path.write_text("still no delimiters after retry")

        with pytest.raises(SystemExit):
            _run_compliance_checks(state, str(tmp_cache_dir))

        assert state.current_state == State.ABORTED
        assert "retry" in state.error["message"].lower()

    def test_passing_compliance(self, tmp_cache_dir, skill_dir):
        delimiters = _make_delimiters()
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=delimiters,
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
            }],
        )

        prompt_path = str(tmp_cache_dir / "prompts" / "SEC-phase1-iter1.md")
        Path(prompt_path).write_text("prompt")
        from orchestrator.validation import compute_content_hash
        state.prompt_hashes["SEC-phase1-iter1.md"] = compute_content_hash("prompt")

        output_path = tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md"
        output_path.write_text(
            f"preamble\n{delimiters.begin}\n"
            + ("x" * 600) +
            f"\n{delimiters.end}\npostamble"
        )

        _run_compliance_checks(state, str(tmp_cache_dir))
        assert state.relay_compliance_rounds == 1
        assert state.active_retry is None


class TestHandleResume:
    def test_resume_from_aborted_exits(self, tmp_cache_dir, skill_dir):
        state = FsmState(
            current_state=State.ABORTED,
            config=_make_config(),
            error={"type": "test", "message": "test error"},
        )
        save_state(state, tmp_cache_dir)

        with pytest.raises(SystemExit):
            handle_resume(
                ["--cache-dir", str(tmp_cache_dir)],
                skill_dir=skill_dir,
            )

    def test_resume_from_done_writes_done_dispatch(
        self, tmp_cache_dir, skill_dir, capsys
    ):
        state = FsmState(
            current_state=State.DONE,
            config=_make_config(),
            delimiters=_make_delimiters(),
        )
        save_state(state, tmp_cache_dir)

        handle_resume(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        dispatch = json.loads((tmp_cache_dir / "dispatch.json").read_text())
        assert dispatch["done"] is True

        output = capsys.readouterr().out
        data = json.loads(output)
        assert "cache_dir" in data

    @patch("orchestrator.fsm.read_profile_config")
    @patch("orchestrator.fsm.compose_prompt")
    def test_resume_dispatch_state_re_dispatches_missing_outputs(
        self, mock_compose, mock_profile, tmp_cache_dir, skill_dir, capsys
    ):
        mock_compose.return_value = "prompt"
        mock_profile.return_value = {
            "agents": [{"prefix": "SEC", "file": "sec.md"}]
        }

        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=_make_delimiters(),
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
            }],
        )
        save_state(state, tmp_cache_dir)

        handle_resume(
            ["--cache-dir", str(tmp_cache_dir)],
            skill_dir=skill_dir,
        )

        dispatch = json.loads((tmp_cache_dir / "dispatch.json").read_text())
        assert dispatch["phase"] == "self-refinement"

        output = capsys.readouterr().out
        data = json.loads(output)
        assert "delimiters" in data


class TestGenerateDelimiters:
    def test_fallback_when_script_missing(self, tmp_path):
        delimiters = _generate_delimiters(str(tmp_path), str(tmp_path))
        assert delimiters.begin.startswith("===REVIEW_TARGET_")
        assert delimiters.end.endswith("_END===")
        assert len(delimiters.hex) == 32

    def test_fallback_delimiters_are_unique(self, tmp_path):
        d1 = _generate_delimiters(str(tmp_path), str(tmp_path))
        d2 = _generate_delimiters(str(tmp_path), str(tmp_path))
        assert d1.hex != d2.hex


class TestAgentFilename:
    def test_self_refinement_filename(self):
        assert _agent_filename("SEC", "self-refinement", 1) == "SEC-phase1-iter1.md"
        assert _agent_filename("SEC", "self-refinement", 3) == "SEC-phase1-iter3.md"

    def test_challenge_round_filename(self):
        assert _agent_filename("SEC", "challenge-round", 1) == "SEC-challenge-iter1.md"


class TestDiscoverNewFiles:
    def test_finds_new_files(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            config=_make_config(),
        )
        (tmp_cache_dir / "outputs" / "test.md").write_text("content")

        files = _discover_new_files(state, str(tmp_cache_dir))
        rel_paths = {rel for _, rel in files}
        assert "outputs/test.md" in rel_paths

    def test_skips_already_tracked(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.SELF_REFINEMENT,
            config=_make_config(),
            completed_outputs={"outputs/test.md"},
        )
        (tmp_cache_dir / "outputs" / "test.md").write_text("content")

        files = _discover_new_files(state, str(tmp_cache_dir))
        rel_paths = {rel for _, rel in files}
        assert "outputs/test.md" not in rel_paths


class TestCollectFindingsSummary:
    def test_collects_tracked_files(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.REPORT,
            config=_make_config(),
            delimiters=_make_delimiters(),
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
            }],
        )
        (tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md").write_text("findings")
        (tmp_cache_dir / "outputs" / ".DS_Store").write_bytes(b"\x00\x01\x02")

        summary = _collect_findings_summary(state, str(tmp_cache_dir))
        assert "SEC-phase1-iter1.md" in summary
        assert ".DS_Store" not in summary

    def test_excludes_report(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.REPORT,
            config=_make_config(),
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
            }, {
                "phase": "report",
                "iteration": 1,
                "agents": ["REPORT"],
            }],
        )
        (tmp_cache_dir / "outputs" / "REPORT.md").write_text("report")
        (tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md").write_text("findings")

        summary = _collect_findings_summary(state, str(tmp_cache_dir))
        assert "REPORT.md" not in summary
        assert "SEC-phase1-iter1.md" in summary


class TestAnonymizedFindings:
    def test_anonymizes_agent_prefixes(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.REPORT,
            config=_make_config(),
            delimiters=_make_delimiters(),
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC", "CORR"],
            }],
        )
        (tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md").write_text(
            "SEC found a vulnerability in the auth module"
        )
        (tmp_cache_dir / "outputs" / "CORR-phase1-iter1.md").write_text(
            "CORR found a bug in the parser"
        )

        summary = _collect_findings_summary(state, str(tmp_cache_dir),
                                            anonymize=True)
        assert "SEC-phase1-iter1.md" not in summary
        assert "CORR-phase1-iter1.md" not in summary
        assert "Reviewer" in summary
        assert "Iteration 1" in summary

    def test_non_anonymized_keeps_names(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.REPORT,
            config=_make_config(),
            delimiters=_make_delimiters(),
            dispatch_history=[{
                "phase": "self-refinement",
                "iteration": 1,
                "agents": ["SEC"],
            }],
        )
        (tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md").write_text("findings")

        summary = _collect_findings_summary(state, str(tmp_cache_dir),
                                            anonymize=False)
        assert "SEC-phase1-iter1.md" in summary

    def test_consistent_labels_across_iterations(self, tmp_cache_dir):
        state = FsmState(
            current_state=State.REPORT,
            config=_make_config(),
            delimiters=_make_delimiters(),
            dispatch_history=[
                {"phase": "self-refinement", "iteration": 1,
                 "agents": ["SEC", "CORR"]},
                {"phase": "self-refinement", "iteration": 2,
                 "agents": ["SEC", "CORR"]},
            ],
        )
        for i in [1, 2]:
            (tmp_cache_dir / "outputs" / f"SEC-phase1-iter{i}.md").write_text(
                f"SEC iter {i}"
            )
            (tmp_cache_dir / "outputs" / f"CORR-phase1-iter{i}.md").write_text(
                f"CORR iter {i}"
            )

        summary = _collect_findings_summary(state, str(tmp_cache_dir),
                                            anonymize=True)
        # SEC should consistently map to the same label
        lines = summary.split("\n")
        reviewer_labels = [l for l in lines if l.startswith("### Reviewer")]
        # Should have 4 entries (2 agents x 2 iterations)
        assert len(reviewer_labels) == 4


class TestPhase2bHandlers:
    """Tests for the Phase 2b (Red Team Audit) state handlers."""

    def _make_state(self, current_state, **overrides):
        defaults = dict(
            current_state=current_state,
            iteration=1,
            config=_make_config(agents=[AgentConfig(prefix="SEC", file="sec.md")]),
            delimiters=_make_delimiters(),
        )
        defaults.update(overrides)
        return FsmState(**defaults)

    @patch("orchestrator.fsm._run_compliance_checks")
    def test_red_team_audit_transitions_to_check(self, mock_compliance, tmp_cache_dir):
        """RED_TEAM_AUDIT runs compliance then transitions to RED_TEAM_CHECK."""
        state = self._make_state(State.RED_TEAM_AUDIT)
        result = _process_red_team_audit(state, str(tmp_cache_dir), str(tmp_cache_dir))
        assert state.current_state == State.RED_TEAM_CHECK
        assert result == "continue"
        mock_compliance.assert_called_once()

    def test_red_team_check_with_flags_and_deep_dives(self, tmp_cache_dir):
        """RED_TEAM_CHECK with FLAG: in output and deep dive dirs transitions to DEEP_DIVE."""
        state = self._make_state(
            State.RED_TEAM_CHECK,
            dispatch_history=[{
                "phase": "red-team-audit", "iteration": 1,
                "agents": ["RED-TEAM"],
            }],
        )

        # Create audit output with flags
        audit_dir = tmp_cache_dir / "dispatch" / "RED-TEAM-red-team-audit-iter1"
        audit_dir.mkdir(parents=True)
        (audit_dir / "output.md").write_text("FLAG: F001 - severity inflation\n")

        # Create a deep dive dir (simulating prepare-deep-dives.py output)
        dd_dir = tmp_cache_dir / "dispatch" / "DEEP-DIVE-F001"
        dd_dir.mkdir(parents=True)
        (dd_dir / "prompt.md").write_text("investigate F001")

        with patch("orchestrator.fsm._run_legacy_script") as mock_script:
            _process_red_team_check(state, str(tmp_cache_dir), str(tmp_cache_dir))

        assert state.current_state == State.RED_TEAM_DEEP_DIVE
        assert state.dispatch_history[-1]["phase"] == "red-team-deep-dive"
        # dispatch.json should exist
        dispatch_path = tmp_cache_dir / "dispatch.json"
        assert dispatch_path.exists()
        dispatch = json.loads(dispatch_path.read_text())
        assert dispatch["phase"] == "red-team-deep-dive"
        assert any("DEEP-DIVE-F001" in a["id"] for a in dispatch["agents"])

    def test_red_team_check_with_no_flags_reported(self, tmp_cache_dir):
        """RED_TEAM_CHECK with NO_FLAGS_REPORTED transitions to REPORT."""
        state = self._make_state(
            State.RED_TEAM_CHECK,
            dispatch_history=[{
                "phase": "red-team-audit", "iteration": 1,
                "agents": ["RED-TEAM"],
            }],
        )

        audit_dir = tmp_cache_dir / "dispatch" / "RED-TEAM-red-team-audit-iter1"
        audit_dir.mkdir(parents=True)
        (audit_dir / "output.md").write_text("NO_FLAGS_REPORTED\n")

        with patch("orchestrator.fsm._write_report_dispatch"):
            _process_red_team_check(state, str(tmp_cache_dir), str(tmp_cache_dir))

        assert state.current_state == State.REPORT

    def test_red_team_check_no_output_file(self, tmp_cache_dir):
        """RED_TEAM_CHECK with missing audit output transitions to REPORT."""
        state = self._make_state(
            State.RED_TEAM_CHECK,
            dispatch_history=[{
                "phase": "red-team-audit", "iteration": 1,
                "agents": ["RED-TEAM"],
            }],
        )
        # No audit output file created

        with patch("orchestrator.fsm._write_report_dispatch"):
            _process_red_team_check(state, str(tmp_cache_dir), str(tmp_cache_dir))

        assert state.current_state == State.REPORT
        # Should have a guardrail log entry about skipping deep dives
        skip_logs = [
            g for g in state.guardrail_log
            if g["name"] == "skip_deep_dives"
        ]
        assert len(skip_logs) == 1

    def test_red_team_check_flags_but_no_deep_dive_dirs(self, tmp_cache_dir):
        """FLAGS found but prepare-deep-dives.py didn't create dirs: fall back to REPORT."""
        state = self._make_state(
            State.RED_TEAM_CHECK,
            dispatch_history=[{
                "phase": "red-team-audit", "iteration": 1,
                "agents": ["RED-TEAM"],
            }],
        )

        audit_dir = tmp_cache_dir / "dispatch" / "RED-TEAM-red-team-audit-iter1"
        audit_dir.mkdir(parents=True)
        (audit_dir / "output.md").write_text("FLAG: F001 - weak evidence\n")

        with patch("orchestrator.fsm._run_legacy_script"), \
             patch("orchestrator.fsm._write_report_dispatch"):
            _process_red_team_check(state, str(tmp_cache_dir), str(tmp_cache_dir))

        assert state.current_state == State.REPORT
        no_dd_logs = [
            g for g in state.guardrail_log
            if g["name"] == "no_deep_dives"
        ]
        assert len(no_dd_logs) == 1

    def test_red_team_check_with_both_flag_and_no_flags_reported(self, tmp_cache_dir):
        """NO_FLAGS_REPORTED overrides FLAG: markers."""
        state = self._make_state(
            State.RED_TEAM_CHECK,
            dispatch_history=[{
                "phase": "red-team-audit", "iteration": 1,
                "agents": ["RED-TEAM"],
            }],
        )

        audit_dir = tmp_cache_dir / "dispatch" / "RED-TEAM-red-team-audit-iter1"
        audit_dir.mkdir(parents=True)
        (audit_dir / "output.md").write_text(
            "FLAG: F001 - false alarm\nNO_FLAGS_REPORTED\n"
        )

        with patch("orchestrator.fsm._write_report_dispatch"):
            _process_red_team_check(state, str(tmp_cache_dir), str(tmp_cache_dir))

        assert state.current_state == State.REPORT

    @patch("orchestrator.fsm._run_compliance_checks")
    @patch("orchestrator.fsm._run_legacy_script")
    def test_deep_dive_sets_red_team_completed(
        self, mock_script, mock_compliance, tmp_cache_dir
    ):
        """RED_TEAM_DEEP_DIVE sets red_team_completed=True and transitions to RESOLUTION."""
        state = self._make_state(
            State.RED_TEAM_DEEP_DIVE,
            red_team_completed=False,
            dispatch_history=[{
                "phase": "red-team-deep-dive", "iteration": 1,
                "agents": ["DEEP-DIVE-F001"],
            }],
        )

        # Create deep dive output
        dd_dir = tmp_cache_dir / "dispatch" / "DEEP-DIVE-F001"
        dd_dir.mkdir(parents=True)
        (dd_dir / "output.md").write_text("Deep dive findings for F001")

        result = _process_red_team_deep_dive(state, str(tmp_cache_dir), str(tmp_cache_dir))

        assert state.red_team_completed is True
        assert state.current_state == State.RESOLUTION
        assert result == "continue"

        # Verify deep dive results were collected
        deep_dive_results = tmp_cache_dir / "deep-dive-results"
        assert deep_dive_results.exists()
        collected = list(deep_dive_results.glob("*.md"))
        assert len(collected) == 1
        assert "DEEP-DIVE-F001" in collected[0].name

    @patch("orchestrator.fsm._run_compliance_checks")
    @patch("orchestrator.fsm._run_legacy_script")
    def test_deep_dive_handles_script_failure(
        self, mock_script, mock_compliance, tmp_cache_dir
    ):
        """RED_TEAM_DEEP_DIVE logs warning on script failure but still transitions."""
        mock_script.side_effect = FileNotFoundError("resolve-votes.py not found")

        state = self._make_state(
            State.RED_TEAM_DEEP_DIVE,
            dispatch_history=[{
                "phase": "red-team-deep-dive", "iteration": 1,
                "agents": ["DEEP-DIVE-F001"],
            }],
        )

        _process_red_team_deep_dive(state, str(tmp_cache_dir), str(tmp_cache_dir))

        assert state.red_team_completed is True
        assert state.current_state == State.RESOLUTION
        warning_logs = [
            g for g in state.guardrail_log
            if g["name"] == "resolve_deep_dives" and g["level"] == "warning"
        ]
        assert len(warning_logs) == 1

    def test_has_deep_dive_dirs_true(self, tmp_cache_dir):
        """_has_deep_dive_dirs returns True when DEEP-DIVE-* dirs exist."""
        dispatch_dir = tmp_cache_dir / "dispatch"
        dispatch_dir.mkdir(parents=True, exist_ok=True)
        (dispatch_dir / "DEEP-DIVE-F001").mkdir()
        assert _has_deep_dive_dirs(str(tmp_cache_dir)) is True

    def test_has_deep_dive_dirs_false_no_dispatch(self, tmp_cache_dir):
        """_has_deep_dive_dirs returns False when dispatch dir doesn't exist."""
        assert _has_deep_dive_dirs(str(tmp_cache_dir)) is False

    def test_has_deep_dive_dirs_false_no_matching(self, tmp_cache_dir):
        """_has_deep_dive_dirs returns False when no DEEP-DIVE-* dirs exist."""
        dispatch_dir = tmp_cache_dir / "dispatch"
        dispatch_dir.mkdir(parents=True, exist_ok=True)
        (dispatch_dir / "RED-TEAM-red-team-audit-iter1").mkdir()
        assert _has_deep_dive_dirs(str(tmp_cache_dir)) is False

    def test_write_red_team_dispatch(self, tmp_cache_dir, skill_dir):
        """_write_red_team_dispatch creates dispatch.json and adds history entry."""
        state = self._make_state(
            State.RED_TEAM_AUDIT,
            dispatch_history=[{
                "phase": "self-refinement", "iteration": 1,
                "agents": ["SEC"],
            }],
        )
        (tmp_cache_dir / "outputs" / "SEC-phase1-iter1.md").write_text("findings")

        _write_red_team_dispatch(state, str(tmp_cache_dir), skill_dir)

        dispatch_path = tmp_cache_dir / "dispatch.json"
        assert dispatch_path.exists()
        dispatch = json.loads(dispatch_path.read_text())
        assert dispatch["phase"] == "red-team-audit"
        assert dispatch["dispatch_version"] == "3.0"
        assert len(dispatch["agents"]) == 1
        assert dispatch["agents"][0]["id"] == "RED-TEAM"
        assert dispatch["agents"][0]["subagent_type"] == "red-team-auditor"

        assert state.dispatch_history[-1]["phase"] == "red-team-audit"
        assert state.dispatch_history[-1]["agents"] == ["RED-TEAM"]

    def test_write_deep_dive_dispatch(self, tmp_cache_dir):
        """_write_deep_dive_dispatch creates dispatch.json from DEEP-DIVE-* dirs."""
        state = self._make_state(State.RED_TEAM_DEEP_DIVE, dispatch_history=[])

        dispatch_dir = tmp_cache_dir / "dispatch"
        dispatch_dir.mkdir(parents=True, exist_ok=True)
        (dispatch_dir / "DEEP-DIVE-F001").mkdir()
        (dispatch_dir / "DEEP-DIVE-F002").mkdir()
        # Non-matching dir should be ignored
        (dispatch_dir / "RED-TEAM-red-team-audit-iter1").mkdir()

        _write_deep_dive_dispatch(state, str(tmp_cache_dir), str(tmp_cache_dir))

        dispatch_path = tmp_cache_dir / "dispatch.json"
        assert dispatch_path.exists()
        dispatch = json.loads(dispatch_path.read_text())
        assert dispatch["phase"] == "red-team-deep-dive"
        assert dispatch["parallel"] is True
        assert len(dispatch["agents"]) == 2
        agent_ids = [a["id"] for a in dispatch["agents"]]
        assert "DEEP-DIVE-F001" in agent_ids
        assert "DEEP-DIVE-F002" in agent_ids

        assert state.dispatch_history[-1]["phase"] == "red-team-deep-dive"

    def test_red_team_check_prepare_deep_dives_failure(self, tmp_cache_dir):
        """If prepare-deep-dives.py fails, has_flags resets and goes to REPORT."""
        state = self._make_state(
            State.RED_TEAM_CHECK,
            dispatch_history=[{
                "phase": "red-team-audit", "iteration": 1,
                "agents": ["RED-TEAM"],
            }],
        )

        audit_dir = tmp_cache_dir / "dispatch" / "RED-TEAM-red-team-audit-iter1"
        audit_dir.mkdir(parents=True)
        (audit_dir / "output.md").write_text("FLAG: F001 - concern\n")

        with patch("orchestrator.fsm._run_legacy_script",
                   side_effect=Exception("script crashed")), \
             patch("orchestrator.fsm._write_report_dispatch"):
            _process_red_team_check(state, str(tmp_cache_dir), str(tmp_cache_dir))

        # After prepare-deep-dives.py fails, has_flags is set to False
        assert state.current_state == State.REPORT
        warning_logs = [
            g for g in state.guardrail_log
            if g["name"] == "prepare_deep_dives"
        ]
        assert len(warning_logs) == 1
