"""FSM state machine logic for the adversarial-reviewing orchestrator."""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import budget, cache as cache_mod, convergence, telemetry
from .config import read_profile_config
from .dispatch import write_dispatch, write_dispatch_v3, write_terminal
from .prompt import (
    compose_prompt, load_shared_templates, prepare_dispatch_directory,
    _inline_source_files,
)
from .state import save_state
from .subprocess_utils import (
    fatal_error, ScriptError, run_script as _subprocess_run_script,
    run_python_script as _subprocess_run_python,
)
from .types import (
    State, FsmState, FsmConfig, DispatchAgent, ActiveRetry, AgentConfig,
    VALID_TRANSITIONS, InvalidTransitionError, RetryDispatchError,
    PHASE_SELF_REFINEMENT, PHASE_CHALLENGE_ROUND,
)
from .validation import (
    check_outputs_exist, check_delimiters, check_prompt_hashes,
    check_output_sizes, compute_content_hash,
)

_MAX_FINDINGS_SIZE = 500_000
_MAX_CHALLENGE_ITERATIONS = 3

_profile_config_cache: dict[str, dict] = {}
_templates_cache: dict[str, dict] = {}


# -- Public entry points --

def process_state(state: FsmState, cache_dir: str, skill_dir: str):
    root_span = telemetry.start_span("adversarial_review", {
        "profile": state.config.profile,
        "target": state.config.target or "",
        "budget_limit": state.config.budget_limit,
        "agents": [a.prefix for a in state.config.agents],
    })
    try:
        while True:
            handler = _STATE_HANDLERS.get(state.current_state)
            if handler is None:
                fatal_error(f"Cannot call 'next' from state {state.current_state.value}")
            result = handler(state, cache_dir, skill_dir)
            if result != "continue":
                break
    finally:
        telemetry.end_span(root_span, {
            "final_state": state.current_state.value,
            "iterations": state.iteration,
            "budget_consumed": state.budget_consumed,
        })


def resume_dispatch_state(state: FsmState, cache_dir: str, skill_dir: str):
    if state.current_state == State.REPORT:
        report_output = os.path.join(cache_dir, "outputs", "REPORT.md")
        if os.path.exists(report_output):
            process_state(state, cache_dir, skill_dir)
        else:
            _write_report_dispatch(state, cache_dir, skill_dir)
            save_state(state, cache_dir)
        return

    last = state.dispatch_history[-1] if state.dispatch_history else {}
    agents = last.get("agents", [a.prefix for a in state.config.agents])
    phase = last.get("phase", PHASE_SELF_REFINEMENT)
    iteration = _current_phase_iteration(state)

    existing = []
    for agent_id in agents:
        fname = _agent_filename(agent_id, phase, iteration)
        path = os.path.join(cache_dir, "outputs", fname)
        if os.path.exists(path):
            existing.append(fname)

    if len(existing) == len(agents):
        process_state(state, cache_dir, skill_dir)
    else:
        write_agent_dispatch(state, cache_dir, skill_dir, phase)
        save_state(state, cache_dir)


def is_budget_exceeded(state: FsmState) -> bool:
    if state.config.flags.get("no_budget") or state.config.budget_limit == 0:
        return False
    return state.budget_consumed >= state.config.budget_limit


def transition(state: FsmState, new_state: State):
    allowed = VALID_TRANSITIONS.get(state.current_state, set())
    if new_state not in allowed:
        raise InvalidTransitionError(
            f"{state.current_state.value} -> {new_state.value}"
        )
    state.current_state = new_state


def abort(state: FsmState, cache_dir: str, error_type: str, message: str):
    if not state.current_state.is_terminal:
        transition(state, State.ABORTED)
    state.error = {"type": error_type, "message": message}
    try:
        save_state(state, cache_dir)
    except Exception:
        pass
    fatal_error(message, recoverable=False)


def log_guardrail(state, category, name, agent, level, details):
    state.guardrail_log.append({
        "timestamp": _now(),
        "category": category,
        "name": name,
        "agent": agent,
        "level": level,
        "details": details,
    })


# -- State processors (each returns "continue" or None) --

def _process_self_refinement(state, cache_dir, skill_dir):
    span = telemetry.start_span(
        f"phase.self_refinement.iter{state.iteration}",
        {"phase": PHASE_SELF_REFINEMENT, "iteration": state.iteration},
    )
    _run_compliance_checks(state, cache_dir)
    _measure_budget(state, cache_dir, skill_dir)
    _run_post_self_refinement_scripts(state, cache_dir, skill_dir)
    transition(state, State.CONVERGENCE_CHECK)
    save_state(state, cache_dir)
    telemetry.end_span(span, {"budget_consumed": state.budget_consumed})
    return "continue"


def _process_convergence_check(state, cache_dir, skill_dir):
    span = telemetry.start_span(
        f"convergence_check.iter{state.iteration}",
        {"phase": "convergence-check", "iteration": state.iteration},
    )
    state.self_refinement_iterations = state.iteration

    decision = _evaluate_convergence(state, cache_dir, skill_dir)

    if decision == "continue":
        state.iteration += 1
        transition(state, State.SELF_REFINEMENT)
        write_agent_dispatch(state, cache_dir, skill_dir, PHASE_SELF_REFINEMENT)
        save_state(state, cache_dir)
        telemetry.end_span(span, {"decision": decision})
        return None
    elif decision == "budget_exceeded":
        transition(state, State.RESOLUTION)
        save_state(state, cache_dir)
        telemetry.end_span(span, {"decision": decision})
        return "continue"
    else:
        state.challenge_iteration = 1
        _run_pre_challenge_scripts(state, cache_dir, skill_dir)
        transition(state, State.CHALLENGE_ROUND)
        write_agent_dispatch(state, cache_dir, skill_dir, PHASE_CHALLENGE_ROUND)
        save_state(state, cache_dir)
        telemetry.end_span(span, {"decision": decision})
        return None


def _process_challenge_round(state, cache_dir, skill_dir):
    span = telemetry.start_span(
        f"phase.challenge_round.iter{state.challenge_iteration}",
        {"phase": PHASE_CHALLENGE_ROUND, "iteration": state.challenge_iteration},
    )
    _run_compliance_checks(state, cache_dir)
    _measure_budget(state, cache_dir, skill_dir)
    transition(state, State.CHALLENGE_CHECK)
    save_state(state, cache_dir)
    telemetry.end_span(span, {"budget_consumed": state.budget_consumed})
    return "continue"


def _process_challenge_check(state, cache_dir, skill_dir):
    span = telemetry.start_span(
        f"challenge_check.iter{state.challenge_iteration}",
        {"phase": "challenge-check", "iteration": state.challenge_iteration},
    )
    budget_exceeded = is_budget_exceeded(state)
    remaining = max(0, state.config.max_iterations - state.self_refinement_iterations)
    max_challenge_iter = min(_MAX_CHALLENGE_ITERATIONS, remaining)

    if state.challenge_iteration < max_challenge_iter and not budget_exceeded:
        state.challenge_iteration += 1
        transition(state, State.CHALLENGE_ROUND)
        write_agent_dispatch(state, cache_dir, skill_dir, PHASE_CHALLENGE_ROUND)
        save_state(state, cache_dir)
        telemetry.end_span(span, {"decision": "continue"})
        return None
    else:
        transition(state, State.RESOLUTION)
        save_state(state, cache_dir)
        telemetry.end_span(span, {"decision": "done"})
        return "continue"


def _process_resolution(state, cache_dir, skill_dir):
    span = telemetry.start_span(
        "phase.resolution",
        {"phase": "resolution"},
    )
    from .phases.resolution import run_resolution
    try:
        run_resolution(cache_dir, skill_dir)
    except FileNotFoundError as e:
        msg = f"Resolution script not found: {e}"
        log_guardrail(state, "resolution", "deduplicate", "", "warning", msg)
        print(json.dumps({"warning": "resolution_skipped", "message": msg}),
              file=sys.stderr)
    except ScriptError as e:
        msg = f"Resolution phase failed: {e}"
        log_guardrail(state, "resolution", "deduplicate", "", "warning", msg)
        state.resolution_warning = msg
        print(json.dumps({"warning": "resolution_failed", "message": msg}),
              file=sys.stderr)

    if state.red_team_completed:
        transition(state, State.REPORT)
        _write_report_dispatch(state, cache_dir, skill_dir)
    else:
        transition(state, State.RED_TEAM_AUDIT)
        _write_red_team_dispatch(state, cache_dir, skill_dir)
    save_state(state, cache_dir)
    telemetry.end_span(span, {"final_state": state.current_state.value})
    return None


def _process_red_team_audit(state, cache_dir, skill_dir):
    """Process RED_TEAM_AUDIT: compliance checks after red team agent completes."""
    _run_compliance_checks(state, cache_dir)
    transition(state, State.RED_TEAM_CHECK)
    save_state(state, cache_dir)
    return "continue"


def _process_red_team_check(state, cache_dir, skill_dir):
    """Process RED_TEAM_CHECK: parse audit output, decide deep dives."""
    audit_dir = os.path.join(cache_dir, "dispatch", "RED-TEAM-red-team-audit-iter1")
    audit_output = os.path.join(audit_dir, "output.md")

    has_flags = False
    if os.path.isfile(audit_output):
        content = Path(audit_output).read_text()
        has_flags = "FLAG:" in content or "BLIND_SPOT:" in content
        if "NO_FLAGS_REPORTED" in content:
            has_flags = False

    if has_flags and not state.red_team_completed:
        log_guardrail(state, "red_team", "audit_flags", "",
                      "info", "Red team audit found flags, dispatching deep dives")
        try:
            _run_legacy_script("prepare-deep-dives.py",
                               [audit_output, os.path.join(cache_dir, "dispatch")],
                               cache_dir, skill_dir)
        except Exception as e:
            log_guardrail(state, "red_team", "prepare_deep_dives", "",
                          "warning", f"prepare-deep-dives.py failed: {e}")
            has_flags = False

    if has_flags and not state.red_team_completed:
        deep_dive_available = _has_deep_dive_dirs(cache_dir)
        if deep_dive_available:
            transition(state, State.RED_TEAM_DEEP_DIVE)
            _write_deep_dive_dispatch(state, cache_dir, skill_dir)
        else:
            log_guardrail(state, "red_team", "no_deep_dives", "",
                          "info", "Flags found but no deep dive directories, proceeding to report")
            transition(state, State.REPORT)
            _write_report_dispatch(state, cache_dir, skill_dir)
    else:
        log_guardrail(state, "red_team", "skip_deep_dives", "",
                      "info", "No flags or red team already completed, proceeding to report")
        transition(state, State.REPORT)
        _write_report_dispatch(state, cache_dir, skill_dir)
    save_state(state, cache_dir)
    return None


def _process_red_team_deep_dive(state, cache_dir, skill_dir):
    """Process RED_TEAM_DEEP_DIVE: compliance checks after deep dive agents complete."""
    _run_compliance_checks(state, cache_dir)
    state.red_team_completed = True

    # Collect deep dive outputs and re-run resolution
    try:
        deep_dive_dir = os.path.join(cache_dir, "deep-dive-results")
        os.makedirs(deep_dive_dir, exist_ok=True)
        dispatch_dir = os.path.join(cache_dir, "dispatch")
        if os.path.isdir(dispatch_dir):
            import shutil
            for entry in os.listdir(dispatch_dir):
                if entry.startswith("DEEP-DIVE-"):
                    output = os.path.join(dispatch_dir, entry, "output.md")
                    if os.path.isfile(output):
                        shutil.copy2(output, os.path.join(deep_dive_dir, f"{entry}.md"))

        _run_legacy_script("resolve-votes.py",
                           [os.path.join(cache_dir, "votes.json"),
                            "--deep-dive-results", deep_dive_dir],
                           cache_dir, skill_dir)
    except Exception as e:
        log_guardrail(state, "red_team", "resolve_deep_dives", "",
                      "warning", f"resolve-votes.py --deep-dive-results failed: {e}")

    transition(state, State.RESOLUTION)
    save_state(state, cache_dir)
    return "continue"


def _process_report(state, cache_dir, skill_dir):
    span = telemetry.start_span(
        "phase.report",
        {"phase": "report"},
    )
    _run_compliance_checks(state, cache_dir)

    report_path = os.path.join(cache_dir, "outputs", "REPORT.md")
    transition(state, State.DONE)
    save_state(state, cache_dir)
    write_terminal(cache_dir, report_path, "Review complete.")
    telemetry.end_span(span, {"final_state": state.current_state.value})
    return None


# -- Convergence --

def _evaluate_convergence(state, cache_dir, skill_dir) -> str:
    budget_exceeded = is_budget_exceeded(state)
    converged = False

    if state.iteration >= state.config.min_iterations:
        converged = _check_agent_convergence(state, cache_dir, skill_dir)

    if not converged and state.iteration < state.config.max_iterations and not budget_exceeded:
        return "continue"
    if budget_exceeded:
        return "budget_exceeded"
    if converged:
        return "converged"
    return "max_iterations"


# -- Dispatch helpers --

def _agent_filename(prefix: str, phase: str, iteration: int) -> str:
    if phase == PHASE_CHALLENGE_ROUND:
        return f"{prefix}-challenge-iter{iteration}.md"
    return f"{prefix}-phase1-iter{iteration}.md"


def _current_phase_iteration(state: FsmState) -> int:
    if state.current_state in (State.CHALLENGE_ROUND, State.CHALLENGE_CHECK):
        return state.challenge_iteration
    return state.iteration


def _prepare_agent_prompts(state, cache_dir, skill_dir, phase) -> list[tuple[str, str, str]]:
    profile_dir = os.path.join(skill_dir, "profiles", state.config.profile)
    if profile_dir not in _profile_config_cache:
        _profile_config_cache[profile_dir] = read_profile_config(profile_dir)
    profile_cfg = _profile_config_cache[profile_dir]
    agent_map = {a["prefix"]: a["file"] for a in profile_cfg["agents"]}

    if profile_dir not in _templates_cache:
        _templates_cache[profile_dir] = load_shared_templates(profile_dir)
    shared_templates = _templates_cache[profile_dir]

    iteration = _current_phase_iteration(state)
    results = []
    for agent_cfg in state.config.agents:
        agent_file = agent_cfg.file or agent_map.get(agent_cfg.prefix, "")
        fname = _agent_filename(agent_cfg.prefix, phase, iteration)

        output_path = os.path.join(cache_dir, "outputs", fname)
        delims = (state.delimiters.begin, state.delimiters.end) if state.delimiters else ("", "")
        prompt_content = compose_prompt(
            agent_prefix=agent_cfg.prefix, agent_file=agent_file,
            profile_dir=profile_dir, cache_dir=cache_dir,
            source_root=state.config.source_root or os.getcwd(),
            phase=phase,
            iteration=iteration, flags=state.config.flags,
            target=state.config.target,
            shared_templates=shared_templates,
            output_file=output_path,
            delimiters=delims,
        )
        results.append((agent_cfg.prefix, prompt_content, fname))
    return results


def _load_agent_instructions(profile_dir: str, agent_file: str) -> str:
    """Load the .md file content for an agent, with path-traversal checks."""
    if not agent_file or not re.match(r"^[a-zA-Z0-9._-]+$", agent_file):
        return ""
    agent_path = os.path.join(profile_dir, "agents", agent_file)
    resolved = os.path.realpath(agent_path)
    agents_dir = os.path.realpath(os.path.join(profile_dir, "agents"))
    if resolved.startswith(agents_dir + os.sep) and os.path.exists(resolved):
        return Path(resolved).read_text()
    return ""


def _collect_prior_findings(cache_dir: str, agent_id: str, phase: str,
                            iteration: int) -> str:
    """Collect prior iteration outputs for an agent (iteration 2+)."""
    if iteration <= 1:
        return ""
    parts = []
    outputs_dir = os.path.join(cache_dir, "outputs")
    for prev_iter in range(1, iteration):
        fname = _agent_filename(agent_id, phase, prev_iter)
        fpath = os.path.join(outputs_dir, fname)
        if os.path.isfile(fpath):
            try:
                content = Path(fpath).read_text()
                parts.append(f"### Iteration {prev_iter}\n{content}")
            except (UnicodeDecodeError, OSError):
                continue
    return "\n\n".join(parts)


def _prepare_dispatch_directories(state, cache_dir, skill_dir, phase) -> list[tuple[str, str]]:
    """Prepare dispatch directories for all agents. Returns (agent_id, dispatch_path) tuples."""
    profile_dir = os.path.join(skill_dir, "profiles", state.config.profile)
    if profile_dir not in _profile_config_cache:
        _profile_config_cache[profile_dir] = read_profile_config(profile_dir)
    profile_cfg = _profile_config_cache[profile_dir]
    agent_map = {a["prefix"]: a["file"] for a in profile_cfg["agents"]}

    if profile_dir not in _templates_cache:
        _templates_cache[profile_dir] = load_shared_templates(profile_dir)
    shared_templates = _templates_cache[profile_dir]

    common_instructions = shared_templates.get("common", "")
    finding_template = shared_templates.get("finding", "")

    source_files = _inline_source_files(cache_dir, max_tokens=150_000)

    iteration = _current_phase_iteration(state)
    results = []
    for agent_cfg in state.config.agents:
        agent_file = agent_cfg.file or agent_map.get(agent_cfg.prefix, "")
        agent_instructions = _load_agent_instructions(profile_dir, agent_file)
        prior_findings = _collect_prior_findings(
            cache_dir, agent_cfg.prefix, phase, iteration,
        )

        dispatch_path = prepare_dispatch_directory(
            cache_dir=cache_dir,
            agent_id=agent_cfg.prefix,
            phase=phase,
            iteration=iteration,
            agent_instructions=agent_instructions,
            common_instructions=common_instructions,
            finding_template=finding_template,
            source_files=source_files,
            prior_findings=prior_findings,
        )
        results.append((agent_cfg.prefix, dispatch_path))
    return results


def _build_hook_config(skill_dir: str) -> dict:
    # Verify skill_dir contains expected structure beyond just SKILL.md
    for required_subdir in ("profiles", "scripts"):
        if not os.path.isdir(os.path.join(skill_dir, required_subdir)):
            return {}
    hooks_dir = os.path.join(skill_dir, "scripts", "hooks")
    if not os.path.isdir(hooks_dir):
        return {}
    hooks = {}
    pre_path = os.path.join(hooks_dir, "pre_dispatch_validate.py")
    if os.path.isfile(pre_path):
        hooks["PreToolUse"] = [{
            "type": "command",
            "command": f"python3 {shlex.quote(pre_path)}",
            "timeout": 5000,
        }]
    post_path = os.path.join(hooks_dir, "post_output_validate.py")
    if os.path.isfile(post_path):
        hooks["PostToolUse"] = [{
            "type": "command",
            "command": f"python3 {shlex.quote(post_path)}",
            "timeout": 5000,
        }]
    compact_path = os.path.join(hooks_dir, "post_compact_reinject.py")
    if os.path.isfile(compact_path):
        hooks["PostCompact"] = [{
            "type": "command",
            "command": f"python3 {shlex.quote(compact_path)}",
            "timeout": 3000,
        }]
    return hooks


def write_agent_dispatch(state, cache_dir, skill_dir, phase):
    dispatch_dirs = _prepare_dispatch_directories(state, cache_dir, skill_dir, phase)
    iteration = _current_phase_iteration(state)

    # Also write prompt files for compliance checks (prompt hash verification)
    prompts = _prepare_agent_prompts(state, cache_dir, skill_dir, phase)
    for prefix, prompt_content, fname in prompts:
        prompt_path = os.path.join(cache_dir, "prompts", fname)
        Path(prompt_path).write_text(prompt_content)
        state.prompt_hashes[fname] = compute_content_hash(prompt_content)

    phase_num = 1 if phase == PHASE_SELF_REFINEMENT else 2
    try:
        cache_mod.generate_navigation(
            cache_dir, skill_dir,
            state.config.profile if state.config else "code",
            iteration=iteration, phase=phase_num,
        )
    except Exception as e:
        log_guardrail(
            state, "dispatch", "generate_navigation", "", "warning",
            f"Navigation generation failed: {e}",
        )

    label = phase.replace("-", " ").title()
    v3_agents = []
    for agent_id, dispatch_path in dispatch_dirs:
        v3_agents.append({
            "id": agent_id,
            "description": f"{agent_id}: {label} Iteration {iteration}",
            "subagent_type": "review-specialist",
            "dispatch_path": dispatch_path,
        })

    write_dispatch_v3(cache_dir, phase, iteration, v3_agents)

    entry = {
        "phase": phase,
        "iteration": iteration,
        "agents": [a.prefix for a in state.config.agents],
        "timestamp": _now(),
    }
    if (state.dispatch_history
            and state.dispatch_history[-1].get("phase") == phase
            and state.dispatch_history[-1].get("iteration") == iteration):
        log_guardrail(state, "dispatch", "overwrite", "", "info",
                      f"Overwriting dispatch entry for {phase} iter {iteration}")
        state.dispatch_history[-1] = entry
    else:
        state.dispatch_history.append(entry)


def _write_report_dispatch(state, cache_dir, skill_dir):
    profile_dir = os.path.join(skill_dir, "profiles", state.config.profile)
    prompt_path = os.path.join(cache_dir, "prompts", "REPORT.md")

    from .phases.report import compose_report_prompt
    findings_summary = _collect_findings_summary(state, cache_dir)
    resolution_warning = state.resolution_warning
    prompt_content = compose_report_prompt(
        cache_dir, profile_dir, findings_summary,
        target=state.config.target,
        source_root=state.config.source_root,
        delimiter_hex=state.delimiters.hex if state.delimiters else "",
        resolution_warning=resolution_warning,
        skill_dir=skill_dir,
        profile=state.config.profile if state.config else "",
        specialists=[a.prefix for a in state.config.agents] if state.config else None,
        iterations=state.iteration,
        budget_limit=state.config.budget_limit if state.config else 0,
    )
    # Write prompt file for compliance checks (prompt hash verification)
    Path(prompt_path).write_text(prompt_content)
    state.prompt_hashes["REPORT.md"] = compute_content_hash(prompt_content)

    # Create dispatch directory for report agent
    dispatch_path = prepare_dispatch_directory(
        cache_dir=cache_dir,
        agent_id="REPORT",
        phase="report",
        iteration=1,
        agent_instructions=prompt_content,
        common_instructions="",
        finding_template="",
        source_files="",
    )

    v3_agents = [{
        "id": "REPORT",
        "description": "Report Writer",
        "subagent_type": "compose-report",
        "dispatch_path": dispatch_path,
    }]
    write_dispatch_v3(cache_dir, "report", 1, v3_agents, parallel=False)

    entry = {
        "phase": "report",
        "iteration": 1,
        "agents": ["REPORT"],
        "timestamp": _now(),
    }
    if (state.dispatch_history
            and state.dispatch_history[-1].get("phase") == "report"):
        log_guardrail(state, "dispatch", "overwrite", "", "info",
                      "Overwriting dispatch entry for report")
        state.dispatch_history[-1] = entry
    else:
        state.dispatch_history.append(entry)


def _write_red_team_dispatch(state, cache_dir, skill_dir):
    """Write dispatch for red team audit phase."""
    resolved = _collect_findings_summary(state, cache_dir)

    dispatch_path = prepare_dispatch_directory(
        cache_dir=cache_dir,
        agent_id="RED-TEAM",
        phase="red-team-audit",
        iteration=1,
        agent_instructions=(
            "Audit the consensus findings for weak evidence, severity inflation, "
            "groupthink, and blind spots. For each concern, write "
            "FLAG: {FINDING_ID} - {concern}. For blind spots, write "
            "BLIND_SPOT: {description}. If no concerns, write NO_FLAGS_REPORTED."
        ),
        common_instructions="",
        finding_template="",
        source_files=resolved,
    )

    write_dispatch_v3(cache_dir, "red-team-audit", 1, [
        {"id": "RED-TEAM", "subagent_type": "red-team-auditor",
         "dispatch_path": dispatch_path},
    ], parallel=False)

    entry = {
        "phase": "red-team-audit",
        "iteration": 1,
        "agents": ["RED-TEAM"],
        "timestamp": _now(),
    }
    state.dispatch_history.append(entry)


def _has_deep_dive_dirs(cache_dir: str) -> bool:
    """Check whether prepare-deep-dives.py created any DEEP-DIVE-* directories."""
    dispatch_dir = os.path.join(cache_dir, "dispatch")
    if not os.path.isdir(dispatch_dir):
        return False
    return any(
        d.startswith("DEEP-DIVE-") and os.path.isdir(os.path.join(dispatch_dir, d))
        for d in os.listdir(dispatch_dir)
    )


def _write_deep_dive_dispatch(state, cache_dir, skill_dir):
    """Write dispatch for deep dive agents (one per flagged finding)."""
    dispatch_dir = os.path.join(cache_dir, "dispatch")
    deep_dive_dirs = sorted(
        d for d in os.listdir(dispatch_dir)
        if d.startswith("DEEP-DIVE-") and os.path.isdir(os.path.join(dispatch_dir, d))
    )

    agents = []
    for dd_dir_name in deep_dive_dirs:
        dd_path = os.path.join(dispatch_dir, dd_dir_name)
        agents.append({
            "id": dd_dir_name,
            "subagent_type": "review-specialist",
            "dispatch_path": dd_path,
        })

    write_dispatch_v3(cache_dir, "red-team-deep-dive", 1, agents, parallel=True)
    entry = {
        "phase": "red-team-deep-dive",
        "iteration": 1,
        "agents": [a["id"] for a in agents],
        "timestamp": _now(),
    }
    state.dispatch_history.append(entry)


# -- Findings collection --

def _iter_from_fname(fname: str) -> str:
    m = re.search(r"iter(\d+)", fname)
    return m.group(1) if m else "?"


def _collect_findings_summary(state, cache_dir, anonymize: bool = False) -> str:
    outputs_dir = os.path.join(cache_dir, "outputs")
    if not os.path.isdir(outputs_dir):
        return ""

    tracked_files = []
    for entry in state.dispatch_history:
        phase = entry.get("phase", "")
        iteration = entry.get("iteration", 1)
        for agent_id in entry.get("agents", []):
            if agent_id == "REPORT":
                continue
            tracked_files.append((phase, iteration, _agent_filename(agent_id, phase, iteration)))

    def _sort_key(item):
        phase, iteration, _ = item
        phase_order = 1 if phase == PHASE_CHALLENGE_ROUND else 0
        return (phase_order, iteration)

    tracked_files.sort(key=_sort_key, reverse=True)
    seen = set()
    ordered_fnames = []
    for _, _, fname in tracked_files:
        if fname not in seen:
            seen.add(fname)
            ordered_fnames.append(fname)

    _anon_map: dict[str, str] = {}

    def _anon_label(prefix: str) -> str:
        if prefix not in _anon_map:
            _anon_map[prefix] = chr(ord("A") + (len(_anon_map) % 26))
        return f"Reviewer {_anon_map[prefix]}"

    parts = []
    total_size = 0
    for fname in ordered_fnames:
        fpath = os.path.join(outputs_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            content = Path(fpath).read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if state.delimiters:
            begin = content.find(state.delimiters.begin)
            end = content.find(state.delimiters.end)
            if begin >= 0 and end > begin:
                content = content[begin + len(state.delimiters.begin):end].strip()
        if total_size + len(content) > _MAX_FINDINGS_SIZE:
            trunc_msg = "### [TRUNCATED] Remaining findings omitted (size limit)"
            if total_size + len(trunc_msg) <= _MAX_FINDINGS_SIZE:
                parts.append(trunc_msg)
            break

        if anonymize:
            prefix = fname.split("-")[0]
            iteration = _iter_from_fname(fname)
            section = f"### {_anon_label(prefix)}, Iteration {iteration}\n{content}"
            # CORR-007: Use regex to replace agent prefixes only when NOT
            # followed by a dash-and-digits pattern (which indicates a finding ID
            # like SEC-001). This prevents corrupting finding IDs.
            for agent_cfg in state.config.agents:
                # Replace "PREFIX-" only when NOT followed by digits (finding IDs)
                section = re.sub(
                    re.escape(agent_cfg.prefix) + r'-(?!\d)',
                    _anon_label(agent_cfg.prefix) + '-',
                    section,
                )
                # Replace "PREFIX " (prefix followed by space)
                section = re.sub(
                    re.escape(agent_cfg.prefix) + r'(?=\s)',
                    _anon_label(agent_cfg.prefix),
                    section,
                )
        else:
            section = f"### {fname}\n{content}"

        join_overhead = 2 if parts else 0
        if total_size + len(section) + join_overhead > _MAX_FINDINGS_SIZE:
            trunc_msg = "### [TRUNCATED] Remaining findings omitted (size limit)"
            if total_size + len(trunc_msg) + join_overhead <= _MAX_FINDINGS_SIZE:
                parts.append(trunc_msg)
            break
        parts.append(section)
        total_size += len(section) + join_overhead
    return "\n\n".join(parts)


# -- Compliance --

def _get_expected_outputs(state, cache_dir) -> tuple[list[str], str, int]:
    last_dispatch = state.dispatch_history[-1] if state.dispatch_history else {}
    phase = last_dispatch.get(
        "phase", state.current_state.phase_name
    )
    iteration = last_dispatch.get("iteration", _current_phase_iteration(state))

    if state.current_state == State.REPORT:
        return (
            [os.path.join(cache_dir, "outputs", "REPORT.md")],
            phase,
            iteration,
        )

    output_files = []
    agent_ids = last_dispatch.get("agents") or [a.prefix for a in state.config.agents]
    for agent_id in agent_ids:
        fname = _agent_filename(agent_id, phase, iteration)
        output_files.append(os.path.join(cache_dir, "outputs", fname))
    return output_files, phase, iteration


def _validate_outputs(state, output_files) -> tuple[bool, str, str]:
    exist_result = check_outputs_exist(output_files)
    if not exist_result.passed:
        return False, "missing_output", exist_result.error
    return True, "", ""


def _validate_delimiters(state, output_files) -> tuple[bool, str, str]:
    if not state.delimiters:
        return True, "", ""
    known_prefixes = [a.prefix for a in state.config.agents] if state.config else []
    for f in output_files:
        delim_result = check_delimiters(f, state.delimiters)
        if not delim_result.passed:
            prefix = _extract_agent_prefix(os.path.basename(f), known_prefixes)
            return False, delim_result.error, prefix
    return True, "", ""


def _handle_delimiter_retry(state, cache_dir, phase, iteration, failed_agent) -> None:
    state.active_retry = ActiveRetry(
        phase=phase, iteration=iteration, attempt=1,
        failed_agent=failed_agent,
    )
    save_state(state, cache_dir)

    targets = [a for a in state.config.agents if a.prefix == failed_agent]
    if not targets:
        targets = list(state.config.agents)
    retry_agents = []
    for agent_cfg in targets:
        fname = _agent_filename(agent_cfg.prefix, phase, iteration)
        retry_agents.append(DispatchAgent(
            id=agent_cfg.prefix,
            description=f"{agent_cfg.prefix}: Retry (delimiter missing)",
            prompt_file=os.path.join(cache_dir, "prompts", fname),
            output_file=os.path.join(cache_dir, "outputs", fname),
        ))

    agent_configs = {a.prefix: a for a in state.config.agents}
    write_dispatch(cache_dir, phase, iteration, retry_agents, retry=True,
                   agent_configs=agent_configs)
    print(json.dumps({
        "error": "retry_delimiter",
        "message": f"RETRY: Agent {failed_agent} output missing delimiters. "
                   "Re-dispatch required.",
        "recoverable": True,
    }), file=sys.stderr)
    raise RetryDispatchError(
        f"Agent {failed_agent} output missing delimiters. Re-dispatch required."
    )


def _run_compliance_checks(state, cache_dir):
    output_files, phase, iteration = _get_expected_outputs(state, cache_dir)

    passed, error_type, error_msg = _validate_outputs(state, output_files)
    if not passed:
        state.relay_compliance_violations += 1
        abort(state, cache_dir, error_type, error_msg)

    relevant_basenames = set()
    if state.current_state == State.REPORT:
        relevant_basenames.add("REPORT.md")
    else:
        fallback_prefixes = [a.prefix for a in state.config.agents]
        agent_ids = (state.dispatch_history[-1].get("agents", fallback_prefixes)
                     if state.dispatch_history else fallback_prefixes)
        for agent_id in agent_ids:
            relevant_basenames.add(_agent_filename(agent_id, phase, iteration))

    prompt_map = {}
    for basename, expected_hash in state.prompt_hashes.items():
        if basename not in relevant_basenames:
            continue
        prompt_path = os.path.join(cache_dir, "prompts", basename)
        if os.path.exists(prompt_path):
            prompt_map[prompt_path] = expected_hash
    hash_result = check_prompt_hashes(prompt_map)
    if not hash_result.passed:
        state.relay_compliance_violations += 1
        abort(state, cache_dir, "prompt_tampered", hash_result.error)

    delim_ok, delim_err, failed_agent = _validate_delimiters(state, output_files)
    if not delim_ok:
        state.relay_compliance_violations += 1
        if state.active_retry:
            abort(state, cache_dir, "compliance_failed",
                  f"Delimiter check failed after retry: {delim_err}")
        else:
            _handle_delimiter_retry(state, cache_dir, phase, iteration, failed_agent)

    size_result = check_output_sizes(output_files)
    state.relay_compliance_warnings += size_result.warnings
    for detail in size_result.warning_details:
        log_guardrail(state, "compliance", "output_size", "", "warning", detail)

    state.relay_compliance_rounds += 1
    state.active_retry = None


# -- Budget helpers --

def _discover_new_files(state, cache_dir) -> list[tuple[str, str]]:
    new_files = []
    d = os.path.join(cache_dir, "outputs")
    if not os.path.isdir(d):
        return new_files
    for f in os.listdir(d):
        fp = os.path.join(d, f)
        rel = os.path.join("outputs", f)
        if os.path.isfile(fp) and not os.path.islink(fp) and rel not in state.completed_outputs:
            new_files.append((fp, rel))
    return new_files


def _measure_budget(state, cache_dir, skill_dir):
    if state.config.flags.get("no_budget") or state.config.budget_limit == 0:
        return

    new_files = _discover_new_files(state, cache_dir)

    total_bytes = 0
    for fp, rel in new_files:
        total_bytes += os.path.getsize(fp)
        state.completed_outputs.add(rel)

    if total_bytes > 0:
        try:
            result = budget.add_consumption(total_bytes, cache_dir, skill_dir)
            state.budget_consumed = result.get("consumed", state.budget_consumed)
            state.budget_remaining = result.get("remaining", state.budget_remaining)
        except ScriptError as e:
            log_guardrail(
                state, "budget", "add_consumption", "",
                "error", f"Budget tracking failed: {e}",
            )

    phase_name = state.current_state.phase_name
    iteration = _current_phase_iteration(state)
    state.round_history.append({
        "phase": phase_name,
        "iteration": iteration,
        "bytes": total_bytes,
    })


def _check_agent_convergence(state, cache_dir, skill_dir) -> bool:
    if not state.config.agents:
        return False

    agent_prefixes = [a.prefix for a in state.config.agents]

    def check_one(agent_id):
        curr = os.path.join(
            cache_dir, "outputs",
            _agent_filename(agent_id, PHASE_SELF_REFINEMENT, state.iteration),
        )
        prev = os.path.join(
            cache_dir, "outputs",
            _agent_filename(agent_id, PHASE_SELF_REFINEMENT, state.iteration - 1),
        )
        if not (os.path.exists(curr) and os.path.exists(prev)):
            return agent_id, False, None
        try:
            converged, _ = convergence.check_convergence(curr, prev, skill_dir)
            return agent_id, converged, None
        except Exception as e:
            return agent_id, False, str(e)

    results = [check_one(aid) for aid in agent_prefixes]

    all_converged = True
    check_errors = 0
    for agent_id, converged, error in results:
        if error:
            check_errors += 1
            log_guardrail(
                state, "convergence", "check_convergence",
                agent_id, "error", f"Convergence check failed: {error}",
            )
        state.convergence.setdefault(agent_id, {})[
            f"iteration_{state.iteration}"] = converged
        if not converged:
            all_converged = False
    if check_errors == len(results) and len(results) > 0:
        log_guardrail(
            state, "convergence", "all_checks_failed", "",
            "warning", f"All {check_errors} convergence checks failed, "
            "non-convergence may be due to check failures rather than actual divergence",
        )
    return all_converged


# -- Utility --

def _extract_agent_prefix(basename: str, known_prefixes: list[str]) -> str:
    name = os.path.splitext(basename)[0]
    for prefix in sorted(known_prefixes, key=len, reverse=True):
        if name.startswith(prefix + "-"):
            return prefix
    return name.split("-")[0] if "-" in name else name


def _now():
    return datetime.now(timezone.utc).isoformat()


def _run_legacy_script(script_name: str, args: list[str],
                       cache_dir: str, skill_dir: str) -> tuple[int, str, str]:
    """Run a legacy script from {skill_dir}/scripts/{script_name}.

    Returns (returncode, stdout, stderr). Uses the safe env from subprocess_utils.
    For .py scripts, runs with python3; for .sh scripts, runs with bash.
    """
    script_path = os.path.join(skill_dir, "scripts", script_name)
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")
    env_extra = {"CACHE_DIR": cache_dir, "SKILL_DIR": skill_dir}
    try:
        if script_name.endswith(".py"):
            result = _subprocess_run_python(script_path, args, env_extra=env_extra,
                                            timeout=60)
        else:
            result = _subprocess_run_script(script_path, args, env_extra=env_extra,
                                            timeout=60)
        return (0, json.dumps(result) if result else "", "")
    except ScriptError as e:
        return (1, "", str(e))


def _run_post_self_refinement_scripts(state, cache_dir, skill_dir):
    """Run populate-findings and severity-check after self-refinement outputs."""
    iteration = state.iteration
    outputs_dir = os.path.join(cache_dir, "outputs")
    profile = state.config.profile if state.config else "code"

    for agent_cfg in state.config.agents:
        fname = _agent_filename(agent_cfg.prefix, PHASE_SELF_REFINEMENT, iteration)
        fpath = os.path.join(outputs_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            cache_mod.populate_findings(
                agent=agent_cfg.prefix,
                role_prefix=agent_cfg.prefix,
                findings_file=fpath,
                cache_dir=cache_dir,
                skill_dir=skill_dir,
                profile=profile,
            )
        except Exception as e:
            log_guardrail(state, "post_self_refinement", "populate_findings",
                          agent_cfg.prefix, "warning",
                          f"populate_findings failed for {agent_cfg.prefix}: {e}")

    try:
        rc, stdout, stderr = _run_legacy_script(
            "severity-check.py", [outputs_dir], cache_dir, skill_dir,
        )
        if rc != 0:
            log_guardrail(state, "post_self_refinement", "severity_check",
                          "", "warning",
                          f"severity-check.py failed: {stderr}")
    except FileNotFoundError:
        log_guardrail(state, "post_self_refinement", "severity_check",
                      "", "info", "severity-check.py not found, skipping")
    except Exception as e:
        log_guardrail(state, "post_self_refinement", "severity_check",
                      "", "warning", f"severity-check.py error: {e}")


def _run_pre_challenge_scripts(state, cache_dir, skill_dir):
    """Run dedup, build-summary, and generate-navigation before challenge round."""
    outputs_dir = os.path.join(cache_dir, "outputs")
    profile = state.config.profile if state.config else "code"

    try:
        rc, stdout, stderr = _run_legacy_script(
            "deduplicate.sh", [outputs_dir], cache_dir, skill_dir,
        )
        if rc != 0:
            log_guardrail(state, "pre_challenge", "deduplicate",
                          "", "warning", f"deduplicate.sh failed: {stderr}")
    except FileNotFoundError:
        log_guardrail(state, "pre_challenge", "deduplicate",
                      "", "info", "deduplicate.sh not found, skipping")
    except Exception as e:
        log_guardrail(state, "pre_challenge", "deduplicate",
                      "", "warning", f"deduplicate.sh error: {e}")

    try:
        cache_mod.build_summary(cache_dir, skill_dir, profile)
    except Exception as e:
        log_guardrail(state, "pre_challenge", "build_summary",
                      "", "warning", f"build_summary failed: {e}")

    try:
        cache_mod.generate_navigation(
            cache_dir, skill_dir, profile,
            iteration=1, phase=2,
        )
    except Exception as e:
        log_guardrail(state, "pre_challenge", "generate_navigation",
                      "", "warning", f"generate_navigation for phase 2 failed: {e}")


_STATE_HANDLERS = {
    State.SELF_REFINEMENT: _process_self_refinement,
    State.CONVERGENCE_CHECK: _process_convergence_check,
    State.CHALLENGE_ROUND: _process_challenge_round,
    State.CHALLENGE_CHECK: _process_challenge_check,
    State.RESOLUTION: _process_resolution,
    State.RED_TEAM_AUDIT: _process_red_team_audit,
    State.RED_TEAM_CHECK: _process_red_team_check,
    State.RED_TEAM_DEEP_DIVE: _process_red_team_deep_dive,
    State.REPORT: _process_report,
}
