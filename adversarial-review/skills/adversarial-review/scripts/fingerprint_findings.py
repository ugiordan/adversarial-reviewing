#!/usr/bin/env python3
"""Cross-run finding persistence via stable content-based fingerprints.

Generates SHA-256 fingerprints for adversarial-review findings and tracks them
across runs. Fingerprints are stable across minor line shifts (bucketed to
nearest 5 lines) and whitespace variations.

Usage:
    # Add fingerprints to findings JSON
    fingerprint_findings.py fingerprint findings.json

    # Compare two fingerprinted runs
    fingerprint_findings.py compare current.json previous.json

    # Manage history
    fingerprint_findings.py history append findings.json --commit abc123
    fingerprint_findings.py history query a1b2c3d4e5f67890
    fingerprint_findings.py history summary

Exit codes:
    0  Success
    1  Error
    2  No findings found
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HISTORY_DIR = ".adversarial-review"
HISTORY_FILE = "findings-history.jsonl"


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------

def parse_line_range(lines_str: str) -> tuple[int, int]:
    """Parse a line range string into (start, end) ints.

    Handles formats: "10-20", "10", "L10-L20", empty/missing.
    """
    if not lines_str or lines_str.strip() == "":
        return (0, 0)

    cleaned = lines_str.strip().upper().replace("L", "")

    m = re.match(r"(\d+)\s*[-–]\s*(\d+)", cleaned)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    m = re.match(r"(\d+)", cleaned)
    if m:
        val = int(m.group(1))
        return (val, val)

    return (0, 0)


def fingerprint_finding(finding: dict) -> str:
    """Generate stable content-based fingerprint for a finding.

    The fingerprint is a 16-char hex string (64 bits) derived from SHA-256 of
    normalized finding attributes. Line ranges are bucketed to nearest 5 lines
    so small shifts between runs don't change the fingerprint.
    """
    # Specialist prefix from finding_id (snake_case from findings-to-json.py)
    fid = finding.get("finding_id", finding.get("Finding ID", ""))
    prefix = fid[:4].upper() if fid else ""
    # Strip trailing dash/hyphen for consistency
    prefix = prefix.rstrip("-")

    # File path: code findings use 'file', strat findings use 'document'
    file_path = finding.get("file", finding.get("File", ""))
    if not file_path:
        file_path = finding.get("document", finding.get("Document", ""))
    file_path = file_path.strip().lower()

    # Bucket line ranges to nearest 5 to tolerate small shifts
    lines = finding.get("lines", finding.get("Lines", "0-0"))
    start, end = parse_line_range(lines)
    start_bucket = (start // 5) * 5
    end_bucket = (end // 5) * 5

    # Title: lowercased, whitespace-normalized
    title = finding.get("title", finding.get("Title", ""))
    title = " ".join(title.lower().split())

    # Category (strat findings)
    category = finding.get("category", finding.get("Category", ""))
    category = category.lower().strip()

    content = f"{prefix}|{file_path}|{start_bucket}-{end_bucket}|{title}|{category}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def add_fingerprints(findings: list[dict]) -> list[dict]:
    """Add fingerprint field to each finding in the list."""
    for finding in findings:
        finding["fingerprint"] = fingerprint_finding(finding)
    return findings


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_findings(
    current: list[dict],
    previous: list[dict],
    history_entries: list[dict] | None = None,
) -> dict[str, Any]:
    """Compare two sets of fingerprinted findings.

    Returns a dict with new, recurring, resolved, and regressed findings
    plus summary counts.
    """
    current_by_fp = {}
    for f in current:
        fp = f.get("fingerprint") or fingerprint_finding(f)
        current_by_fp[fp] = f

    previous_by_fp = {}
    for f in previous:
        fp = f.get("fingerprint") or fingerprint_finding(f)
        previous_by_fp[fp] = f

    current_fps = set(current_by_fp.keys())
    previous_fps = set(previous_by_fp.keys())

    new_fps = current_fps - previous_fps
    recurring_fps = current_fps & previous_fps
    resolved_fps = previous_fps - current_fps

    # Build recurring entries with severity change detection
    recurring = []
    for fp in recurring_fps:
        entry = dict(current_by_fp[fp])
        prev_sev = previous_by_fp[fp].get("severity", "")
        curr_sev = entry.get("severity", "")
        if prev_sev.lower() != curr_sev.lower():
            entry["severity_changed"] = True
            entry["previous_severity"] = prev_sev
        else:
            entry["severity_changed"] = False
        recurring.append(entry)

    # Detect regressions: findings that were resolved at some point but
    # reappeared. Requires history data.
    regressed = []
    if history_entries:
        resolved_history_fps = set()
        for h in history_entries:
            if h.get("status") == "resolved":
                resolved_history_fps.add(h.get("fingerprint"))
        for fp in new_fps:
            if fp in resolved_history_fps:
                entry = dict(current_by_fp[fp])
                entry["regressed"] = True
                regressed.append(entry)

    regressed_fps = {f["fingerprint"] for f in regressed}
    truly_new = [current_by_fp[fp] for fp in new_fps if fp not in regressed_fps]

    return {
        "summary": {
            "new": len(truly_new),
            "recurring": len(recurring),
            "resolved": len(resolved_fps),
            "regressed": len(regressed),
            "total_current": len(current),
            "total_previous": len(previous),
        },
        "new": truly_new,
        "recurring": recurring,
        "resolved": [previous_by_fp[fp] for fp in resolved_fps],
        "regressed": regressed,
    }


# ---------------------------------------------------------------------------
# History management
# ---------------------------------------------------------------------------

def get_history_path() -> Path:
    """Get the path to the findings history file.

    Walks up from cwd looking for an existing .adversarial-review directory,
    falls back to creating one in cwd.
    """
    cwd = Path.cwd()
    check = cwd
    while check != check.parent:
        candidate = check / HISTORY_DIR
        if candidate.is_dir():
            return candidate / HISTORY_FILE
        check = check.parent

    return cwd / HISTORY_DIR / HISTORY_FILE


def load_history(path: Path | None = None) -> list[dict]:
    """Load all history entries from the JSONL file."""
    if path is None:
        path = get_history_path()
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def get_current_commit() -> str:
    """Get current git commit SHA, or 'unknown' if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "unknown"


def history_append(findings: list[dict], commit_sha: str | None = None) -> int:
    """Append current run's findings to history file.

    Returns number of entries written.
    """
    if commit_sha is None:
        commit_sha = get_current_commit()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = get_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing history to detect resolved findings
    existing = load_history(path)
    previous_active_fps = set()
    for e in existing:
        if e.get("status") == "active":
            previous_active_fps.add(e.get("fingerprint"))

    current_fps = set()
    entries_written = 0

    with open(path, "a", encoding="utf-8") as f:
        for finding in findings:
            fp = finding.get("fingerprint") or fingerprint_finding(finding)
            current_fps.add(fp)
            entry = {
                "timestamp": timestamp,
                "commit_sha": commit_sha,
                "fingerprint": fp,
                "finding_id": finding.get("finding_id", finding.get("Finding ID", "")),
                "severity": finding.get("severity", ""),
                "title": finding.get("title", finding.get("Title", "")),
                "status": "active",
            }
            f.write(json.dumps(entry) + "\n")
            entries_written += 1

        # Mark resolved findings
        resolved_fps = previous_active_fps - current_fps
        for fp in resolved_fps:
            entry = {
                "timestamp": timestamp,
                "commit_sha": commit_sha,
                "fingerprint": fp,
                "finding_id": "",
                "severity": "",
                "title": "",
                "status": "resolved",
            }
            f.write(json.dumps(entry) + "\n")
            entries_written += 1

    return entries_written


def history_query(fingerprint: str) -> dict[str, Any] | None:
    """Look up a finding's history by fingerprint."""
    entries = load_history()
    matching = [e for e in entries if e.get("fingerprint") == fingerprint]
    if not matching:
        return None

    active_entries = [e for e in matching if e.get("status") == "active"]
    resolved_entries = [e for e in matching if e.get("status") == "resolved"]

    first_seen = min(e["timestamp"] for e in matching)
    last_seen = max(e["timestamp"] for e in matching)

    return {
        "fingerprint": fingerprint,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "run_count": len(active_entries),
        "times_resolved": len(resolved_entries),
        "currently_active": matching[-1].get("status") == "active",
        "latest_finding_id": next(
            (e.get("finding_id") for e in reversed(active_entries) if e.get("finding_id")),
            "",
        ),
        "latest_severity": next(
            (e.get("severity") for e in reversed(active_entries) if e.get("severity")),
            "",
        ),
        "history": matching,
    }


def history_summary() -> dict[str, Any]:
    """Generate summary stats from the history file."""
    entries = load_history()
    if not entries:
        return {
            "total_entries": 0,
            "unique_findings": 0,
            "currently_active": 0,
            "resolved": 0,
            "recurrence_rate": 0.0,
            "runs": 0,
        }

    # Group by fingerprint
    by_fp: dict[str, list[dict]] = {}
    for e in entries:
        fp = e.get("fingerprint", "")
        if fp not in by_fp:
            by_fp[fp] = []
        by_fp[fp].append(e)

    # Track unique timestamps as proxy for runs
    unique_timestamps = set(e.get("timestamp", "") for e in entries)

    currently_active = 0
    resolved = 0
    recurred = 0

    for fp, fp_entries in by_fp.items():
        latest = fp_entries[-1]
        if latest.get("status") == "active":
            currently_active += 1
        else:
            resolved += 1

        # Check for recurrence: resolved then active again
        statuses = [e.get("status") for e in fp_entries]
        for i in range(1, len(statuses)):
            if statuses[i] == "active" and statuses[i - 1] == "resolved":
                recurred += 1
                break

    unique_count = len(by_fp)
    recurrence_rate = recurred / unique_count if unique_count else 0.0

    return {
        "total_entries": len(entries),
        "unique_findings": unique_count,
        "currently_active": currently_active,
        "resolved": resolved,
        "recurrence_rate": round(recurrence_rate, 3),
        "runs": len(unique_timestamps),
    }


# ---------------------------------------------------------------------------
# Input loading helpers
# ---------------------------------------------------------------------------

def load_findings_json(filepath: str) -> list[dict]:
    """Load findings from a JSON file produced by findings-to-json.py.

    Handles both the top-level array format and the wrapped format with
    a 'findings' key.
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "findings" in data:
        return data["findings"]

    print(f"Error: unexpected JSON structure in {filepath}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_fingerprint(args: argparse.Namespace) -> None:
    """Subcommand: add fingerprints to findings JSON."""
    findings = load_findings_json(args.findings_json)
    if not findings:
        print("No findings to fingerprint.", file=sys.stderr)
        sys.exit(2)

    add_fingerprints(findings)
    json.dump(findings, sys.stdout, indent=2)
    print()


def cmd_compare(args: argparse.Namespace) -> None:
    """Subcommand: compare two fingerprinted finding sets."""
    current = load_findings_json(args.current_json)
    previous = load_findings_json(args.previous_json)

    if not current and not previous:
        print("Both finding sets are empty.", file=sys.stderr)
        sys.exit(2)

    # Load history for regression detection if available
    history_path = get_history_path()
    history_entries = load_history(history_path) if history_path.exists() else None

    result = compare_findings(current, previous, history_entries)
    json.dump(result, sys.stdout, indent=2)
    print()


def cmd_history(args: argparse.Namespace) -> None:
    """Subcommand: manage findings history."""
    action = args.action

    if action == "append":
        if not args.findings_json:
            print("Error: history append requires <findings_json>", file=sys.stderr)
            sys.exit(1)
        findings = load_findings_json(args.findings_json)
        if not findings:
            print("No findings to append.", file=sys.stderr)
            sys.exit(2)
        # Ensure fingerprints are present
        add_fingerprints(findings)
        commit = args.commit or get_current_commit()
        count = history_append(findings, commit)
        path = get_history_path()
        print(json.dumps({
            "entries_written": count,
            "history_file": str(path),
            "commit_sha": commit,
        }, indent=2))

    elif action == "query":
        # Fingerprint can come from --fingerprint flag or positional arg
        fp_val = args.fingerprint or args.findings_json
        if not fp_val:
            print("Error: history query requires <fingerprint>", file=sys.stderr)
            sys.exit(1)
        result = history_query(fp_val)
        if result is None:
            print(json.dumps({"error": "fingerprint not found", "fingerprint": args.fingerprint}, indent=2))
            sys.exit(1)
        json.dump(result, sys.stdout, indent=2)
        print()

    elif action == "summary":
        result = history_summary()
        json.dump(result, sys.stdout, indent=2)
        print()

    else:
        print(f"Error: unknown history action '{action}'", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-run finding persistence via content-based fingerprints.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fingerprint subcommand
    fp_parser = subparsers.add_parser(
        "fingerprint",
        help="Add fingerprints to findings JSON",
    )
    fp_parser.add_argument("findings_json", help="Path to findings JSON file")
    fp_parser.set_defaults(func=cmd_fingerprint)

    # compare subcommand
    cmp_parser = subparsers.add_parser(
        "compare",
        help="Compare two fingerprinted finding sets",
    )
    cmp_parser.add_argument("current_json", help="Path to current findings JSON")
    cmp_parser.add_argument("previous_json", help="Path to previous findings JSON")
    cmp_parser.set_defaults(func=cmd_compare)

    # history subcommand
    hist_parser = subparsers.add_parser(
        "history",
        help="Manage findings history file",
    )
    hist_parser.add_argument(
        "action",
        choices=["append", "query", "summary"],
        help="History action to perform",
    )
    hist_parser.add_argument(
        "findings_json",
        nargs="?",
        help="Path to findings JSON (for append)",
    )
    hist_parser.add_argument(
        "--fingerprint",
        help="Fingerprint to query (for query action)",
    )
    hist_parser.add_argument(
        "--commit",
        help="Commit SHA to associate with this run (default: current HEAD)",
    )
    hist_parser.set_defaults(func=cmd_history)

    args = parser.parse_args()
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"Error: file not found: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
