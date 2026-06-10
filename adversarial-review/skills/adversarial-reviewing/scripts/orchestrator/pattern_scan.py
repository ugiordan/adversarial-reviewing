"""Extract detection patterns from agent instructions and pre-scan source code.

Parses backtick-quoted code patterns from the '## Detection Patterns' section
of agent instruction files. Runs grep against the source tree to produce
deterministic hit lists. Generates structured checklists for dispatch dirs.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)

_SECTION_RE = re.compile(r"^##\s+Detection Patterns", re.MULTILINE)
_NEXT_SECTION_RE = re.compile(r"^##\s+", re.MULTILINE)
_CATEGORY_RE = re.compile(r"^\*\*(.+?)[:]*\*\*", re.MULTILINE)
_BACKTICK_RE = re.compile(r"`([^`]{3,})`")

_SKIP_DIRS = {
    "vendor", "testdata", "zz_generated", ".git", "node_modules", "__pycache__",
    "gopath-loader", ".gopath-loader", ".cache", ".adversarial-review-cache",
    "bin", ".idea",
}
_SKIP_SUFFIXES = ("_test.go", "_test.py", ".test.ts", ".test.js", ".spec.ts")

_MAX_HITS_PER_PATTERN = 10

_LANG_EXTENSIONS = {
    "go": ["*.go", "*.yaml", "*.yml"],
    "python": ["*.py", "*.yaml", "*.yml"],
    "typescript": ["*.ts", "*.tsx", "*.yaml", "*.yml"],
    "default": ["*.go", "*.py", "*.ts", "*.yaml", "*.yml", "*.json"],
}

_TOO_BROAD = {
    "[0]", "[1]", "ok", "nil", "err", "Get", "List", "true", "false",
    "name", "key", "value", "type", "auto", "update", "Handle",
    "Random", "Generate", "secrets", "escalate", "bind", "MinVersion",
}


@dataclass
class PatternDef:
    id: str
    category: str
    grep_pattern: str
    description: str


@dataclass
class PatternHit:
    file: str
    line: int
    content: str


@dataclass
class ScanResult:
    pattern: PatternDef
    hits: list[PatternHit] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "hits_found" if self.hits else "no_hits"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:40]


def extract_patterns(agent_instructions: str, agent_prefix: str) -> list[PatternDef]:
    """Parse detection patterns from agent-instructions.md.

    Finds the '## Detection Patterns' section, extracts backtick-quoted code
    snippets grouped by bold category headers.
    """
    m = _SECTION_RE.search(agent_instructions)
    if not m:
        return []

    section_start = m.end()
    rest = agent_instructions[section_start:]
    m2 = _NEXT_SECTION_RE.search(rest)
    section_text = rest[:m2.start()] if m2 else rest

    patterns: list[PatternDef] = []
    current_category = "general"
    category_counters: dict[str, int] = {}

    for line in section_text.split("\n"):
        cat_match = _CATEGORY_RE.match(line.strip())
        if cat_match:
            current_category = cat_match.group(1).strip().rstrip(":")

        for code_match in _BACKTICK_RE.finditer(line):
            code = code_match.group(1).strip()
            if code in _TOO_BROAD:
                continue
            if " " in code and len(code) > 80:
                continue

            cat_slug = _slugify(current_category)
            category_counters[cat_slug] = category_counters.get(cat_slug, 0) + 1
            pattern_id = f"{cat_slug}_{category_counters[cat_slug]}"

            description_line = line.strip()
            if description_line.startswith("-"):
                description_line = description_line[1:].strip()
            description_line = re.sub(r"`[^`]+`", "", description_line).strip()
            if len(description_line) > 120:
                description_line = description_line[:120] + "..."

            patterns.append(PatternDef(
                id=pattern_id,
                category=current_category,
                grep_pattern=code,
                description=description_line or current_category,
            ))

    return patterns


def _should_skip(filepath: str) -> bool:
    parts = filepath.split(os.sep)
    for d in _SKIP_DIRS:
        if d in parts:
            return True
    for suffix in _SKIP_SUFFIXES:
        if filepath.endswith(suffix):
            return True
    if "pkg/mod/" in filepath:
        return True
    return False


def run_prescan(
    source_root: str,
    patterns: list[PatternDef],
    language: str = "default",
) -> list[ScanResult]:
    """Run grep for each pattern against source_root.

    Returns a ScanResult per pattern with file:line hits.
    """
    extensions = _LANG_EXTENSIONS.get(language, _LANG_EXTENSIONS["default"])
    results: list[ScanResult] = []

    for pattern_def in patterns:
        hits = _grep_pattern(source_root, pattern_def.grep_pattern, extensions)
        results.append(ScanResult(pattern=pattern_def, hits=hits))

    return results


def _grep_pattern(
    source_root: str,
    pattern: str,
    extensions: list[str],
) -> list[PatternHit]:
    cmd = ["grep", "-rn", "--fixed-strings"]
    for ext in extensions:
        cmd.extend(["--include", ext])
    for skip in ("vendor", "testdata", "node_modules",
                  "gopath-loader", ".gopath-loader",
                  ".git", "bin", ".cache", ".idea"):
        cmd.extend(["--exclude-dir", skip])
    cmd.append(pattern)
    cmd.append(".")

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=source_root, timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning("grep failed for pattern %r: %s", pattern, e)
        return []

    hits: list[PatternHit] = []
    for line in proc.stdout.splitlines():
        if not line:
            continue
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        filepath = parts[0].lstrip("./")
        if _should_skip(filepath):
            continue
        try:
            lineno = int(parts[1])
        except ValueError:
            continue
        content = parts[2].strip()
        if len(content) > 200:
            content = content[:200] + "..."
        hits.append(PatternHit(file=filepath, line=lineno, content=content))
        if len(hits) >= _MAX_HITS_PER_PATTERN:
            break

    return hits


def generate_checklist(scan_results: list[ScanResult], agent_prefix: str) -> dict:
    """Generate a structured checklist YAML dict from scan results."""
    patterns_list = []
    for result in scan_results:
        entry = {
            "id": result.pattern.id,
            "category": result.pattern.category,
            "description": result.pattern.description,
            "grep": result.pattern.grep_pattern,
            "status": result.status,
            "hits": [
                {"file": h.file, "line": h.line, "content": h.content}
                for h in result.hits
            ],
        }
        patterns_list.append(entry)
    return {"agent": agent_prefix, "patterns": patterns_list}


def format_pattern_hits_md(
    scan_results: list[ScanResult],
    source_root: str = "",
) -> str:
    """Format scan results as markdown for inclusion in dispatch directory.

    When source_root is provided, includes 3 lines of context around each
    hit so the agent has evidence without needing to Read the file.
    """
    hits_found = [r for r in scan_results if r.hits]
    if not hits_found:
        return ""

    lines = [
        "## Pre-Scan Pattern Hits\n",
        "These patterns from your Detection Patterns section matched in the source code.",
        "You MUST investigate each hit and either:",
        "1. Produce a finding (using the finding template), or",
        "2. Explain why it is not an issue (in your Coverage Report under \"checked, not an issue\")\n",
    ]

    for result in hits_found:
        lines.append(f"### {result.pattern.id}: {result.pattern.grep_pattern}")
        lines.append(f"Category: {result.pattern.category}")
        lines.append(f"Description: {result.pattern.description}\n")
        for hit in result.hits:
            lines.append(f"- {hit.file}:{hit.line}: `{hit.content}`")
            if source_root:
                context = _read_context(source_root, hit.file, hit.line, 3)
                if context:
                    lines.append(f"  ```")
                    lines.append(context)
                    lines.append(f"  ```")
        lines.append("")

    return "\n".join(lines)


def _read_context(source_root: str, filepath: str, line: int, radius: int) -> str:
    """Read a few lines around a hit for inline evidence."""
    fpath = os.path.join(source_root, filepath)
    if not os.path.isfile(fpath):
        return ""
    try:
        with open(fpath, errors="replace") as f:
            all_lines = f.readlines()
        start = max(0, line - radius - 1)
        end = min(len(all_lines), line + radius)
        context_lines = []
        for i in range(start, end):
            marker = ">>>" if i == line - 1 else "   "
            context_lines.append(f"  {marker} {i+1}: {all_lines[i].rstrip()}")
        return "\n".join(context_lines)
    except OSError:
        return ""


def run_full_prescan(
    source_root: str,
    profile_dir: str,
    agents: list,
    language: str = "default",
) -> dict:
    """Run pre-scan for all agents. Returns {agent_prefix: list[ScanResult]}.

    The `agents` parameter expects objects with `.prefix` and `.file` attributes.
    Agent instructions are loaded from profile_dir/agents/{file}.
    """
    all_results: dict[str, list[ScanResult]] = {}

    for agent_cfg in agents:
        agent_file = agent_cfg.file or ""
        if not agent_file:
            continue
        instructions_path = os.path.join(profile_dir, "agents", agent_file)
        if not os.path.isfile(instructions_path):
            logger.warning("Agent instructions not found: %s", instructions_path)
            continue

        with open(instructions_path) as f:
            instructions = f.read()

        patterns = extract_patterns(instructions, agent_cfg.prefix)
        if not patterns:
            logger.info("No detection patterns found for %s", agent_cfg.prefix)
            continue

        scan_results = run_prescan(source_root, patterns, language)
        all_results[agent_cfg.prefix] = scan_results

    return all_results


def save_prescan(results: dict, cache_dir: str) -> str:
    """Save pre-scan results to cache_dir/pattern-scan.yaml.

    Serializes ScanResult objects to YAML-friendly dicts.
    Returns the path to the saved file.
    """
    output_path = os.path.join(cache_dir, "pattern-scan.yaml")
    serialized = {}
    for prefix, scan_results in results.items():
        serialized[prefix] = generate_checklist(scan_results, prefix)

    with open(output_path, "w") as f:
        yaml.safe_dump(serialized, f, default_flow_style=False, sort_keys=False)

    return output_path


def load_prescan(cache_dir: str) -> dict | None:
    """Load pre-scan results from cache_dir/pattern-scan.yaml."""
    path = os.path.join(cache_dir, "pattern-scan.yaml")
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            loaded = yaml.safe_load(f)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}
