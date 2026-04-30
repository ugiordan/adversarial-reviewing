import os
from .subprocess_utils import run_script, ScriptError

BudgetError = ScriptError


def init_budget(limit: int, cache_dir: str, skill_dir: str = "") -> dict:
    return _run_track_budget(["init", str(limit)], cache_dir, skill_dir)


def add_consumption(size_bytes: int, cache_dir: str, skill_dir: str = "") -> dict:
    return _run_track_budget(["add", str(size_bytes)], cache_dir, skill_dir)


def estimate(num_agents: int, code_tokens: int, iterations: int,
             cache_dir: str, skill_dir: str = "") -> dict:
    return _run_track_budget(
        ["estimate", str(num_agents), str(code_tokens), str(iterations)],
        cache_dir, skill_dir,
    )


def get_status(cache_dir: str, skill_dir: str = "") -> dict:
    return _run_track_budget(["status"], cache_dir, skill_dir)


def _run_track_budget(args: list[str], cache_dir: str,
                      skill_dir: str = "") -> dict:
    if not skill_dir:
        skill_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    script = os.path.join(skill_dir, "scripts", "track-budget.sh")
    return run_script(script, args, env_extra={"CACHE_DIR": cache_dir}, timeout=30)
