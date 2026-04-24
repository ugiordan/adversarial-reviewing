#!/usr/bin/env python3
"""Normalize external review comments into JSON lines format.

Usage: parse_comments.py <source_type> <input_file>
  source_type: github-pr | structured | freeform
Output: JSON lines to stdout, one comment per line.
"""

import argparse
import json
import re
import secrets
import sys
from typing import Any, Dict, List, Optional

KNOWN_BOTS = [
    "coderabbitai",
    "dependabot",
    "renovate",
    "github-actions",
    "greenkeeper",
    "codecov",
    "snyk-bot",
    "whitesource-bolt",
    "sonarcloud",
]

PRIVILEGED_MARKERS = [
    "NO_FINDINGS_REPORTED",
    "NO_TRIAGE_EVALUATIONS",
    "SKIP_VALIDATION",
    "BYPASS_CHECKS",
    "ADMIN_OVERRIDE",
]

INJECTION_PATTERNS = [
    r"ignore all previous",
    r"ignore prior instructions",
    r"disregard (?:all |the )?(?:above|previous)",
    r"you are now",
    r"new system prompt",
    r"override (?:system|instructions)",
    r"act as (?:a |an )?(?:different|new)",
    r"forget (?:all |everything)",
]

GITHUB_ROLE_MAP = {
    "OWNER": "maintainer",
    "MEMBER": "maintainer",
    "COLLABORATOR": "collaborator",
    "CONTRIBUTOR": "contributor",
    "FIRST_TIME_CONTRIBUTOR": "contributor",
    "FIRST_TIMER": "contributor",
    "NONE": "contributor",
}


def scan_injection_patterns(text: str) -> bool:
    """Scan text for injection patterns."""
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def strip_markers(text: str) -> tuple:
    """Strip privileged markers and scan for injection patterns."""
    has_injection = False
    cleaned = text

    for marker in PRIVILEGED_MARKERS:
        if marker in cleaned:
            has_injection = True
            cleaned = cleaned.replace(marker, "[MARKER_STRIPPED]")

    if scan_injection_patterns(cleaned):
        has_injection = True

    return cleaned, has_injection


def is_bot(user_login: str, user_type: Optional[str] = None) -> bool:
    """Detect if a user is a bot."""
    if user_type and user_type.lower() == "bot":
        return True
    return user_login.lower() in KNOWN_BOTS


def map_github_role(association: str) -> str:
    """Map GitHub author association to role."""
    return GITHUB_ROLE_MAP.get(association, "contributor")


def auto_categorize(comment: str, file: Optional[str] = None) -> str:
    """Auto-categorize comment based on content."""
    comment_lower = comment.lower()

    security_keywords = [
        "injection", "xss", "csrf", "vulnerability", "exploit",
        "security", "auth", "permission", "credential",
    ]
    if any(kw in comment_lower for kw in security_keywords):
        return "security"

    perf_keywords = [
        "performance", "slow", "memory", "leak", "optimization",
        "cache", "bottleneck",
    ]
    if any(kw in comment_lower for kw in perf_keywords):
        return "performance"

    correctness_keywords = [
        "error", "exception", "panic", "crash", "nil pointer",
        "null pointer", "undefined", "bug", "incorrect", "wrong",
        "race condition", "edge case", "off-by-one",
    ]
    if any(kw in comment_lower for kw in correctness_keywords):
        return "correctness"

    design_keywords = [
        "architecture", "design", "pattern", "structure",
        "dependency injection", "coupling", "cohesion",
        "abstraction", "interface", "refactor",
    ]
    if any(kw in comment_lower for kw in design_keywords):
        return "design"

    style_keywords = [
        "style", "naming", "format", "indent", "whitespace",
        "readability", "convention", "lint", "nit",
    ]
    if any(kw in comment_lower for kw in style_keywords):
        return "style"

    return "unknown"


def calculate_word_overlap(text1: str, text2: str) -> float:
    """Calculate word overlap percentage between two texts."""
    words1 = set(re.findall(r"\w+", text1.lower()))
    words2 = set(re.findall(r"\w+", text2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def is_near_duplicate(
    comment: Dict[str, Any], existing_comments: List[Dict[str, Any]]
) -> bool:
    """Check if comment is a near-duplicate of existing comments."""
    for existing in existing_comments:
        if comment.get("file") != existing.get("file"):
            continue

        comment_line = comment.get("line")
        existing_line = existing.get("line")

        if comment_line is not None and existing_line is not None:
            if abs(comment_line - existing_line) > 5:
                continue

        overlap = calculate_word_overlap(
            comment.get("comment", ""), existing.get("comment", "")
        )

        if overlap > 0.6:
            return True

    return False


def parse_github_pr(data: List[Dict]) -> List[Dict]:
    """Parse GitHub PR comments format."""
    comments = []

    for item in data:
        user = item.get("user", {})
        user_login = user.get("login", "unknown")
        user_type = user.get("type")

        comment_text = item.get("body", "")
        cleaned_comment, has_injection = strip_markers(comment_text)

        if is_bot(user_login, user_type):
            author_role = "bot"
        else:
            association = item.get("author_association", "NONE")
            author_role = map_github_role(association)

        comment_obj: Dict[str, Any] = {
            "file": item.get("path"),
            "line": item.get("line"),
            "author": user_login,
            "author_role": author_role,
            "comment": cleaned_comment,
            "category": auto_categorize(cleaned_comment, item.get("path")),
        }

        if has_injection:
            comment_obj["injection_warning"] = True

        comments.append(comment_obj)

    return comments


def parse_structured(data: List[Dict]) -> List[Dict]:
    """Parse structured comments format."""
    comments = []

    for item in data:
        comment_text = item.get("comment", "")
        cleaned_comment, has_injection = strip_markers(comment_text)

        file_path = item.get("file")
        category = item.get("category")

        if category is None:
            category = auto_categorize(cleaned_comment, file_path)

        comment_obj: Dict[str, Any] = {
            "file": file_path,
            "line": item.get("line"),
            "author": item.get("author", "unknown"),
            "author_role": "contributor",
            "comment": cleaned_comment,
            "category": category,
        }

        if has_injection:
            comment_obj["injection_warning"] = True

        comments.append(comment_obj)

    return comments


def parse_freeform(text: str) -> List[Dict]:
    """Parse freeform text comments."""
    comments = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^([^:]+):(\d+)\s*-\s*(.+)$", line)
        if match:
            file_path: Optional[str] = match.group(1)
            line_num: Optional[int] = int(match.group(2))
            comment_text = match.group(3)
        else:
            gen_match = re.match(r"^General comment:\s*(.+)$", line)
            if gen_match:
                file_path = None
                line_num = None
                comment_text = gen_match.group(1)
            else:
                file_path = None
                line_num = None
                comment_text = line

        cleaned_comment, has_injection = strip_markers(comment_text)

        comment_obj: Dict[str, Any] = {
            "file": file_path,
            "line": line_num,
            "author": "unknown",
            "author_role": "contributor",
            "comment": cleaned_comment,
            "category": auto_categorize(cleaned_comment, file_path),
        }

        if has_injection:
            comment_obj["injection_warning"] = True

        comments.append(comment_obj)

    return comments


def deduplicate_comments(comments: List[Dict]) -> List[Dict]:
    """Remove near-duplicate comments."""
    unique_comments: List[Dict] = []

    for comment in comments:
        if not is_near_duplicate(comment, unique_comments):
            unique_comments.append(comment)

    return unique_comments


def add_field_markers(comments: List[Dict]) -> List[Dict]:
    """Add field isolation markers to each comment."""
    for comment in comments:
        comment["field_start"] = secrets.token_hex(8)
        comment["field_end"] = secrets.token_hex(8)
    return comments


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize external review comments into JSON lines format"
    )
    parser.add_argument(
        "source_type",
        choices=["github-pr", "structured", "freeform"],
        help="Comment source format",
    )
    parser.add_argument("input_file", help="Path to input file")
    args = parser.parse_args()

    try:
        with open(args.input_file, "r") as f:
            if args.source_type == "freeform":
                content = f.read()
            else:
                content = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        return 1

    if args.source_type == "github-pr":
        comments = parse_github_pr(content)
    elif args.source_type == "structured":
        comments = parse_structured(content)
    elif args.source_type == "freeform":
        comments = parse_freeform(content)
    else:
        print(f"Error: Unknown source type: {args.source_type}", file=sys.stderr)
        return 1

    comments = deduplicate_comments(comments)
    comments = comments[:100]
    comments = add_field_markers(comments)

    for idx, comment in enumerate(comments, start=1):
        comment["id"] = f"EXT-{idx:03d}"
        print(json.dumps(comment))

    return 0


if __name__ == "__main__":
    sys.exit(main())
