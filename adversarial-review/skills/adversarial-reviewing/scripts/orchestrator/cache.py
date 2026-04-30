import os
from .subprocess_utils import run_python_script, ScriptError

CacheError = ScriptError


def init_cache(session_hex: str, skill_dir: str, profile: str) -> dict:
    return _run_manage_cache(
        ["init", session_hex],
        skill_dir=skill_dir,
        env_extra={"REVIEW_PROFILE": profile, "SOURCE_ROOT": os.getcwd()},
    )


def populate_code(file_list_path: str, delimiter_hex: str, cache_dir: str,
                  skill_dir: str, profile: str) -> dict:
    return _run_manage_cache(
        ["populate-code", file_list_path, delimiter_hex],
        skill_dir=skill_dir,
        env_extra={"CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile},
    )


def populate_templates(cache_dir: str, skill_dir: str, profile: str) -> dict:
    return _run_manage_cache(
        ["populate-templates"],
        skill_dir=skill_dir,
        env_extra={"CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile},
    )


def populate_references(cache_dir: str, skill_dir: str, profile: str) -> dict:
    return _run_manage_cache(
        ["populate-references"],
        skill_dir=skill_dir,
        env_extra={"CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile},
    )


def populate_context(cache_dir: str, skill_dir: str, profile: str,
                     label: str, source: str) -> dict:
    return _run_manage_cache(
        ["populate-context"],
        skill_dir=skill_dir,
        env_extra={
            "CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile,
            "CONTEXT_LABEL": label, "CONTEXT_SOURCE": source,
        },
    )


def populate_constraints(cache_dir: str, skill_dir: str, profile: str,
                         source: str) -> dict:
    return _run_manage_cache(
        ["populate-constraints"],
        skill_dir=skill_dir,
        env_extra={
            "CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile,
            "CONSTRAINTS_SOURCE": source,
        },
    )


def generate_navigation(cache_dir: str, skill_dir: str, profile: str,
                        iteration: int = 1, phase: int = 1) -> dict:
    return _run_manage_cache(
        ["generate-navigation", str(iteration), str(phase)],
        skill_dir=skill_dir,
        env_extra={"CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile},
    )


def populate_findings(agent: str, role_prefix: str, findings_file: str,
                      cache_dir: str, skill_dir: str, profile: str,
                      scope_file: str = "") -> dict:
    """Validate, sanitize, and split agent findings via manage_cache.py."""
    args = ["populate-findings", agent, role_prefix, findings_file]
    if scope_file:
        args.extend(["--scope", scope_file])
    return _run_manage_cache(args, skill_dir=skill_dir,
                             env_extra={"CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile})


def build_summary(cache_dir: str, skill_dir: str, profile: str) -> dict:
    """Build cross-agent finding summary for challenge round."""
    return _run_manage_cache(["build-summary"], skill_dir=skill_dir,
                             env_extra={"CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile})


def validate_cache(cache_dir: str, skill_dir: str, profile: str) -> dict:
    """Validate cache integrity."""
    return _run_manage_cache(["validate-cache", cache_dir], skill_dir=skill_dir,
                             env_extra={"CACHE_DIR": cache_dir, "REVIEW_PROFILE": profile})


def _run_manage_cache(args: list[str], skill_dir: str,
                      env_extra: dict = None) -> dict:
    script = os.path.join(skill_dir, "scripts", "manage_cache.py")
    return run_python_script(script, args, env_extra=env_extra, timeout=60)
