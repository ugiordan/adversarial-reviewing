from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path
from .types import FsmConfig, AgentConfig, SAFE_ID_RE, ALLOWED_AGENT_TOOLS, VALID_EFFORT_LEVELS
from .subprocess_utils import fatal_error

try:
    import yaml as _yaml
except ImportError:
    _yaml = None

DEFAULT_BUDGET = 350_000
QUICK_BUDGET = 150_000
THOROUGH_BUDGET = 800_000
QUICK_MAX_ITER = 2
THOROUGH_MAX_ITER = 5

# Maps CLI specialist flags to agent prefix codes.
SPECIALIST_FLAG_MAP = {
    "security": "SEC",
    "performance": "PERF",
    "quality": "QUAL",
    "correctness": "CORR",
    "architecture": "ARCH",
    "feasibility": "FEAS",
    "user_impact": "USER",
    "scope": "SCOP",
    "testability": "TEST",
}

# Specialist flags that only apply to strat/rfe profiles.
_STRAT_RFE_SPECIALISTS = {"feasibility", "user_impact", "scope", "testability"}
# Specialist flags that only apply to code profiles.
_CODE_SPECIALISTS = {"security", "performance", "quality", "correctness", "architecture"}


def parse_args(argv: list[str] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FSM orchestrator for adversarial-reviewing")
    p.add_argument("target", help="Review target (file, directory, or URL)")
    p.add_argument("--profile", default="code", help="Review profile")

    # Mode flags (mutually exclusive): --quick or --thorough
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Quick review with reduced specialists")
    mode.add_argument("--thorough", action="store_true", help="Thorough review with all specialists and higher budget")

    # Specialist flags (independent, combinable)
    specialists = p.add_argument_group("specialist selection")
    specialists.add_argument("--security", action="store_true", help="Include security specialist")
    specialists.add_argument("--performance", action="store_true", help="Include performance specialist")
    specialists.add_argument("--quality", action="store_true", help="Include quality specialist")
    specialists.add_argument("--correctness", action="store_true", help="Include correctness specialist")
    specialists.add_argument("--architecture", action="store_true", help="Include architecture specialist")
    specialists.add_argument("--feasibility", action="store_true", help="Include feasibility specialist (strat/rfe)")
    specialists.add_argument("--user-impact", action="store_true", help="Include user-impact specialist (strat/rfe)")
    specialists.add_argument("--scope", action="store_true", help="Include scope specialist (strat/rfe)")
    specialists.add_argument("--testability", action="store_true", help="Include testability specialist (strat/rfe)")

    # Operational flags
    p.add_argument("--budget", type=int, default=None, help="Override token budget")
    p.add_argument("--force", action="store_true", help="Bypass 200-file limit")
    p.add_argument("--strict-scope", action="store_true", help="Strict scope enforcement")
    p.add_argument("--topic", type=str, default="", help="Override topic name")
    p.add_argument("--dry-run", action="store_true", help="Preview remediation without applying")
    p.add_argument("--converge", action="store_true", help="Post-fix delta loop")
    p.add_argument("--range", type=str, default="", help="Git commit range for --diff")
    p.add_argument("--triage", type=str, default="", help="Source for external review triage")
    p.add_argument("--gap-analysis", action="store_true", help="Run gap analysis")
    p.add_argument("--list-references", action="store_true", help="List reference documents")
    p.add_argument("--update-references", action="store_true", help="Update reference documents")
    p.add_argument("--review-only", action="store_true", help="Skip pipeline for strat/rfe")
    p.add_argument("--confirm", action="store_true", help="Show refined doc before proceeding")
    p.add_argument("--arch-context", type=str, default="", help="Architecture context repo@ref (strat/rfe only)")

    # Existing flags
    p.add_argument("--context", action="append", default=[], metavar="LABEL=SOURCE")
    p.add_argument("--constraints", default="")
    p.add_argument("--principles", default="")
    p.add_argument("--no-budget", action="store_true")
    p.add_argument("--delta", action="store_true")
    p.add_argument("--diff", action="store_true")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--save", action="store_true")
    p.add_argument("--keep-cache", action="store_true")
    p.add_argument("--reuse-cache", default="")
    p.add_argument("--normalize", action="store_true")
    p.add_argument("--persist", action="store_true")

    args = p.parse_args(argv)
    _validate_flag_compatibility(args)
    return args


def _validate_flag_compatibility(args: argparse.Namespace) -> None:
    """Validate that flag combinations are compatible."""
    if args.delta and args.reuse_cache:
        fatal_error("--delta and --reuse-cache are incompatible. Delta requires fresh analysis.")

    if args.no_budget and args.budget is not None:
        fatal_error("--no-budget and --budget are incompatible. Use one or the other.")

    if args.converge and not args.fix:
        fatal_error("--converge requires --fix. Convergence loop only runs after remediation.")

    if args.dry_run and not args.fix:
        fatal_error("--dry-run requires --fix. Dry-run previews remediation changes.")

    if args.fix and args.profile in ("strat", "rfe"):
        fatal_error(f"--fix is not supported with the '{args.profile}' profile. Remediation is code-only.")

    if args.review_only and args.confirm:
        fatal_error("--review-only and --confirm are incompatible.")

    if args.arch_context and args.profile == "code":
        fatal_error("--arch-context is only supported with strat/rfe profiles.")

    if args.principles and args.profile == "code":
        fatal_error("--principles is only supported with strat/rfe profiles.")


def read_profile_config(profile_dir: str) -> dict:
    config_path = os.path.join(profile_dir, "config.yml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config.yml not found at {config_path}")
    content = Path(config_path).read_text()
    if _yaml is None:
        raise ImportError(
            "PyYAML is required for profile config parsing. "
            "Install with: pip install pyyaml"
        )
    try:
        return _yaml.safe_load(content)
    except _yaml.YAMLError as e:
        raise ValueError(
            f"config.yml at {config_path} has invalid YAML: {e}"
        ) from e


def resolve_config(args: argparse.Namespace, skill_dir: str) -> FsmConfig:
    if not SAFE_ID_RE.match(args.profile):
        fatal_error(
            f"Profile name '{args.profile}' contains invalid characters. "
            "Only alphanumeric, hyphens, and underscores are allowed."
        )

    profile_dir = os.path.join(skill_dir, "profiles", args.profile)
    profile_cfg = read_profile_config(profile_dir)
    defaults = _load_defaults(profile_dir)
    all_agents = []
    for a in profile_cfg["agents"]:
        tools = a.get("tools", ["Read"])
        if isinstance(tools, str):
            tools = [tools]
        for t in tools:
            if t not in ALLOWED_AGENT_TOOLS:
                fatal_error(f"Invalid tool '{t}' for agent {a['prefix']}. Allowed: {ALLOWED_AGENT_TOOLS}")
        effort = a.get("effort", "medium")
        if effort not in VALID_EFFORT_LEVELS:
            fatal_error(f"Invalid effort '{effort}' for agent {a['prefix']}. Allowed: {VALID_EFFORT_LEVELS}")
        max_turns = a.get("maxTurns", 15)
        if isinstance(max_turns, str):
            try:
                max_turns = int(max_turns)
            except ValueError:
                fatal_error(f"maxTurns must be an integer for agent {a['prefix']}: {max_turns}")
        if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns < 1 or max_turns > 50:
            fatal_error(f"maxTurns out of range for agent {a['prefix']}: {max_turns}")
        all_agents.append(AgentConfig(
            prefix=a["prefix"], file=a.get("file", ""),
            tools=tools, effort=effort, max_turns=max_turns,
        ))

    # Determine which specialist flags the user set
    active_specialist_flags = [
        flag_name for flag_name in SPECIALIST_FLAG_MAP
        if getattr(args, flag_name, False)
    ]

    # Determine agent selection and iteration/budget settings
    if active_specialist_flags:
        # Specialist flags override: filter to only matching agents
        wanted_prefixes = {SPECIALIST_FLAG_MAP[f] for f in active_specialist_flags}
        agents = [a for a in all_agents if a.prefix in wanted_prefixes]

        if args.quick:
            max_iter = QUICK_MAX_ITER
            budget = QUICK_BUDGET
        elif args.thorough:
            max_iter = THOROUGH_MAX_ITER
            budget = THOROUGH_BUDGET
        else:
            max_iter = defaults.get("max_iterations", 3)
            budget = defaults.get("budget", DEFAULT_BUDGET)
    elif args.quick:
        quick_prefixes = set(
            profile_cfg.get("quick_specialists", [a.prefix for a in all_agents[:2]])
        )
        agents = [a for a in all_agents if a.prefix in quick_prefixes]
        max_iter = QUICK_MAX_ITER
        budget = QUICK_BUDGET
    elif args.thorough:
        agents = all_agents
        max_iter = THOROUGH_MAX_ITER
        budget = THOROUGH_BUDGET
    else:
        agents = all_agents
        max_iter = defaults.get("max_iterations", 3)
        budget = defaults.get("budget", DEFAULT_BUDGET)

    # --budget overrides computed budget
    if args.budget is not None:
        budget = args.budget

    if args.no_budget:
        budget = 0

    # Declarative flag collection: bool flags are set when True,
    # string/list flags are set when non-empty.
    BOOL_FLAGS = [
        "save", "delta", "diff", "normalize", "persist", "no_budget",
        "keep_cache", "fix", "force", "strict_scope", "dry_run", "converge",
        "gap_analysis", "list_references", "update_references", "review_only",
        "confirm",
    ]
    STRING_FLAGS = [
        "reuse_cache", "constraints", "principles", "range", "triage",
        "arch_context",
    ]

    flags = {}
    for flag_name in BOOL_FLAGS:
        if getattr(args, flag_name, False):
            flags[flag_name] = True
    for flag_name in STRING_FLAGS:
        val = getattr(args, flag_name, "")
        if val:
            flags[flag_name] = val
    if args.context:
        flags["context"] = args.context

    if not agents:
        fatal_error(
            f"Profile '{args.profile}' resolved to 0 agents. "
            "Check config.yml or specialist flags."
        )

    return FsmConfig(
        profile=args.profile,
        agents=agents,
        budget_limit=budget,
        max_iterations=max_iter,
        min_iterations=min(2, max_iter),
        flags=flags,
        target=args.target,
        source_root=os.path.realpath(args.target) if os.path.isdir(args.target) else os.getcwd(),
        specialist_flags=active_specialist_flags,
        topic=args.topic,
    )


def _load_defaults(profile_dir: str) -> dict:
    path = os.path.join(profile_dir, "defaults.json")
    if not os.path.exists(path):
        return {"max_iterations": 3, "budget": DEFAULT_BUDGET}
    try:
        return json.loads(Path(path).read_text())
    except (json.JSONDecodeError, KeyError):
        return {"max_iterations": 3, "budget": DEFAULT_BUDGET}


def _parse_config_yml(content: str) -> dict:
    """Minimal YAML parser for profile config.yml files.

    .. deprecated::
        Kept for backward compatibility. Use PyYAML (``read_profile_config``) instead.

    Known limitations: no block scalars, anchors, or flow mappings.
    """
    warnings.warn(
        "_parse_config_yml is deprecated. Install PyYAML and use read_profile_config instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    data = {}
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(line) - len(stripped)

        if indent == 0 and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if val:
                if val in ("true", "false"):
                    data[key] = val == "true"
                elif val == "all":
                    data[key] = "all"
                elif val.startswith("[") and val.endswith("]"):
                    items = [x.strip().strip("'\"") for x in val[1:-1].split(",")]
                    data[key] = [x for x in items if x]
                else:
                    data[key] = _unquote(val)
            else:
                i += 1
                items = []

                while i < len(lines):
                    sub = lines[i]
                    sub_stripped = sub.lstrip()
                    sub_indent = len(sub) - len(sub_stripped)

                    if not sub_stripped or (sub_stripped and sub_indent <= indent):
                        if sub_stripped and sub_indent <= indent:
                            break
                        i += 1
                        continue

                    if sub_stripped.startswith("- "):
                        rest = sub_stripped[2:].strip()

                        if ":" in rest:
                            item = {}
                            k2, _, v2 = rest.partition(":")
                            item[k2.strip()] = _parse_scalar(v2.strip())
                            i += 1

                            while i < len(lines):
                                inner = lines[i]
                                inner_s = inner.lstrip()
                                inner_ind = len(inner) - len(inner_s)

                                if not inner_s:
                                    i += 1
                                    continue
                                if inner_ind <= sub_indent:
                                    break

                                if ":" in inner_s and not inner_s.startswith("-"):
                                    k3, _, v3 = inner_s.partition(":")
                                    item[k3.strip()] = _parse_scalar(v3.strip())

                                i += 1

                            items.append(item)
                        else:
                            items.append(_unquote(rest))
                            i += 1
                    elif ":" in sub_stripped:
                        nested = {}
                        while i < len(lines):
                            nsub = lines[i]
                            nsub_s = nsub.lstrip()
                            nsub_ind = len(nsub) - len(nsub_s)
                            if not nsub_s:
                                i += 1
                                continue
                            if nsub_ind <= indent:
                                break
                            if ":" in nsub_s:
                                nk, _, nv = nsub_s.partition(":")
                                nested[nk.strip()] = _unquote(nv.strip())
                            i += 1
                        data[key] = nested
                        continue
                    else:
                        i += 1

                if items:
                    data[key] = items
                elif key not in data:
                    data[key] = []
                continue

        i += 1

    return data


def _parse_scalar(val: str):
    """Parse a YAML scalar value: inline lists, booleans, or plain strings."""
    if val.startswith("[") and val.endswith("]"):
        items = [x.strip().strip("'\"") for x in val[1:-1].split(",")]
        return [x for x in items if x]
    if val in ("true", "false"):
        return val == "true"
    return _unquote(val)


def _unquote(val: str) -> str:
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val
