from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import NoReturn

ALLOWED_ENV_KEYS = {"HOME", "PATH", "TMPDIR", "LANG", "SHELL", "USER", "LOGNAME"}
ALLOWED_ENV_EXTRA_KEYS = {
    "CACHE_DIR", "REVIEW_PROFILE", "CONTEXT_LABEL", "CONTEXT_SOURCE",
    "CONSTRAINTS_SOURCE", "SESSION_HEX", "SKILL_DIR", "BUDGET_LIMIT",
    "SOURCE_ROOT", "REVIEW_CACHE_DIR", "REVIEW_AGENT_ID", "REVIEW_PHASE",
    "REVIEW_ITERATION", "REVIEW_TARGET",
}

_MAX_OUTPUT_BYTES = 2 * 1024 * 1024


class ScriptError(Exception):
    pass


def _run_subprocess(command: list[str], env_extra: dict = None,
                    timeout: int = 30) -> dict:
    env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}
    if env_extra:
        blocked = set(env_extra.keys()) - ALLOWED_ENV_EXTRA_KEYS
        if blocked:
            raise ScriptError(f"Blocked environment variables: {blocked}")
        env.update(env_extra)
    script_name = os.path.basename(command[1]) if len(command) > 1 else command[0]
    try:
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        )
        stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise ScriptError(f"{script_name} timed out")
    if len(stdout_bytes) > _MAX_OUTPUT_BYTES:
        raise ScriptError(
            f"{script_name} output exceeded {_MAX_OUTPUT_BYTES} bytes "
            f"({len(stdout_bytes)} bytes)"
        )
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        # SEC-007: Truncate stderr to avoid leaking internal details in error messages
        truncated_stderr = stderr.strip()[:500]
        raise ScriptError(
            f"{script_name} failed (exit {proc.returncode}): {truncated_stderr}"
        )
    if not stdout.strip():
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        raise ScriptError(
            f"{script_name} returned non-JSON output: {stdout[:200]}"
        )


def run_script(script_path: str, args: list[str] = None,
               env_extra: dict = None, timeout: int = 30) -> dict:
    return _run_subprocess(
        ["bash", script_path] + (args or []),
        env_extra=env_extra, timeout=timeout,
    )


def run_python_script(script_path: str, args: list[str] = None,
                      env_extra: dict = None, timeout: int = 60) -> dict:
    return _run_subprocess(
        ["python3", script_path] + (args or []),
        env_extra=env_extra, timeout=timeout,
    )


def fatal_error(message: str, recoverable: bool = False) -> NoReturn:
    print(json.dumps({
        "error": "fsm_error",
        "message": message,
        "recoverable": recoverable,
    }), file=sys.stderr)
    sys.exit(1)
