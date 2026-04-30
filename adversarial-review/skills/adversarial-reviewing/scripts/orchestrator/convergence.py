import os
from .subprocess_utils import run_script, ScriptError

ConvergenceError = ScriptError


def check_convergence(current_file: str, previous_file: str,
                      skill_dir: str) -> tuple[bool, dict]:
    script = os.path.join(skill_dir, "scripts", "detect-convergence.sh")
    try:
        data = run_script(script, [current_file, previous_file], timeout=30)
        return data.get("converged", True), data
    except ScriptError:
        return False, {"converged": False}
