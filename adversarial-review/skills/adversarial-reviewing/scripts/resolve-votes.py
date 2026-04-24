#!/usr/bin/env python3
"""Tallies challenge round votes and determines resolution outcomes."""

import json
import math
import sys
from collections import Counter
from typing import Any, Dict, List


def compute_resolution(finding: Dict[str, Any], n_global: int) -> Dict[str, Any]:
    """Apply resolution rules to a single finding."""
    votes = finding["votes"]

    # Count vote positions
    agree_votes = [v for v in votes if v["position"] == "Agree"]
    challenge_votes = [v for v in votes if v["position"] == "Challenge"]
    abstain_votes = [v for v in votes if v["position"] == "Abstain"]

    agree_count = len(agree_votes)
    challenge_count = len(challenge_votes)
    abstain_count = len(abstain_votes)

    # Rule 1: compute effective pool
    n_effective = agree_count + challenge_count

    # Rule 2: single-specialist fallback
    single_specialist = n_effective < 2

    # Rule 3: compute thresholds
    strict_majority = math.ceil((n_effective + 1) / 2)
    quorum = strict_majority

    # Rule 4: apply outcome rules in order
    if n_effective == 0:
        outcome = "escalated_no_quorum"
    elif agree_count == n_effective and challenge_count == 0:
        outcome = "consensus"
    elif agree_count >= strict_majority:
        outcome = "majority"
    elif challenge_count >= strict_majority:
        outcome = "dismissed"
    elif (agree_count + challenge_count) < quorum:
        outcome = "escalated_no_quorum"
    else:
        outcome = "escalated"

    # Rule 5: resolve severity for passing findings
    resolved_severity = finding["severity"]
    severity_disputed = False

    if outcome in ("consensus", "majority") and agree_votes:
        severity_votes = [v["severity"] for v in agree_votes if v["severity"]]
        if severity_votes:
            severity_counter = Counter(severity_votes)
            most_common = severity_counter.most_common(2)
            resolved_severity = most_common[0][0]
            if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
                # Tie, use highest severity
                severities_order = ["Critical", "Important", "Moderate", "Low"]
                resolved_severity = min(severity_votes, key=lambda s: severities_order.index(s) if s in severities_order else 999)
            severity_disputed = len(set(severity_votes)) > 1

    # Determine label and report section
    if single_specialist:
        label = f"Single specialist ({n_effective}/{n_global} specialists)"
        report_section = 8
    elif outcome == "consensus":
        label = f"Consensus ({n_effective}/{n_global} specialists)"
        report_section = 3
    elif outcome == "majority":
        label = f"Majority ({n_effective}/{n_global} specialists)"
        report_section = 4
    elif outcome == "escalated":
        label = f"Escalated ({n_effective}/{n_global} specialists, no majority)"
        report_section = 5
    elif outcome == "escalated_no_quorum":
        label = f"Escalated (quorum not met, {n_effective}/{n_global} specialists)"
        report_section = 6
    else:  # dismissed
        label = f"Dismissed ({n_effective}/{n_global} specialists)"
        report_section = 7

    return {
        "id": finding["id"],
        "outcome": "single_specialist" if single_specialist else outcome,
        "agree_count": agree_count,
        "challenge_count": challenge_count,
        "abstain_count": abstain_count,
        "n_effective": n_effective,
        "n_global": n_global,
        "resolved_severity": resolved_severity,
        "severity_disputed": severity_disputed,
        "label": label,
        "report_section": report_section
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: resolve-votes.py <votes.json>", file=sys.stderr)
        sys.exit(1)

    votes_file = sys.argv[1]
    try:
        with open(votes_file) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {votes_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: {votes_file} contains invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error reading {votes_file}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        n_global = data["global_specialist_count"]
    except KeyError:
        print(f"Error: input JSON is missing required key 'global_specialist_count'", file=sys.stderr)
        sys.exit(1)

    if "findings" not in data:
        print(f"Error: input JSON is missing required key 'findings'", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data["findings"], list):
        print(f"Error: 'findings' must be a JSON array, got {type(data['findings']).__name__}", file=sys.stderr)
        sys.exit(1)

    try:
        resolutions = [compute_resolution(f, n_global) for f in data["findings"]]
    except KeyError as e:
        print(f"Error: a finding object is missing required key {e}", file=sys.stderr)
        print(f"Each finding needs at least 'id', 'votes', and 'severity' keys.", file=sys.stderr)
        sys.exit(1)

    # Build summary
    summary = Counter(r["outcome"] for r in resolutions)

    output = {
        "resolutions": resolutions,
        "summary": {
            "consensus": summary.get("consensus", 0),
            "majority": summary.get("majority", 0),
            "dismissed": summary.get("dismissed", 0),
            "escalated": summary.get("escalated", 0) + summary.get("escalated_no_quorum", 0),
            "single_specialist": summary.get("single_specialist", 0)
        }
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
