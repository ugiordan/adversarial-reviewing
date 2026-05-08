"""Pre-computed hotspot scanner for adversarial-reviewing agents.

Runs specialist-specific grep patterns against the source root before
dispatching agents. Results are included as hotspots.md in each agent's
dispatch directory so agents prioritize files with known patterns.
"""
from __future__ import annotations

import os
import subprocess
from collections import defaultdict
from pathlib import Path

_SKIP_DIRS = ["vendor", "node_modules", ".git", "__pycache__", "testdata", "bin", ".idea"]
_SOURCE_INCLUDES = [
    "--include=*.go", "--include=*.py", "--include=*.ts", "--include=*.js",
    "--include=*.rs", "--include=*.java", "--include=*.yaml", "--include=*.yml",
    "--include=*.json", "--include=*.toml", "--include=*.sh", "--include=*.tmpl",
    "--include=Dockerfile", "--include=Makefile",
]
_MAX_PER_PATTERN = 50
_MAX_TOTAL = 400


def load_hotspot_patterns(profile_dir: str) -> dict[str, list[dict]]:
    """Load hotspot-patterns.yaml for a profile.

    Returns {agent_prefix: [{pattern, description}, ...]} or empty dict.
    """
    path = os.path.join(profile_dir, "hotspot-patterns.yaml")
    if not os.path.isfile(path):
        return {}
    try:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, list)}
    except ImportError:
        return _parse_patterns_fallback(path)
    except Exception:
        return {}


def _parse_patterns_fallback(path: str) -> dict[str, list[dict]]:
    """Parse hotspot patterns YAML without PyYAML."""
    result: dict[str, list[dict]] = {}
    current_agent = ""
    current_entry: dict = {}

    for line in Path(path).read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            if current_entry and current_agent:
                result.setdefault(current_agent, []).append(current_entry)
                current_entry = {}
            current_agent = stripped[:-1]
            continue
        if stripped.startswith("- pattern:"):
            if current_entry and current_agent:
                result.setdefault(current_agent, []).append(current_entry)
            val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            current_entry = {"pattern": val}
        elif stripped.startswith("description:"):
            val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            current_entry["description"] = val

    if current_entry and current_agent:
        result.setdefault(current_agent, []).append(current_entry)
    return result


def compute_hotspots(
    source_root: str,
    agent_prefix: str,
    patterns: list[dict],
    max_per_pattern: int = _MAX_PER_PATTERN,
) -> str:
    """Run grep for each pattern against source_root.

    Returns a markdown string with results organized by pattern.
    """
    if not patterns or not os.path.isdir(source_root):
        return ""

    exclude_args = [f"--exclude-dir={d}" for d in _SKIP_DIRS]
    all_results: list[tuple[str, str, list[tuple[str, int, str]]]] = []
    file_hits: dict[str, int] = defaultdict(int)
    total_hits = 0

    for entry in patterns:
        pattern = entry.get("pattern", "")
        description = entry.get("description", "")
        if not pattern:
            continue

        hits = _grep_pattern(source_root, pattern, exclude_args, max_per_pattern)
        if hits:
            all_results.append((pattern, description, hits))
            for fpath, _, _ in hits:
                file_hits[fpath] += 1
            total_hits += len(hits)

        if total_hits >= _MAX_TOTAL:
            break

    if not all_results:
        return ""

    return _format_hotspots(agent_prefix, all_results, file_hits, source_root)


def _grep_pattern(
    source_root: str,
    pattern: str,
    exclude_args: list[str],
    max_results: int,
) -> list[tuple[str, int, str]]:
    """Run grep for a single pattern. Returns [(file, line_num, match_text)]."""
    cmd = ["grep", "-rn"] + _SOURCE_INCLUDES + exclude_args + [pattern, source_root]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3,
        )
        if result.returncode not in (0, 1):
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return _grep_python_fallback(source_root, pattern, max_results)

    hits = []
    for line in result.stdout.splitlines()[:max_results]:
        parts = line.split(":", 2)
        if len(parts) >= 3:
            fpath = parts[0]
            try:
                line_num = int(parts[1])
            except ValueError:
                continue
            match_text = parts[2].strip()[:200]
            if not fpath.startswith(source_root):
                continue
            hits.append((fpath, line_num, match_text))
    return hits


def _grep_python_fallback(
    source_root: str,
    pattern: str,
    max_results: int,
) -> list[tuple[str, int, str]]:
    """Pure Python grep fallback when grep binary is unavailable."""
    import re
    hits = []
    skip = set(_SKIP_DIRS)
    try:
        regex = re.compile(pattern)
    except re.error:
        regex = re.compile(re.escape(pattern))

    for root, dirs, files in os.walk(source_root):
        dirs[:] = [d for d in dirs if d not in skip]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            hits.append((fpath, i, line.strip()[:200]))
                            if len(hits) >= max_results:
                                return hits
            except (OSError, UnicodeDecodeError):
                continue
    return hits


def _format_hotspots(
    agent_prefix: str,
    results: list[tuple[str, str, list[tuple[str, int, str]]]],
    file_hits: dict[str, int],
    source_root: str,
) -> str:
    """Format hotspot results as markdown."""
    parts = [
        f"## Hotspot Analysis for {agent_prefix}\n",
        "Pre-computed grep results for patterns relevant to your specialty.",
        "**Read this first.** Files with multiple hits are highest priority.",
        "These results are a starting sample. If a pattern shows 'more matches',",
        "grep for it yourself to find ALL occurrences.\n",
    ]

    top_files = sorted(file_hits.items(), key=lambda x: x[1], reverse=True)[:20]
    if top_files:
        parts.append("### Priority files (by hit count)")
        parts.append("| File | Hits |")
        parts.append("|------|------|")
        for fpath, count in top_files:
            rel = os.path.relpath(fpath, source_root)
            parts.append(f"| `{rel}` | {count} |")
        parts.append("")

    for pattern, description, hits in results:
        parts.append(f"### Pattern: `{pattern}`")
        if description:
            parts.append(f"> {description}")
        for fpath, line_num, match_text in hits[:25]:
            rel = os.path.relpath(fpath, source_root)
            parts.append(f"- `{rel}:{line_num}`: {match_text}")
        if len(hits) > 25:
            parts.append(f"- ... and {len(hits) - 25} more matches (grep this pattern yourself)")
        parts.append("")

    return "\n".join(parts)
