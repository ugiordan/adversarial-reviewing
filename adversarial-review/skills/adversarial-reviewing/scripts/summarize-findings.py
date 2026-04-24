#!/usr/bin/env python3
"""Generate finding summary statistics for adversarial review reports."""

import json
import sys
from collections import defaultdict


def main():
    if len(sys.argv) != 2:
        print("Usage: summarize-findings.py <resolution_output.json>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    try:
        with open(input_file) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: {input_file} contains invalid JSON: {e}", file=sys.stderr)
        print(f"Expected the output from resolve-votes.py.", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error reading {input_file}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, dict):
        print(f"Error: expected a JSON object, got {type(data).__name__}", file=sys.stderr)
        sys.exit(1)

    resolutions = data.get("resolutions", [])

    # Count by severity and outcome category
    stats = defaultdict(lambda: {"validated": 0, "dismissed": 0, "escalated": 0})
    consensus_count = 0
    majority_count = 0

    for res in resolutions:
        outcome = res.get("outcome")

        # Determine severity
        if outcome == "dismissed":
            # Use original severity from originator's finding
            originator = res.get("originator", {})
            severity = originator.get("severity", "Minor")
        else:
            severity = res.get("resolved_severity", "Minor")

        # Categorize outcome
        if outcome in ["consensus", "majority"]:
            stats[severity]["validated"] += 1
            if outcome == "consensus":
                consensus_count += 1
            else:
                majority_count += 1
        elif outcome == "dismissed":
            stats[severity]["dismissed"] += 1
        elif outcome in ["escalated", "escalated_no_quorum", "single_specialist"]:
            stats[severity]["escalated"] += 1

    # Generate markdown table
    print("## Finding Summary\n")
    print("| Severity | Validated | Dismissed | Escalated | Total |")
    print("|----------|-----------|-----------|-----------|-------|")

    severity_order = ["Critical", "Important", "Minor"]
    totals = {"validated": 0, "dismissed": 0, "escalated": 0, "total": 0}

    for severity in severity_order:
        s = stats[severity]
        total = s["validated"] + s["dismissed"] + s["escalated"]
        if total > 0:
            print(f"| {severity} | {s['validated']} | {s['dismissed']} | {s['escalated']} | {total} |")
            totals["validated"] += s["validated"]
            totals["dismissed"] += s["dismissed"]
            totals["escalated"] += s["escalated"]
            totals["total"] += total

    print(f"| **Total** | **{totals['validated']}** | **{totals['dismissed']}** | **{totals['escalated']}** | **{totals['total']}** |")

    print(f"\n**Outcome:** {totals['validated']} findings validated ({consensus_count} consensus, {majority_count} majority), {totals['dismissed']} dismissed, {totals['escalated']} escalated.")


if __name__ == "__main__":
    main()
