"""Project structure scanner for adversarial-reviewing agents.

Builds a language-agnostic project map that tells agents WHERE to look
without hardcoding what to look for. Agents use their own expertise to
decide which patterns matter for the detected project type.

Optionally appends profile-specific hotspot grep results when
hotspot-patterns.yaml exists.
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

_SKIP_DIRS = {
    "vendor", "node_modules", ".git", "__pycache__", "testdata",
    "bin", ".idea", ".vscode", "output", ".cache",
}

_FRAMEWORK_MARKERS = {
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "setup.py": "Python",
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "package.json": "JavaScript/TypeScript",
    "tsconfig.json": "TypeScript",
    "Gemfile": "Ruby",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java (Gradle)",
    "CMakeLists.txt": "C/C++",
    "Makefile": "Make-based build",
    "Dockerfile": "Containerized",
}

_FRAMEWORK_SPECIALIZATIONS = {
    ("Go", "api/", "internal/controller/"): "Go Kubernetes operator",
    ("Go", "cmd/", "pkg/"): "Go CLI/library",
    ("Python", "manage.py",): "Python Django app",
    ("Python", "app.py",): "Python Flask app",
    ("Python", "main.py",): "Python application",
    ("JavaScript/TypeScript", "src/", "pages/"): "Next.js/React app",
    ("JavaScript/TypeScript", "src/", "routes/"): "Express server",
    ("Rust", "src/main.rs",): "Rust application",
    ("Java (Maven)", "src/main/java/"): "Java application",
}

_SECURITY_KEYWORDS = {
    "auth": "authentication/authorization",
    "secret": "secrets management",
    "credential": "secrets management",
    "password": "secrets management",
    "token": "authentication/authorization",
    "webhook": "webhook/admission",
    "rbac": "RBAC/permissions",
    "permission": "RBAC/permissions",
    "cert": "crypto/TLS",
    "tls": "crypto/TLS",
    "crypt": "crypto/TLS",
    "ssl": "crypto/TLS",
    "oauth": "authentication/authorization",
    "oidc": "authentication/authorization",
    "session": "authentication/authorization",
    "key": "crypto/TLS",
    "config": "configuration",
    "security": "security",
    "policy": "policy/access control",
    "role": "RBAC/permissions",
    "acl": "RBAC/permissions",
    "firewall": "network security",
    "network": "network security",
    "sanitize": "input validation",
    "validate": "input validation",
    "escape": "input validation",
    "gateway": "network/gateway",
    "proxy": "network/gateway",
    "hash": "crypto/TLS",
    "registry": "service registry",
}

_INFRA_FILES = {"Dockerfile", "Makefile", "docker-compose.yml", "docker-compose.yaml"}


def build_project_map(source_root: str) -> str:
    """Scan source tree and build a project structure map.

    Returns markdown with project type, directory tree, and
    security-relevant files grouped by concern.
    """
    if not os.path.isdir(source_root):
        return ""

    framework = _detect_framework(source_root)
    dir_tree = _build_dir_tree(source_root)
    security_files = _find_security_relevant_files(source_root)
    infra_files = _find_infra_files(source_root)

    return _format_project_map(
        source_root, framework, dir_tree, security_files, infra_files,
    )


def _detect_framework(source_root: str) -> str:
    """Detect project framework from marker files and directory structure."""
    detected_langs = []
    for marker, lang in _FRAMEWORK_MARKERS.items():
        if os.path.exists(os.path.join(source_root, marker)):
            detected_langs.append(lang)

    if not detected_langs:
        return "Unknown project type"

    primary = detected_langs[0]

    for (lang, *markers), specialization in _FRAMEWORK_SPECIALIZATIONS.items():
        if lang != primary:
            continue
        if all(
            os.path.exists(os.path.join(source_root, m)) or
            os.path.isdir(os.path.join(source_root, m.rstrip("/")))
            for m in markers
        ):
            return specialization

    extras = [l for l in detected_langs[1:] if l != primary]
    if extras:
        return f"{primary} project (also: {', '.join(extras)})"
    return f"{primary} project"


def _build_dir_tree(source_root: str, max_depth: int = 3) -> list[tuple[str, int, dict[str, int]]]:
    """Build compact directory tree with file counts by extension.

    Returns [(rel_dir_path, total_files, {ext: count})].
    """
    result = []

    for root, dirs, files in os.walk(source_root):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        rel = os.path.relpath(root, source_root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > max_depth:
            dirs.clear()
            continue

        ext_counts: dict[str, int] = defaultdict(int)
        for f in files:
            if f.startswith("."):
                continue
            ext = os.path.splitext(f)[1].lower() or "(no ext)"
            ext_counts[ext] += 1

        if ext_counts:
            result.append((rel, sum(ext_counts.values()), dict(ext_counts)))

    return result


def _find_security_relevant_files(source_root: str) -> dict[str, list[str]]:
    """Find files whose names match security-relevant keywords.

    Returns {concern_category: [relative_file_paths]}.
    """
    by_concern: dict[str, list[str]] = defaultdict(list)

    for root, dirs, files in os.walk(source_root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname.startswith("."):
                continue
            lower = fname.lower()
            rel = os.path.relpath(os.path.join(root, fname), source_root)

            dir_parts = rel.lower().split(os.sep)

            for keyword, concern in _SECURITY_KEYWORDS.items():
                if keyword in lower or any(keyword in part for part in dir_parts):
                    by_concern[concern].append(rel)
                    break

    for concern in by_concern:
        by_concern[concern] = sorted(set(by_concern[concern]))[:30]

    return dict(by_concern)


def _find_infra_files(source_root: str) -> list[str]:
    """Find infrastructure files (Dockerfile, Makefile, docker-compose, etc.)."""
    found = []
    for root, dirs, files in os.walk(source_root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname in _INFRA_FILES:
                found.append(os.path.relpath(os.path.join(root, fname), source_root))
    return sorted(found)[:20]


def _format_project_map(
    source_root: str,
    framework: str,
    dir_tree: list[tuple[str, int, dict[str, int]]],
    security_files: dict[str, list[str]],
    infra_files: list[str],
) -> str:
    """Format project map as markdown."""
    parts = [
        "## Project Map\n",
        f"**Project type:** {framework}",
        f"**Source root:** {source_root}\n",
    ]

    parts.append("### Directory Structure")
    parts.append("| Directory | Files | Primary types |")
    parts.append("|-----------|-------|---------------|")
    for rel, total, exts in dir_tree[:40]:
        top_exts = sorted(exts.items(), key=lambda x: x[1], reverse=True)[:3]
        ext_str = ", ".join(f"{e}({c})" for e, c in top_exts)
        display = rel if rel != "." else "(root)"
        parts.append(f"| `{display}` | {total} | {ext_str} |")
    parts.append("")

    if security_files:
        parts.append("### Security-Relevant Files")
        parts.append(
            "Files flagged by naming convention. **You MUST examine each of these.**"
        )
        for concern in sorted(security_files):
            files = security_files[concern]
            parts.append(f"\n**{concern}** ({len(files)} files)")
            for f in files[:15]:
                parts.append(f"- `{f}`")
            if len(files) > 15:
                parts.append(f"- ... and {len(files) - 15} more")
        parts.append("")

    if infra_files:
        parts.append("### Infrastructure Files")
        for f in infra_files:
            parts.append(f"- `{f}`")
        parts.append("")

    return "\n".join(parts)


# -- Backward-compatible hotspot pattern support --
# These functions are kept for profiles that have hotspot-patterns.yaml.
# The project map works without them.

from .hotspots import load_hotspot_patterns, compute_hotspots  # noqa: F401, E402
