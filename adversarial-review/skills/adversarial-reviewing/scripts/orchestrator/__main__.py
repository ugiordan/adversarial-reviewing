"""FSM orchestrator for adversarial-reviewing skill.

CLI entry point. Subcommands:
  init $ARGUMENTS     - Parse flags, init cache, write first dispatch.json
  next --cache-dir D  - Read outputs, advance FSM, write next dispatch.json
  confirm --cache-dir D - User confirmed scope, advance to SELF_REFINEMENT
  resume --cache-dir D  - Resume from crash, write next dispatch.json

Output contract: init and resume write JSON to stdout (cache_dir, delimiters).
next and confirm communicate via dispatch.json in the cache directory.
All subcommands write JSON error objects to stderr on failure.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from . import cache
from . import budget as budget_mod
from .config import parse_args as parse_skill_args, resolve_config
from .dispatch import write_scope_confirmation, write_terminal
from .fsm import (
    process_state, resume_dispatch_state, transition, abort,
    log_guardrail, write_agent_dispatch,
)
from .state import save_state, load_state
from .subprocess_utils import fatal_error, ALLOWED_ENV_KEYS
from .types import State, FsmState, Delimiters, SAFE_ID_RE, PHASE_SELF_REFINEMENT, RetryDispatchError


def main():
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description="FSM orchestrator for adversarial-reviewing skill",
    )
    parser.add_argument(
        "command", choices=["init", "next", "confirm", "resume"],
        help="Subcommand to run",
    )
    args, remaining = parser.parse_known_args()

    skill_dir = _validated_skill_dir()

    {"init": handle_init,
     "next": handle_next,
     "confirm": handle_confirm,
     "resume": handle_resume,
     }[args.command](remaining, skill_dir)


def handle_init(argv: list[str], skill_dir: str):
    args = parse_skill_args(argv)
    config = resolve_config(args, skill_dir)

    session_hex = secrets.token_hex(16)

    cache_result = cache.init_cache(session_hex, skill_dir, config.profile)
    cache_dir = cache_result["cache_dir"]

    _ensure_cache_directories(cache_dir)

    from . import telemetry
    telemetry.init_tracer("adversarial-review", cache_dir)

    delimiters = _generate_delimiters(skill_dir, cache_dir)

    if config.budget_limit > 0:
        budget_mod.init_budget(config.budget_limit, cache_dir, skill_dir)

    state = FsmState(
        current_state=State.PARSE_FLAGS,
        config=config,
        delimiters=delimiters,
        budget_remaining=config.budget_limit,
    )

    transition(state, State.RESOLVE_SCOPE)
    transition(state, State.CONFIRM_SCOPE)

    sanitized_target = " ".join(args.target.split())
    scope_msg = os.path.join(cache_dir, "scope-confirmation.md")
    Path(scope_msg).write_text(
        f"## Scope Confirmation\n\n"
        f"Profile: {config.profile}\n"
        f"Agents: {', '.join(a.prefix for a in config.agents)}\n"
        f"Budget: {config.budget_limit}\n"
        f"Max iterations: {config.max_iterations}\n"
        f"Target: {sanitized_target}\n\n"
        f"Proceed with review?"
    )

    save_state(state, cache_dir)
    write_scope_confirmation(cache_dir, scope_msg)

    print(json.dumps({
        "cache_dir": cache_dir,
        "delimiters": {
            "begin": delimiters.begin,
            "end": delimiters.end,
        },
    }))


def handle_confirm(argv: list[str], skill_dir: str):
    p = argparse.ArgumentParser()
    p.add_argument("--cache-dir", required=True)
    args = p.parse_args(argv)
    cache_dir = _validated_cache_dir(args.cache_dir)

    state = load_state(cache_dir)
    if state.current_state != State.CONFIRM_SCOPE:
        fatal_error(f"Cannot confirm from state {state.current_state.value}")

    if state.delimiters is None:
        fatal_error("State missing delimiters. Re-run orchestrator init.")

    try:
        transition(state, State.INIT_CACHE)

        cache.populate_templates(cache_dir, skill_dir, state.config.profile)
        cache.populate_references(cache_dir, skill_dir, state.config.profile)

        ctx_flags = state.config.flags.get("context", [])
        for ctx in ctx_flags:
            if "=" not in ctx:
                log_guardrail(
                    state, "input", "context_parse", "",
                    "warning", f"Context entry missing '=' separator, skipped: {ctx}",
                )
                continue
            label, source = ctx.split("=", 1)
            if not label or not source:
                log_guardrail(
                    state, "input", "context_parse", "",
                    "warning", f"Context entry has empty label or source: {ctx}",
                )
                continue
            if not SAFE_ID_RE.match(label):
                log_guardrail(
                    state, "input", "context_parse", "",
                    "warning", f"Context label contains invalid characters: {label}",
                )
                continue
            if "://" in source:
                log_guardrail(
                    state, "input", "context_traversal", "",
                    "warning", f"Context source contains URL scheme, skipped: {source}",
                )
                continue
            # SEC-002: Reject shell metacharacters in context source paths
            _shell_meta = set(";|&$`\\!()")
            if any(ch in _shell_meta for ch in source):
                log_guardrail(
                    state, "input", "context_source_validation", "",
                    "warning", f"Context source contains shell metacharacters, skipped: {source}",
                )
                continue
            if state.config.source_root:
                resolved_source = os.path.realpath(source)
                root = os.path.realpath(state.config.source_root)
                if not resolved_source.startswith(root + os.sep) and resolved_source != root:
                    log_guardrail(
                        state, "input", "context_traversal", "",
                        "warning", f"Context source outside source root, skipped: {source}",
                    )
                    continue
            cache.populate_context(
                cache_dir, skill_dir, state.config.profile, label, source
            )

        if state.config.flags.get("constraints"):
            cache.populate_constraints(
                cache_dir, skill_dir, state.config.profile,
                state.config.flags["constraints"],
            )

        # Generate scope file and populate code before navigation
        source_root = state.config.source_root or os.getcwd()
        if os.path.isdir(source_root):
            scope_file = os.path.join(cache_dir, "scope-files.txt")
            _generate_scope_file(
                source_root, scope_file,
                force=bool(state.config.flags.get("force")),
            )
            if os.path.exists(scope_file) and os.path.getsize(scope_file) > 0:
                cache.populate_code(
                    scope_file, state.delimiters.hex, cache_dir,
                    skill_dir, state.config.profile,
                )

            cache.generate_navigation(
                cache_dir, skill_dir, state.config.profile,
                iteration=1, phase=1,
            )

        _ensure_cache_directories(cache_dir)

        transition(state, State.POPULATE_CACHE)
        transition(state, State.SELF_REFINEMENT)

        write_agent_dispatch(state, cache_dir, skill_dir, PHASE_SELF_REFINEMENT)
        save_state(state, cache_dir)
    except Exception as e:
        abort(state, cache_dir, "populate_failed", f"Cache population failed: {e}")


def handle_next(argv: list[str], skill_dir: str):
    p = argparse.ArgumentParser()
    p.add_argument("--cache-dir", required=True)
    args = p.parse_args(argv)
    cache_dir = _validated_cache_dir(args.cache_dir)

    state = load_state(cache_dir)

    from . import telemetry
    telemetry.init_tracer("adversarial-review", cache_dir)
    try:
        process_state(state, cache_dir, skill_dir)
    except RetryDispatchError:
        sys.exit(1)
    telemetry.flush()


def handle_resume(argv: list[str], skill_dir: str):
    p = argparse.ArgumentParser()
    p.add_argument("--cache-dir", required=True)
    args = p.parse_args(argv)
    cache_dir = _validated_cache_dir(args.cache_dir)

    state = load_state(cache_dir)

    from . import telemetry
    telemetry.init_tracer("adversarial-review", cache_dir)

    if state.current_state == State.ABORTED:
        fatal_error("Cannot resume from ABORTED state. Start a fresh run.")

    if state.current_state == State.DONE:
        report_path = os.path.join(cache_dir, "outputs", "REPORT.md")
        write_terminal(cache_dir, report_path, "Already complete.")
    elif state.current_state.is_dispatch_state:
        resume_dispatch_state(state, cache_dir, skill_dir)
    else:
        process_state(state, cache_dir, skill_dir)

    telemetry.flush()

    print(json.dumps({
        "cache_dir": cache_dir,
        "delimiters": {
            "begin": state.delimiters.begin,
            "end": state.delimiters.end,
        } if state.delimiters else {},
    }))


# -- Utility --

def _validated_skill_dir() -> str:
    skill_dir = os.environ.get("CLAUDE_SKILL_DIR", _find_skill_dir())
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        fatal_error(f"Invalid skill directory (SKILL.md not found): {skill_dir}")
    return skill_dir


def _validated_cache_dir(cache_dir: str) -> str:
    state_file = os.path.join(cache_dir, "fsm-state.json")
    if not os.path.isdir(cache_dir) or not os.path.isfile(state_file):
        fatal_error(
            f"Invalid cache directory: {cache_dir} "
            "(directory must exist and contain fsm-state.json)"
        )
    return cache_dir


def _generate_delimiters(skill_dir: str, cache_dir: str) -> Delimiters:
    import subprocess
    script = os.path.join(skill_dir, "scripts", "generate-delimiters.sh")
    scope_file = os.path.join(cache_dir, "scope-confirmation.md")
    Path(scope_file).touch()

    env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}
    try:
        result = subprocess.run(
            ["bash", script, scope_file],
            capture_output=True, text=True, env=env, timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return Delimiters(
                begin=data["start_delimiter"],
                end=data["end_delimiter"],
                hex=data["hex"],
            )
    except Exception as e:
        print(json.dumps({
            "warning": "delimiter_fallback",
            "message": f"generate-delimiters.sh failed ({e}), using fallback",
        }), file=sys.stderr)

    hex_val = secrets.token_hex(16)
    return Delimiters(
        begin=f"===REVIEW_TARGET_{hex_val}_START===",
        end=f"===REVIEW_TARGET_{hex_val}_END===",
        hex=hex_val,
    )


def _ensure_cache_directories(cache_dir: str) -> None:
    for subdir in ("prompts", "outputs", "reasoning", "compaction"):
        os.makedirs(os.path.join(cache_dir, subdir), exist_ok=True)


MAX_SCOPE_FILES = 10_000


def _generate_scope_file(source_root: str, output_path: str,
                         force: bool = False) -> None:
    """Walk source_root and write file paths (one per line) to output_path.

    Excludes common non-source directories and generated/test files.
    Truncates to MAX_SCOPE_FILES unless force=True.
    """
    skip_dirs = {
        "vendor", "node_modules", ".git", "__pycache__",
        "testdata", "bin",
    }
    skip_suffixes = ("_test.go", "zz_generated")
    lines = []
    for root, dirs, fnames in os.walk(source_root):
        dirs[:] = sorted(d for d in dirs if d not in skip_dirs)
        for fname in sorted(fnames):
            if any(fname.endswith(s) for s in skip_suffixes):
                continue
            full = os.path.join(root, fname)
            if os.path.islink(full):
                continue
            lines.append(full)
            if not force and len(lines) >= MAX_SCOPE_FILES:
                print(json.dumps({
                    "warning": "scope_truncated",
                    "message": f"Scope file truncated at {MAX_SCOPE_FILES} files. "
                               "Use --force to bypass.",
                }), file=sys.stderr)
                break
        else:
            continue
        break
    Path(output_path).write_text("\n".join(lines) + "\n" if lines else "")


def _find_skill_dir():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, "SKILL.md")):
            return d
        d = os.path.dirname(d)
    fatal_error(
        f"SKILL.md not found in any parent directory starting from "
        f"{os.path.dirname(os.path.abspath(__file__))}"
    )


if __name__ == "__main__":
    main()
