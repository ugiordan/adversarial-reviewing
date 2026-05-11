# scripts/orchestrator/tests/test_types.py
import pytest
from orchestrator.types import (
    State, FsmConfig, FsmState, DispatchAgent, VALID_TRANSITIONS, InvalidTransitionError,
    AgentConfig, ALLOWED_AGENT_TOOLS, VALID_EFFORT_LEVELS,
)


class TestState:
    def test_all_states_defined(self):
        expected = {
            "PARSE_FLAGS", "RESOLVE_SCOPE", "CONFIRM_SCOPE",
            "INIT_CACHE", "POPULATE_CACHE", "SELF_REFINEMENT",
            "CONVERGENCE_CHECK", "CHALLENGE_ROUND", "CHALLENGE_CHECK",
            "RESOLUTION", "REPORT", "DONE", "ABORTED",
            "RED_TEAM_AUDIT", "RED_TEAM_CHECK", "RED_TEAM_DEEP_DIVE",
        }
        assert {s.name for s in State} == expected

    def test_dispatch_states(self):
        assert State.SELF_REFINEMENT.is_dispatch_state
        assert State.CHALLENGE_ROUND.is_dispatch_state
        assert State.REPORT.is_dispatch_state
        assert not State.CONVERGENCE_CHECK.is_dispatch_state
        assert not State.DONE.is_dispatch_state

    def test_terminal_states(self):
        assert State.DONE.is_terminal
        assert State.ABORTED.is_terminal
        assert not State.SELF_REFINEMENT.is_terminal


class TestValidTransitions:
    def test_every_state_has_entry(self):
        for s in State:
            assert s in VALID_TRANSITIONS

    def test_terminal_states_have_no_exits(self):
        assert VALID_TRANSITIONS[State.DONE] == set()
        assert VALID_TRANSITIONS[State.ABORTED] == set()

    def test_aborted_reachable_from_all_non_terminal(self):
        for s in State:
            if not s.is_terminal:
                assert State.ABORTED in VALID_TRANSITIONS[s]

    def test_happy_path_sequence(self):
        path = [
            State.PARSE_FLAGS, State.RESOLVE_SCOPE, State.CONFIRM_SCOPE,
            State.INIT_CACHE, State.POPULATE_CACHE, State.SELF_REFINEMENT,
            State.CONVERGENCE_CHECK, State.CHALLENGE_ROUND,
            State.CHALLENGE_CHECK, State.RESOLUTION, State.REPORT, State.DONE,
        ]
        for i in range(len(path) - 1):
            assert path[i + 1] in VALID_TRANSITIONS[path[i]], (
                f"{path[i].value} -> {path[i+1].value} not allowed"
            )


class TestAgentConfig:
    def test_defaults(self):
        ac = AgentConfig(prefix="SEC", file="security-auditor.md")
        assert ac.prefix == "SEC"
        assert ac.file == "security-auditor.md"
        assert ac.tools == ["Read"]
        assert ac.effort == "medium"
        assert ac.max_turns == 15

    def test_custom_values(self):
        ac = AgentConfig(
            prefix="CORR", file="correctness-verifier.md",
            tools=["Read", "Grep"], effort="high", max_turns=25,
        )
        assert ac.prefix == "CORR"
        assert ac.file == "correctness-verifier.md"
        assert ac.tools == ["Read", "Grep"]
        assert ac.effort == "high"
        assert ac.max_turns == 25

    def test_tools_default_is_independent(self):
        a1 = AgentConfig(prefix="A", file="a.md")
        a2 = AgentConfig(prefix="B", file="b.md")
        a1.tools.append("Grep")
        assert a2.tools == ["Read"]

    def test_allowed_tools_constant(self):
        assert ALLOWED_AGENT_TOOLS == {"Read", "Write", "Grep", "Glob"}

    def test_valid_effort_levels_constant(self):
        assert VALID_EFFORT_LEVELS == {"low", "medium", "high", "xhigh", "max"}


class TestFsmConfig:
    def test_from_dict(self):
        cfg = FsmConfig(
            profile="code",
            agents=[
                AgentConfig(prefix="SEC", file="sec.md"),
                AgentConfig(prefix="CORR", file="corr.md"),
            ],
            budget_limit=150000,
            max_iterations=2,
            min_iterations=1,
            flags={"save": True},
        )
        assert cfg.profile == "code"
        assert len(cfg.agents) == 2
        assert cfg.agents[0].prefix == "SEC"
        assert cfg.agents[1].prefix == "CORR"
        assert cfg.budget_limit == 150000

    def test_no_budget(self):
        cfg = FsmConfig(
            profile="code",
            agents=[AgentConfig(prefix="SEC", file="sec.md")],
            budget_limit=0,
            max_iterations=2, min_iterations=1, flags={"no_budget": True},
        )
        assert cfg.budget_limit == 0

    def test_source_root_default(self):
        cfg = FsmConfig(
            profile="code",
            agents=[AgentConfig(prefix="SEC", file="sec.md")],
            budget_limit=0,
            max_iterations=1, min_iterations=1,
        )
        assert cfg.source_root == ""

    def test_min_iterations_default(self):
        cfg = FsmConfig(
            profile="code",
            agents=[AgentConfig(prefix="SEC", file="sec.md")],
            budget_limit=0,
            max_iterations=1,
        )
        assert cfg.min_iterations == 1


class TestRedTeamStates:
    def test_red_team_states_exist(self):
        assert State.RED_TEAM_AUDIT.value == "RED_TEAM_AUDIT"
        assert State.RED_TEAM_CHECK.value == "RED_TEAM_CHECK"
        assert State.RED_TEAM_DEEP_DIVE.value == "RED_TEAM_DEEP_DIVE"

    def test_red_team_dispatch_states(self):
        assert State.RED_TEAM_AUDIT.is_dispatch_state
        assert State.RED_TEAM_DEEP_DIVE.is_dispatch_state
        assert not State.RED_TEAM_CHECK.is_dispatch_state

    def test_red_team_transitions(self):
        assert State.RED_TEAM_AUDIT in VALID_TRANSITIONS[State.RESOLUTION]
        assert State.RED_TEAM_CHECK in VALID_TRANSITIONS[State.RED_TEAM_AUDIT]
        assert State.RED_TEAM_DEEP_DIVE in VALID_TRANSITIONS[State.RED_TEAM_CHECK]
        assert State.REPORT in VALID_TRANSITIONS[State.RED_TEAM_CHECK]
        assert State.RESOLUTION in VALID_TRANSITIONS[State.RED_TEAM_DEEP_DIVE]

    def test_red_team_phase_names(self):
        assert State.RED_TEAM_AUDIT.phase_name == "red-team-audit"
        assert State.RED_TEAM_CHECK.phase_name == "red-team-check"
        assert State.RED_TEAM_DEEP_DIVE.phase_name == "red-team-deep-dive"

    def test_red_team_completed_default(self):
        state = FsmState(current_state=State.RESOLUTION)
        assert state.red_team_completed is False

    def test_red_team_not_terminal(self):
        for s in [State.RED_TEAM_AUDIT, State.RED_TEAM_CHECK, State.RED_TEAM_DEEP_DIVE]:
            assert not s.is_terminal
