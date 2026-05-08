"""Codebase knowledge index for adversarial-reviewing agents.

Builds a compact symbol index (function/type/variable definitions with
file:line locations) using regex-based extraction. Optionally uses ctags
when available for broader language coverage.

The index IS valid evidence: it's from static analysis, not LLM inference.
Agents can cite index entries directly. When the index doesn't cover what
an agent needs, the agent falls back to Read/Grep on source files.
"""
from __future__ import annotations

import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

_SKIP_DIRS = {
    "vendor", "node_modules", ".git", "__pycache__", "testdata",
    "bin", ".idea", ".vscode", "output", ".cache",
}

_SKIP_SUFFIXES = ("_test.go", "_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js")

_MAX_INDEX_CHARS = 80_000

_SYMBOL_PATTERNS = {
    ".go": [
        (re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)"), "func"),
        (re.compile(r"^type\s+(\w+)\s+(struct|interface)"), "type"),
        (re.compile(r"^var\s+(\w+)\s+"), "var"),
        (re.compile(r"^const\s+(\w+)\s+"), "const"),
    ],
    ".py": [
        (re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)"), "def"),
        (re.compile(r"^class\s+(\w+)"), "class"),
    ],
    ".ts": [
        (re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)"), "function"),
        (re.compile(r"^(?:export\s+)?class\s+(\w+)"), "class"),
        (re.compile(r"^(?:export\s+)?interface\s+(\w+)"), "interface"),
        (re.compile(r"^(?:export\s+)?type\s+(\w+)\s*="), "type"),
    ],
    ".js": [
        (re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)"), "function"),
        (re.compile(r"^(?:export\s+)?class\s+(\w+)"), "class"),
    ],
    ".rs": [
        (re.compile(r"^pub(?:\s*\(crate\))?\s+fn\s+(\w+)\s*\(([^)]*)\)"), "fn"),
        (re.compile(r"^fn\s+(\w+)\s*\(([^)]*)\)"), "fn"),
        (re.compile(r"^pub(?:\s*\(crate\))?\s+struct\s+(\w+)"), "struct"),
        (re.compile(r"^pub(?:\s*\(crate\))?\s+enum\s+(\w+)"), "enum"),
        (re.compile(r"^pub(?:\s*\(crate\))?\s+trait\s+(\w+)"), "trait"),
    ],
    ".java": [
        (re.compile(r"(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)?(\w+)\s*\(([^)]*)\)"), "method"),
        (re.compile(r"(?:public|private|protected)\s+class\s+(\w+)"), "class"),
        (re.compile(r"(?:public|private|protected)\s+interface\s+(\w+)"), "interface"),
    ],
}

_SECURITY_KEYWORDS = {
    "auth", "secret", "credential", "password", "token", "webhook",
    "rbac", "permission", "cert", "tls", "crypt", "ssl", "oauth",
    "session", "key", "security", "policy", "role", "validate",
    "sanitize", "admin", "grant", "acl", "gateway", "proxy",
    "hash", "crypto", "registry",
}


def build_code_index(source_root: str, detected_language: str = "") -> str:
    """Build a compact code index from the source tree.

    Uses regex-based symbol extraction (works without external tools).
    Returns markdown with symbol definitions grouped by file.
    """
    if not os.path.isdir(source_root):
        return ""

    symbols_by_file = _extract_symbols(source_root)
    if not symbols_by_file:
        return ""

    security_files, other_files = _split_by_security_relevance(
        symbols_by_file, source_root
    )

    callers = _find_callers_for_security_symbols(
        security_files, source_root
    )

    return _format_index(security_files, other_files, callers, source_root)


def _extract_symbols(
    source_root: str,
) -> dict[str, list[tuple[str, str, int, str]]]:
    """Walk source tree and extract symbol definitions.

    Returns {rel_path: [(name, kind, line_num, signature)]}.
    """
    result: dict[str, list[tuple[str, str, int, str]]] = {}

    for root, dirs, files in os.walk(source_root):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for fname in sorted(files):
            if fname.startswith("."):
                continue
            if any(fname.endswith(s) for s in _SKIP_SUFFIXES):
                continue
            ext = os.path.splitext(fname)[1].lower()
            patterns = _SYMBOL_PATTERNS.get(ext)
            if not patterns:
                continue

            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, source_root)

            try:
                symbols = _extract_from_file(fpath, patterns)
            except (OSError, UnicodeDecodeError):
                continue

            if symbols:
                result[rel] = symbols

    return result


def _extract_from_file(
    fpath: str, patterns: list[tuple[re.Pattern, str]],
) -> list[tuple[str, str, int, str]]:
    """Extract symbol definitions from a single file."""
    if os.path.islink(fpath):
        resolved = os.path.realpath(fpath)
        source_dir = os.path.dirname(os.path.realpath(os.path.dirname(fpath)))
        if not resolved.startswith(source_dir):
            return []
    symbols = []
    try:
        raw = Path(fpath).read_bytes()
        if b"\x00" in raw[:8192]:
            return []
        lines = raw.decode("utf-8", errors="replace").splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        for pattern, kind in patterns:
            m = pattern.match(stripped)
            if m:
                name = m.group(1)
                sig = stripped[:120]
                symbols.append((name, kind, line_num, sig))
                break

    return symbols


def _split_by_security_relevance(
    symbols_by_file: dict[str, list],
    source_root: str,
) -> tuple[dict[str, list], dict[str, list]]:
    """Split files into security-relevant and other."""
    security = {}
    other = {}

    for rel_path, symbols in symbols_by_file.items():
        lower = rel_path.lower()
        is_security = any(kw in lower for kw in _SECURITY_KEYWORDS)
        if is_security:
            security[rel_path] = symbols
        else:
            other[rel_path] = symbols

    return security, other


def _find_callers_for_security_symbols(
    security_files: dict[str, list[tuple[str, str, int, str]]],
    source_root: str,
    max_total_seconds: float = 30.0,
) -> dict[str, list[str]]:
    """For each symbol in security-relevant files, find callers via grep.

    Returns {symbol_name: ["file:line"]}.
    """
    import time
    callers: dict[str, list[str]] = {}
    exclude_args = [f"--exclude-dir={d}" for d in _SKIP_DIRS]
    start_time = time.monotonic()

    symbols_to_search = []
    for _rel, syms in security_files.items():
        for name, kind, _line, _sig in syms:
            if kind in ("func", "def", "function", "fn", "method") and len(name) > 3:
                symbols_to_search.append(name)

    for sym in symbols_to_search[:50]:
        if time.monotonic() - start_time > max_total_seconds:
            break
        search_path = os.path.abspath(source_root)
        cmd = (
            ["grep", "-rn", "--include=*.go", "--include=*.py",
             "--include=*.ts", "--include=*.js", "--include=*.rs",
             "--include=*.java"]
            + exclude_args
            + ["--", f"{sym}(", search_path]
        )
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                hits = []
                for line in result.stdout.splitlines()[:5]:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        rel = os.path.relpath(parts[0], source_root)
                        hits.append(f"{rel}:{parts[1]}")
                if hits:
                    callers[sym] = hits
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    return callers


def _format_index(
    security_files: dict[str, list[tuple[str, str, int, str]]],
    other_files: dict[str, list[tuple[str, str, int, str]]],
    callers: dict[str, list[str]],
    source_root: str,
) -> str:
    """Format the index as compact markdown."""
    parts = [
        "## Code Index (static analysis)\n",
        "Symbol definitions extracted from source. These are real file:line",
        "locations from static analysis. You can cite them as evidence.\n",
    ]

    total_chars = 0

    if security_files:
        parts.append("### Security-relevant files\n")
        for rel_path in sorted(security_files):
            section = _format_file_section(
                rel_path, security_files[rel_path], callers
            )
            if total_chars + len(section) > _MAX_INDEX_CHARS:
                parts.append(
                    f"\n*({len(security_files) - len([r for r in sorted(security_files) if r <= rel_path])} "
                    f"more security files. Use Grep to find symbols in them.)*"
                )
                break
            parts.append(section)
            total_chars += len(section)

    if other_files and total_chars < _MAX_INDEX_CHARS * 0.8:
        parts.append("\n### Other source files\n")
        for rel_path in sorted(other_files):
            section = _format_file_section(
                rel_path, other_files[rel_path], callers
            )
            if total_chars + len(section) > _MAX_INDEX_CHARS:
                remaining = len(other_files) - len(
                    [r for r in sorted(other_files) if r <= rel_path]
                )
                parts.append(
                    f"\n*({remaining} more files. Use Grep to find symbols.)*"
                )
                break
            parts.append(section)
            total_chars += len(section)

    return "\n".join(parts)


def _format_file_section(
    rel_path: str,
    symbols: list[tuple[str, str, int, str]],
    callers: dict[str, list[str]],
) -> str:
    """Format a single file's symbols."""
    lines = [f"**{rel_path}**"]
    for name, kind, line_num, sig in symbols:
        caller_info = ""
        if name in callers:
            caller_list = ", ".join(callers[name][:3])
            caller_info = f" [called by: {caller_list}]"
        lines.append(f"- `{kind} {name}` :{line_num}{caller_info}")
    return "\n".join(lines) + "\n"
