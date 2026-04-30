from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path
from .types import (
    State, FsmState, FsmConfig, Delimiters, ActiveRetry, AgentConfig, SAFE_ID_RE,
)

STATE_FILE = "fsm-state.json"
_HMAC_KEY_FILE = ".state-integrity-key"
_DELIMITER_RE = re.compile(r"^===REVIEW_TARGET_([0-9a-f]{32})_(START|END)===$")


class StateError(Exception):
    pass


def save_state(state: FsmState, cache_dir: str | Path) -> None:
    data = _serialize(state)
    json_bytes = json.dumps(data, indent=2).encode()
    path = Path(cache_dir) / STATE_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(json_bytes)
    tmp.replace(path)
    key = _get_or_create_hmac_key(cache_dir)
    mac = hmac.new(key, json_bytes, hashlib.sha256).hexdigest()
    (Path(cache_dir) / f"{STATE_FILE}.hmac").write_text(mac)


def load_state(cache_dir: str | Path) -> FsmState:
    path = Path(cache_dir) / STATE_FILE
    if not path.exists():
        raise StateError(f"fsm-state.json not found in {cache_dir}")
    json_bytes = path.read_bytes()
    _verify_hmac(cache_dir, json_bytes)
    try:
        data = json.loads(json_bytes)
    except json.JSONDecodeError as e:
        raise StateError(f"fsm-state.json corrupted: {e}") from e
    return _deserialize(data)


def _get_or_create_hmac_key(cache_dir: str | Path) -> bytes:
    key_path = Path(cache_dir) / _HMAC_KEY_FILE
    if key_path.exists():
        return key_path.read_bytes()
    key = secrets.token_bytes(32)
    key_path.write_bytes(key)
    os.chmod(key_path, 0o600)
    return key


def _verify_hmac(cache_dir: str | Path, json_bytes: bytes) -> None:
    key_path = Path(cache_dir) / _HMAC_KEY_FILE
    hmac_path = Path(cache_dir) / f"{STATE_FILE}.hmac"
    key_exists = key_path.exists()
    hmac_exists = hmac_path.exists()
    if not key_exists and not hmac_exists:
        # First run: neither file exists yet, nothing to verify.
        return
    state_path = Path(cache_dir) / STATE_FILE
    if state_path.exists() and (key_exists != hmac_exists):
        missing = _HMAC_KEY_FILE if not key_exists else f"{STATE_FILE}.hmac"
        raise StateError(
            f"State integrity file missing: {missing}. "
            "Possible tampering or incomplete write."
        )
    key = key_path.read_bytes()
    expected = hmac.new(key, json_bytes, hashlib.sha256).hexdigest()
    actual = hmac_path.read_text().strip()
    if not hmac.compare_digest(expected, actual):
        raise StateError("State file integrity check failed (HMAC mismatch)")


def _serialize(state: FsmState) -> dict:
    d = {
        "current_state": state.current_state.value,
        "iteration": state.iteration,
        "challenge_iteration": state.challenge_iteration,
        "completed_outputs": sorted(state.completed_outputs),
        "budget": {
            "consumed": state.budget_consumed,
            "remaining": state.budget_remaining,
            "round_history": state.round_history,
        },
        "convergence": state.convergence,
        "prompt_hashes": state.prompt_hashes,
        "relay_compliance": {
            "rounds_checked": state.relay_compliance_rounds,
            "violations": state.relay_compliance_violations,
            "warnings": state.relay_compliance_warnings,
            "active_retry": (
                {"phase": state.active_retry.phase,
                 "iteration": state.active_retry.iteration,
                 "attempt": state.active_retry.attempt,
                 "failed_agent": state.active_retry.failed_agent}
                if state.active_retry else None
            ),
        },
        "guardrail_log": state.guardrail_log,
        "self_refinement_iterations": state.self_refinement_iterations,
        "dispatch_history": state.dispatch_history,
        "resolution_warning": state.resolution_warning,
        "red_team_completed": state.red_team_completed,
    }
    if state.delimiters:
        d["delimiters"] = {
            "begin": state.delimiters.begin,
            "end": state.delimiters.end,
            "hex": state.delimiters.hex,
        }
    if state.config:
        d["config"] = {
            "profile": state.config.profile,
            "agents": [
                {
                    "prefix": a.prefix, "file": a.file,
                    "tools": a.tools, "effort": a.effort,
                    "max_turns": a.max_turns,
                }
                for a in state.config.agents
            ],
            "budget_limit": state.config.budget_limit,
            "max_iterations": state.config.max_iterations,
            "min_iterations": state.config.min_iterations,
            "flags": state.config.flags,
            "target": state.config.target,
            "source_root": state.config.source_root,
            "specialist_flags": state.config.specialist_flags,
            "topic": state.config.topic,
        }
    if state.error:
        d["error"] = state.error
    return d


def _deserialize(data: dict) -> FsmState:
    state_name = data.get("current_state", "")
    try:
        current = State(state_name)
    except ValueError:
        raise StateError(
            f"FSM version mismatch or state corruption: unknown state '{state_name}'"
        )

    delimiters = None
    if "delimiters" in data:
        d = data["delimiters"]
        begin, end = d["begin"], d["end"]
        begin_m = _DELIMITER_RE.match(begin)
        end_m = _DELIMITER_RE.match(end)
        if not begin_m or not end_m:
            raise StateError(f"Invalid delimiter format in state file")
        if begin_m.group(1) != end_m.group(1):
            raise StateError("Delimiter begin/end hex values do not match")
        hex_val = d.get("hex", "")
        if hex_val and begin_m.group(1) != hex_val:
            raise StateError("Delimiter hex mismatch in state file")
        delimiters = Delimiters(begin=begin, end=end, hex=hex_val or begin_m.group(1))

    config = None
    if "config" in data:
        c = data["config"]
        profile = c["profile"]
        if not SAFE_ID_RE.match(profile):
            raise StateError(f"Invalid profile name in state: {profile}")
        raw_agents = c["agents"]
        agents = []
        for a in raw_agents:
            if isinstance(a, dict):
                agents.append(AgentConfig(
                    prefix=a["prefix"], file=a.get("file", ""),
                    tools=a.get("tools", ["Read"]),
                    effort=a.get("effort", "medium"),
                    max_turns=a.get("max_turns", 15),
                ))
            elif isinstance(a, str):
                agents.append(AgentConfig(prefix=a, file=""))
            else:
                raise StateError(f"Invalid agent entry in state: {a}")
        for agent_cfg in agents:
            if not SAFE_ID_RE.match(agent_cfg.prefix):
                raise StateError(f"Invalid agent ID in state: {agent_cfg.prefix}")
        max_iter = c["max_iterations"]
        if not isinstance(max_iter, int) or max_iter < 1 or max_iter > 100:
            raise StateError(f"max_iterations out of range: {max_iter}")
        min_iter = c.get("min_iterations", 1)
        if not isinstance(min_iter, int) or min_iter < 1 or min_iter > max_iter:
            raise StateError(
                f"min_iterations out of range: {min_iter} (max_iterations={max_iter})"
            )
        budget_limit = c["budget_limit"]
        if not isinstance(budget_limit, int) or budget_limit < 0:
            raise StateError(f"budget_limit out of range: {budget_limit}")

        flags = c.get("flags", {})
        if not isinstance(flags, dict):
            raise StateError("flags must be a dict")
        _KNOWN_BOOL_FLAGS = {
            "save", "delta", "diff", "normalize", "persist", "no_budget",
            "keep_cache", "fix", "force", "strict_scope", "dry_run", "converge",
            "gap_analysis", "list_references", "update_references", "review_only",
            "confirm",
        }
        _KNOWN_STRING_FLAGS = {
            "reuse_cache", "constraints", "principles", "range", "triage",
            "arch_context",
        }
        for key in _KNOWN_BOOL_FLAGS:
            if key in flags and not isinstance(flags[key], bool):
                raise StateError(
                    f"Flag '{key}' must be boolean, got {type(flags[key]).__name__}: {flags[key]!r}"
                )
        if "context" in flags:
            if not isinstance(flags["context"], list):
                raise StateError(
                    f"Flag 'context' must be a list, got {type(flags['context']).__name__}: {flags['context']!r}"
                )
            for idx, x in enumerate(flags["context"]):
                if not isinstance(x, str):
                    raise StateError(
                        f"Flag 'context' element {idx} must be string, got {type(x).__name__}: {x!r}"
                    )
        for str_key in _KNOWN_STRING_FLAGS:
            if str_key in flags and not isinstance(flags[str_key], str):
                raise StateError(
                    f"Flag '{str_key}' must be a string, got {type(flags[str_key]).__name__}: {flags[str_key]!r}"
                )

        source_root = c.get("source_root", "")
        if source_root and not os.path.isabs(source_root):
            raise StateError(f"source_root must be an absolute path: {source_root}")

        specialist_flags = c.get("specialist_flags", [])
        if not isinstance(specialist_flags, list):
            raise StateError(
                f"specialist_flags must be a list, got {type(specialist_flags).__name__}"
            )
        for idx, sf in enumerate(specialist_flags):
            if not isinstance(sf, str):
                raise StateError(
                    f"specialist_flags element {idx} must be string, got {type(sf).__name__}: {sf!r}"
                )

        topic = c.get("topic", "")
        if not isinstance(topic, str):
            raise StateError(f"topic must be a string, got {type(topic).__name__}: {topic!r}")

        config = FsmConfig(
            profile=profile, agents=agents,
            budget_limit=budget_limit,
            max_iterations=max_iter,
            min_iterations=min_iter,
            flags=flags,
            target=c.get("target", ""),
            source_root=source_root,
            specialist_flags=specialist_flags,
            topic=topic,
        )

    budget = data.get("budget", {})
    compliance = data.get("relay_compliance", {})

    active_retry = None
    retry_data = compliance.get("active_retry")
    if retry_data:
        active_retry = ActiveRetry(
            phase=retry_data["phase"],
            iteration=retry_data["iteration"],
            attempt=retry_data["attempt"],
            failed_agent=retry_data.get("failed_agent", ""),
        )

    iteration = data.get("iteration", 1)
    if not isinstance(iteration, int) or iteration < 1:
        raise StateError(f"iteration out of range: {iteration}")

    challenge_iteration = data.get("challenge_iteration", 0)
    if not isinstance(challenge_iteration, int) or challenge_iteration < 0:
        raise StateError(f"challenge_iteration out of range: {challenge_iteration}")

    self_ref = data.get("self_refinement_iterations", 0)
    if not isinstance(self_ref, int) or self_ref < 0:
        raise StateError(f"self_refinement_iterations out of range: {self_ref}")

    budget_consumed = budget.get("consumed", 0)
    if not isinstance(budget_consumed, int) or budget_consumed < 0:
        raise StateError(f"budget consumed out of range: {budget_consumed}")

    budget_remaining = budget.get("remaining", 0)
    if not isinstance(budget_remaining, int) or budget_remaining < 0:
        raise StateError(f"budget remaining out of range: {budget_remaining}")

    red_team_completed = data.get("red_team_completed", False)
    if not isinstance(red_team_completed, bool):
        raise StateError(f"red_team_completed must be boolean, got {type(red_team_completed).__name__}")

    dispatch_history = data.get("dispatch_history", [])
    if not isinstance(dispatch_history, list):
        raise StateError("dispatch_history must be a list")
    for entry in dispatch_history:
        if not isinstance(entry, dict):
            raise StateError("dispatch_history entries must be dicts")
        for required_key in ("phase", "iteration", "agents"):
            if required_key not in entry:
                raise StateError(f"dispatch_history entry missing required key: {required_key}")
        if not isinstance(entry.get("agents", []), list):
            raise StateError("dispatch_history entry 'agents' must be a list")
        for agent_id in entry.get("agents", []):
            if not isinstance(agent_id, str):
                raise StateError(f"dispatch_history agent ID must be string, got {type(agent_id).__name__}")
            if not SAFE_ID_RE.match(agent_id):
                raise StateError(f"Invalid agent ID in dispatch_history: {agent_id}")

    return FsmState(
        current_state=current,
        iteration=iteration,
        challenge_iteration=challenge_iteration,
        delimiters=delimiters,
        completed_outputs=set(data.get("completed_outputs", [])),
        config=config,
        budget_consumed=budget_consumed,
        budget_remaining=budget_remaining,
        round_history=budget.get("round_history", []),
        convergence=data.get("convergence", {}),
        prompt_hashes=data.get("prompt_hashes", {}),
        relay_compliance_rounds=compliance.get("rounds_checked", 0),
        relay_compliance_violations=compliance.get("violations", 0),
        relay_compliance_warnings=compliance.get("warnings", 0),
        active_retry=active_retry,
        self_refinement_iterations=self_ref,
        guardrail_log=data.get("guardrail_log", []),
        dispatch_history=dispatch_history,
        resolution_warning=data.get("resolution_warning", ""),
        red_team_completed=red_team_completed,
        error=data.get("error"),
    )
