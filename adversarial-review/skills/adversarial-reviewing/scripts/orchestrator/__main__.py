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
    raw_args = sys.argv[1:]
    commands = {"init", "next", "confirm", "resume", "run-all"}
    command = None
    remaining = []
    for i, arg in enumerate(raw_args):
        if arg in commands and command is None:
            command = arg
            remaining = raw_args[:i] + raw_args[i + 1:]
            break
    if command is None:
        if "--cache-dir" in raw_args:
            command = "next"
            remaining = raw_args
        else:
            print("usage: orchestrator {init,next,confirm,resume} [options]",
                  file=sys.stderr)
            sys.exit(2)

    skill_dir = _validated_skill_dir()

    {"init": handle_init,
     "next": handle_next,
     "confirm": handle_confirm,
     "resume": handle_resume,
     "run-all": handle_run_all,
     }[command](remaining, skill_dir)


def handle_init(argv: list[str], skill_dir: str):
    args = parse_skill_args(argv)
    config = resolve_config(args, skill_dir)

    session_hex = secrets.token_hex(16)

    cache_result = cache.init_cache(
        session_hex, skill_dir, config.profile,
        source_root=config.source_root,
    )
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
        f"NEXT STEP: Run the orchestrator confirm command to approve this "
        f"scope and start the review. The confirm command may take several "
        f"minutes for large repos. Wait for it to complete."
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

        binding_labels: set[str] = set()
        for flag_key in ("context", "binding_context"):
            ctx_flags = state.config.flags.get(flag_key, [])
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
                if flag_key == "binding_context":
                    binding_labels.add(label)
        state.binding_context_labels = binding_labels

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
                    source_root=source_root,
                )

            cache.generate_navigation(
                cache_dir, skill_dir, state.config.profile,
                iteration=1, phase=1,
            )

        _ensure_cache_directories(cache_dir)

        _run_external_analyzers(source_root, cache_dir)

        from .config import detect_language
        detected = detect_language(source_root)
        if detected:
            state.config.detected_language = detected
            _try_install_lsp(detected, skill_dir)

        _run_pattern_prescan(
            source_root, cache_dir, skill_dir,
            state.config.profile, state.config.agents,
            detected or "default",
        )

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


_LSP_INSTALL_COMMANDS = {
    "go": (["go", "install", "golang.org/x/tools/gopls@v0.18.1"], "gopls", ["~/go/bin"]),
    "python": (["pip", "install", "--quiet", "pyright==1.1.400"], "pyright", []),
    "typescript": (["npm", "install", "-g", "--silent", "typescript-language-server@4.3.3", "typescript@5.7.3"], "typescript-language-server", []),
    "rust": (["rustup", "component", "add", "rust-analyzer"], "rust-analyzer", ["~/.cargo/bin"]),
}


def _try_install_lsp(language: str, skill_dir: str) -> None:
    """Try to install the LSP binary for the detected language."""
    import shutil
    import subprocess as _sp

    spec = _LSP_INSTALL_COMMANDS.get(language)
    if not spec:
        return
    install_cmd, binary_name, extra_paths = spec

    if shutil.which(binary_name):
        return
    for p in extra_paths:
        candidate = os.path.join(os.path.expanduser(p), binary_name)
        if os.path.isfile(candidate):
            return

    if not shutil.which(install_cmd[0]):
        return

    try:
        _sp.run(install_cmd, capture_output=True, timeout=60)
    except Exception:
        pass


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


def _is_binary(path: str, chunk_size: int = 8192) -> bool:
    """Check if a file contains binary content by reading the first chunk."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(chunk_size)
        return b"\x00" in chunk
    except (OSError, IOError):
        return True


def _run_external_analyzers(source_root: str, cache_dir: str) -> None:
    """Run cymbal index and arch-analyzer if available. Best-effort, non-fatal."""
    import shutil
    import subprocess as _sp

    cymbal_bin = shutil.which("cymbal")
    if cymbal_bin:
        try:
            _sp.run(
                [cymbal_bin, "index", source_root],
                capture_output=True, timeout=30, cwd=source_root,
            )
        except (OSError, _sp.TimeoutExpired):
            pass

    arch_bin = shutil.which("arch-analyzer")
    if not arch_bin:
        candidate = os.path.expanduser(
            "~/workdir/rhoai/architecture-analyzer/arch-analyzer"
        )
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            arch_bin = candidate

    if arch_bin:
        arch_dir = os.path.join(cache_dir, "architecture")
        os.makedirs(arch_dir, exist_ok=True)
        try:
            _sp.run(
                [arch_bin, "analyze", "-output-dir", arch_dir, source_root],
                capture_output=True, timeout=120, cwd=source_root,
            )
        except (OSError, _sp.TimeoutExpired):
            pass
        try:
            _sp.run(
                [arch_bin, "full-analysis", "-output-dir", arch_dir,
                 "-domains", "security", source_root],
                capture_output=True, timeout=120, cwd=source_root,
            )
        except (OSError, _sp.TimeoutExpired):
            pass


def _run_pattern_prescan(
    source_root: str,
    cache_dir: str,
    skill_dir: str,
    profile: str,
    agents: list,
    language: str = "default",
) -> None:
    """Run detection pattern pre-scan against source tree. Best-effort, non-fatal."""
    try:
        from .pattern_scan import run_full_prescan, save_prescan
        profile_dir = os.path.join(skill_dir, "profiles", profile)
        results = run_full_prescan(source_root, profile_dir, agents, language)
        if results:
            save_prescan(results, cache_dir)
    except Exception:
        pass


def _generate_scope_file(source_root: str, output_path: str,
                         force: bool = False) -> None:
    """Walk source_root and write file paths (one per line) to output_path.

    Excludes common non-source directories and generated/test files.
    Truncates to MAX_SCOPE_FILES unless force=True.
    """
    skip_dirs = {
        "vendor", "node_modules", ".git", "__pycache__",
        "testdata", "bin", ".idea", ".vscode", "output",
        ".adversarial-review-cache", ".cache", "artifacts",
        "gopath-loader", ".gopath-loader",
    }
    skip_suffixes = ("_test.go", "zz_generated", ".patch")
    binary_exts = {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp", ".webp",
        ".woff", ".woff2", ".ttf", ".eot",
        ".zip", ".tar", ".gz", ".bz2", ".xz",
        ".exe", ".dll", ".so", ".dylib", ".o", ".a",
        ".pyc", ".pyo", ".class",
        ".db", ".sqlite", ".sqlite3",
        ".DS_Store",
    }
    lines = []
    for root, dirs, fnames in os.walk(source_root):
        dirs[:] = sorted(d for d in dirs if d not in skip_dirs)
        for fname in sorted(fnames):
            if any(fname.endswith(s) for s in skip_suffixes):
                continue
            if fname.startswith("."):
                continue
            _, ext = os.path.splitext(fname)
            if ext.lower() in binary_exts:
                continue
            full = os.path.join(root, fname)
            if os.path.islink(full):
                continue
            if _is_binary(full):
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size > 500_000:
                continue
            lines.append(full)
            if not force and len(lines) >= MAX_SCOPE_FILES:
                print(json.dumps({
                    "warning": "scope_truncated",
                    "message": f"Scope file truncated at {MAX_SCOPE_FILES} files (this is normal for large repos).",
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


def handle_run_all(argv: list[str], skill_dir: str):
    """Run the full orchestrator pipeline without a relay.

    Calls init, confirm, then loops: read dispatch.json, dispatch agents
    via claude CLI, run next. Stops when dispatch.json has done=true.
    """
    import io
    import logging
    from .runner import dispatch_agents, read_dispatch, is_done

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger("run-all")

    model = "claude-opus-4-6"
    light_model = None
    remaining = []
    i = 0
    while i < len(argv):
        if argv[i] == "--model" and i + 1 < len(argv):
            model = argv[i + 1]
            i += 2
        elif argv[i] == "--light-model" and i + 1 < len(argv):
            light_model = argv[i + 1]
            i += 2
        else:
            remaining.append(argv[i])
            i += 1

    if light_model:
        log.info("Models: primary=%s, light=%s (iter2-3, report)", model, light_model)
    else:
        log.info("Model: %s (all phases)", model)
    log.info("Phase: init")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        handle_init(remaining, skill_dir)
        init_output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    cache_dir = ""
    for line in init_output.strip().split("\n"):
        try:
            data = json.loads(line)
            if "cache_dir" in data:
                cache_dir = data["cache_dir"]
                break
        except (json.JSONDecodeError, ValueError):
            continue

    if not cache_dir:
        cache_base = os.path.join(skill_dir, ".adversarial-review-cache")
        if os.path.isdir(cache_base):
            for d in sorted(
                os.listdir(cache_base),
                key=lambda x: os.path.getmtime(os.path.join(cache_base, x)),
                reverse=True,
            ):
                full = os.path.join(cache_base, d)
                if os.path.isdir(full) and os.path.isfile(
                    os.path.join(full, "fsm-state.json")
                ):
                    cache_dir = full
                    break

    if not cache_dir:
        fatal_error("Could not determine cache_dir after init")

    log.info("Cache dir: %s", cache_dir)
    log.info("Phase: confirm")
    handle_confirm(["--cache-dir", cache_dir], skill_dir)

    max_rounds = 20
    for round_num in range(max_rounds):
        dispatch = read_dispatch(cache_dir)
        if not dispatch:
            log.error("No dispatch.json found")
            break
        if is_done(dispatch):
            log.info("Review complete (round %d)", round_num)
            artifacts_dir = os.path.join(skill_dir, "artifacts")
            if os.path.isdir(artifacts_dir):
                log.info("Artifacts: %s", ", ".join(os.listdir(artifacts_dir)))
            print(json.dumps({
                "status": "done",
                "cache_dir": cache_dir,
                "rounds": round_num,
            }))
            return

        phase = dispatch.get("phase", "?")
        iteration = dispatch.get("iteration", "?")
        agents = dispatch.get("agents", [])
        log.info(
            "Round %d: phase=%s iter=%s agents=%s",
            round_num, phase, iteration,
            [a["id"] for a in agents],
        )

        results = dispatch_agents(dispatch, skill_dir, model=model, light_model=light_model)
        for agent_id, rc in results.items():
            status = "OK" if rc == 0 else f"FAIL(exit={rc})"
            log.info("  %s: %s", agent_id, status)

        log.info("Phase: next")
        handle_next(["--cache-dir", cache_dir], skill_dir)

    log.error("Max rounds (%d) exceeded", max_rounds)
    sys.exit(1)


if __name__ == "__main__":
    main()
