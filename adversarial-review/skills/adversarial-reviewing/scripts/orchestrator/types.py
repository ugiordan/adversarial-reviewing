from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class State(Enum):
    PARSE_FLAGS = "PARSE_FLAGS"
    RESOLVE_SCOPE = "RESOLVE_SCOPE"
    CONFIRM_SCOPE = "CONFIRM_SCOPE"
    INIT_CACHE = "INIT_CACHE"
    POPULATE_CACHE = "POPULATE_CACHE"
    SELF_REFINEMENT = "SELF_REFINEMENT"
    CONVERGENCE_CHECK = "CONVERGENCE_CHECK"
    CHALLENGE_ROUND = "CHALLENGE_ROUND"
    CHALLENGE_CHECK = "CHALLENGE_CHECK"
    RESOLUTION = "RESOLUTION"
    REPORT = "REPORT"
    DONE = "DONE"
    ABORTED = "ABORTED"
    RED_TEAM_AUDIT = "RED_TEAM_AUDIT"
    RED_TEAM_CHECK = "RED_TEAM_CHECK"
    RED_TEAM_DEEP_DIVE = "RED_TEAM_DEEP_DIVE"

    @property
    def is_dispatch_state(self) -> bool:
        return self in (State.SELF_REFINEMENT, State.CHALLENGE_ROUND, State.REPORT,
                        State.RED_TEAM_AUDIT, State.RED_TEAM_DEEP_DIVE)

    @property
    def is_terminal(self) -> bool:
        return self in (State.DONE, State.ABORTED)

    @property
    def phase_name(self) -> str:
        return _STATE_PHASE_MAP.get(self, "unknown")


PHASE_SELF_REFINEMENT = "self-refinement"
PHASE_CHALLENGE_ROUND = "challenge-round"

_STATE_PHASE_MAP = {
    State.SELF_REFINEMENT: PHASE_SELF_REFINEMENT,
    State.CONVERGENCE_CHECK: "convergence-check",
    State.CHALLENGE_ROUND: PHASE_CHALLENGE_ROUND,
    State.CHALLENGE_CHECK: "challenge-check",
    State.RESOLUTION: "resolution",
    State.REPORT: "report",
    State.RED_TEAM_AUDIT: "red-team-audit",
    State.RED_TEAM_CHECK: "red-team-check",
    State.RED_TEAM_DEEP_DIVE: "red-team-deep-dive",
}

VALID_TRANSITIONS: dict[State, set[State]] = {
    State.PARSE_FLAGS: {State.RESOLVE_SCOPE, State.ABORTED},
    State.RESOLVE_SCOPE: {State.CONFIRM_SCOPE, State.ABORTED},
    State.CONFIRM_SCOPE: {State.INIT_CACHE, State.ABORTED},
    State.INIT_CACHE: {State.POPULATE_CACHE, State.SELF_REFINEMENT, State.ABORTED},
    State.POPULATE_CACHE: {State.SELF_REFINEMENT, State.ABORTED},
    State.SELF_REFINEMENT: {State.CONVERGENCE_CHECK, State.ABORTED},
    State.CONVERGENCE_CHECK: {State.SELF_REFINEMENT, State.CHALLENGE_ROUND, State.RESOLUTION, State.ABORTED},
    State.CHALLENGE_ROUND: {State.CHALLENGE_CHECK, State.ABORTED},
    State.CHALLENGE_CHECK: {State.CHALLENGE_ROUND, State.RESOLUTION, State.ABORTED},
    State.RESOLUTION: {State.REPORT, State.RED_TEAM_AUDIT, State.ABORTED},
    State.REPORT: {State.DONE, State.ABORTED},
    State.DONE: set(),
    State.ABORTED: set(),
    State.RED_TEAM_AUDIT: {State.RED_TEAM_CHECK, State.ABORTED},
    State.RED_TEAM_CHECK: {State.RED_TEAM_DEEP_DIVE, State.REPORT, State.ABORTED},
    State.RED_TEAM_DEEP_DIVE: {State.RESOLUTION, State.ABORTED},
}


class InvalidTransitionError(Exception):
    pass


class RetryDispatchError(Exception):
    """Raised when an agent output fails delimiter checks and a retry dispatch is needed.

    Caught in __main__.handle_next to translate into sys.exit(1).
    """
    pass


ALLOWED_AGENT_TOOLS = {"Read", "Write", "Grep", "Glob"}
VALID_EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}


@dataclass
class AgentConfig:
    prefix: str
    file: str
    tools: list[str] = field(default_factory=lambda: ["Read"])
    effort: str = "medium"
    max_turns: int = 15


@dataclass
class FsmConfig:
    profile: str
    agents: list[AgentConfig]
    budget_limit: int
    max_iterations: int
    min_iterations: int = 1
    flags: dict = field(default_factory=dict)
    target: str = ""
    source_root: str = ""
    specialist_flags: list[str] = field(default_factory=list)
    topic: str = ""


@dataclass
class DispatchAgent:
    id: str
    description: str
    prompt_file: str
    output_file: str


@dataclass
class Delimiters:
    begin: str
    end: str
    hex: str


@dataclass
class ActiveRetry:
    phase: str
    iteration: int
    attempt: int
    failed_agent: str = ""


@dataclass
class FsmState:
    current_state: State
    iteration: int = 1
    challenge_iteration: int = 0
    delimiters: Optional[Delimiters] = None
    completed_outputs: set[str] = field(default_factory=set)
    config: Optional[FsmConfig] = None
    budget_consumed: int = 0
    budget_remaining: int = 0
    round_history: list[dict] = field(default_factory=list)
    convergence: dict = field(default_factory=dict)
    prompt_hashes: dict = field(default_factory=dict)
    relay_compliance_rounds: int = 0
    relay_compliance_violations: int = 0
    relay_compliance_warnings: int = 0
    active_retry: Optional[ActiveRetry] = None
    guardrail_log: list[dict] = field(default_factory=list)
    self_refinement_iterations: int = 0
    dispatch_history: list[dict] = field(default_factory=list)
    resolution_warning: str = ""
    red_team_completed: bool = False
    error: Optional[dict] = None
