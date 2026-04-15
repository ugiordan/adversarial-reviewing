#!/usr/bin/env bash
set -euo pipefail

# parse-comments.sh - Normalize external review comments into JSON lines format
# Usage: parse-comments.sh <source_type> <input_file>
# source_type: "github-pr" | "structured" | "freeform"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <source_type> <input_file>" >&2
    echo "source_type: github-pr | structured | freeform" >&2
    exit 1
fi

SOURCE_TYPE="$1"
INPUT_FILE="$2"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: Input file not found: $INPUT_FILE" >&2
    exit 1
fi

# Delegate to Python for JSON processing
python3 - "$SOURCE_TYPE" "$INPUT_FILE" <<'PYTHON_SCRIPT'
import json
import sys
import re
import secrets
from typing import Dict, List, Any, Optional

# Known bot usernames
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

# Privileged markers to strip
PRIVILEGED_MARKERS = [
    "NO_FINDINGS_REPORTED",
    "NO_TRIAGE_EVALUATIONS",
    "SKIP_VALIDATION",
    "BYPASS_CHECKS",
    "ADMIN_OVERRIDE",
]

# GitHub author association to role mapping
GITHUB_ROLE_MAP = {
    "OWNER": "owner",
    "MEMBER": "member",
    "COLLABORATOR": "collaborator",
    "CONTRIBUTOR": "contributor",
    "FIRST_TIME_CONTRIBUTOR": "contributor",
    "FIRST_TIMER": "contributor",
    "NONE": "external",
}

def strip_markers(text: str) -> tuple[str, bool]:
    """Strip privileged markers from text and return (cleaned_text, has_injection)"""
    has_injection = False
    cleaned = text

    for marker in PRIVILEGED_MARKERS:
        if marker in cleaned:
            has_injection = True
            cleaned = cleaned.replace(marker, "[MARKER_STRIPPED]")

    return cleaned, has_injection

def is_bot(user_login: str, user_type: Optional[str] = None) -> bool:
    """Detect if a user is a bot"""
    if user_type and user_type.lower() == "bot":
        return True
    return user_login.lower() in KNOWN_BOTS

def map_github_role(association: str) -> str:
    """Map GitHub author association to role"""
    return GITHUB_ROLE_MAP.get(association, "external")

def auto_categorize(comment: str, file: Optional[str] = None) -> str:
    """Auto-categorize comment based on content"""
    comment_lower = comment.lower()

    # Security-related keywords
    if any(kw in comment_lower for kw in [
        "injection", "xss", "csrf", "vulnerability", "exploit",
        "security", "auth", "permission", "credential"
    ]):
        return "security"

    # Performance keywords
    if any(kw in comment_lower for kw in [
        "performance", "slow", "memory", "leak", "optimization",
        "cache", "bottleneck"
    ]):
        return "performance"

    # Architecture keywords
    if any(kw in comment_lower for kw in [
        "architecture", "design", "pattern", "structure",
        "dependency injection", "coupling"
    ]):
        return "architecture"

    # Error handling keywords
    if any(kw in comment_lower for kw in [
        "error", "exception", "panic", "crash", "nil pointer",
        "null pointer", "undefined"
    ]):
        return "error-handling"

    # Testing keywords
    if any(kw in comment_lower for kw in [
        "test", "coverage", "mock", "assertion"
    ]):
        return "testing"

    return "general"

def calculate_word_overlap(text1: str, text2: str) -> float:
    """Calculate word overlap percentage between two texts"""
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0

def is_near_duplicate(comment: Dict[str, Any], existing_comments: List[Dict[str, Any]]) -> bool:
    """Check if comment is a near-duplicate of existing comments"""
    for existing in existing_comments:
        # Same file
        if comment.get("file") != existing.get("file"):
            continue

        # Nearby lines (within 5 lines)
        comment_line = comment.get("line")
        existing_line = existing.get("line")

        if comment_line is not None and existing_line is not None:
            if abs(comment_line - existing_line) > 5:
                continue

        # Check word overlap
        overlap = calculate_word_overlap(
            comment.get("comment", ""),
            existing.get("comment", "")
        )

        if overlap > 0.6:  # More than 60% word overlap
            return True

    return False

def parse_github_pr(data: List[Dict]) -> List[Dict]:
    """Parse GitHub PR comments format"""
    comments = []

    for item in data:
        user = item.get("user", {})
        user_login = user.get("login", "unknown")
        user_type = user.get("type")

        comment_text = item.get("body", "")
        cleaned_comment, has_injection = strip_markers(comment_text)

        # Determine author role
        if is_bot(user_login, user_type):
            author_role = "bot"
        else:
            association = item.get("author_association", "NONE")
            author_role = map_github_role(association)

        file_path = item.get("path")
        line_num = item.get("line")

        comment_obj = {
            "file": file_path,
            "line": line_num,
            "author": user_login,
            "author_role": author_role,
            "comment": cleaned_comment,
            "category": auto_categorize(cleaned_comment, file_path),
        }

        if has_injection:
            comment_obj["injection_warning"] = True

        comments.append(comment_obj)

    return comments

def parse_structured(data: List[Dict]) -> List[Dict]:
    """Parse structured comments format"""
    comments = []

    for item in data:
        comment_text = item.get("comment", "")
        cleaned_comment, has_injection = strip_markers(comment_text)

        file_path = item.get("file")
        line_num = item.get("line")
        author = item.get("author", "unknown")
        category = item.get("category")

        if category is None:
            category = auto_categorize(cleaned_comment, file_path)

        comment_obj = {
            "file": file_path,
            "line": line_num,
            "author": author,
            "author_role": "external",
            "comment": cleaned_comment,
            "category": category,
        }

        if has_injection:
            comment_obj["injection_warning"] = True

        comments.append(comment_obj)

    return comments

def parse_freeform(text: str) -> List[Dict]:
    """Parse freeform text comments"""
    comments = []
    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try to parse file:line - comment format
        match = re.match(r'^([^:]+):(\d+)\s*-\s*(.+)$', line)
        if match:
            file_path = match.group(1)
            line_num = int(match.group(2))
            comment_text = match.group(3)
        else:
            # Try to parse "General comment: ..." format
            gen_match = re.match(r'^General comment:\s*(.+)$', line)
            if gen_match:
                file_path = None
                line_num = None
                comment_text = gen_match.group(1)
            else:
                # Default: treat whole line as comment
                file_path = None
                line_num = None
                comment_text = line

        cleaned_comment, has_injection = strip_markers(comment_text)

        comment_obj = {
            "file": file_path,
            "line": line_num,
            "author": "unknown",
            "author_role": "external",
            "comment": cleaned_comment,
            "category": auto_categorize(cleaned_comment, file_path),
        }

        if has_injection:
            comment_obj["injection_warning"] = True

        comments.append(comment_obj)

    return comments

def add_field_markers(comments: List[Dict]) -> List[Dict]:
    """Add field isolation markers to each comment"""
    for comment in comments:
        comment["field_start"] = secrets.token_hex(8)
        comment["field_end"] = secrets.token_hex(8)
    return comments

def deduplicate_comments(comments: List[Dict]) -> List[Dict]:
    """Remove near-duplicate comments"""
    unique_comments = []

    for comment in comments:
        if not is_near_duplicate(comment, unique_comments):
            unique_comments.append(comment)

    return unique_comments

def main():
    if len(sys.argv) < 3:
        print("Error: Missing arguments", file=sys.stderr)
        sys.exit(1)

    source_type = sys.argv[1]
    input_file = sys.argv[2]

    # Read input file
    try:
        with open(input_file, 'r') as f:
            if source_type == "freeform":
                content = f.read()
            else:
                content = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse comments based on source type
    if source_type == "github-pr":
        comments = parse_github_pr(content)
    elif source_type == "structured":
        comments = parse_structured(content)
    elif source_type == "freeform":
        comments = parse_freeform(content)
    else:
        print(f"Error: Unknown source type: {source_type}", file=sys.stderr)
        sys.exit(1)

    # Deduplicate
    comments = deduplicate_comments(comments)

    # Cap at 100 comments
    comments = comments[:100]

    # Add field isolation markers
    comments = add_field_markers(comments)

    # Add sequential IDs and output as JSON lines
    for idx, comment in enumerate(comments, start=1):
        comment["id"] = f"EXT-{idx:03d}"
        print(json.dumps(comment))

if __name__ == "__main__":
    main()
PYTHON_SCRIPT
