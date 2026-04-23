#!/usr/bin/env python3
"""Generate metadata block for adversarial review reports."""

import argparse
import json
import sys
from datetime import date


def main():
    parser = argparse.ArgumentParser(description="Format report metadata")
    parser.add_argument("--topic", required=True, help="Review topic name")
    parser.add_argument("--profile", required=True, choices=["code", "strat"], help="Review profile")
    parser.add_argument("--specialists", required=True, help="Comma-separated specialist list")
    parser.add_argument("--iterations", required=True, type=int, help="Number of iterations")
    parser.add_argument("--budget-json", required=True, help="Budget JSON string")
    parser.add_argument("--budget-limit", required=True, type=int, help="Budget limit in tokens")
    parser.add_argument("--commit", help="Git commit SHA")
    parser.add_argument("--preset", help="Preset name (quick/thorough/default)")
    parser.add_argument("--flags", help="Comma-separated flags")
    parser.add_argument("--guardrails", help="JSON array of triggered guardrails")

    args = parser.parse_args()

    # Parse budget JSON
    try:
        budget = json.loads(args.budget_json)
        consumed = budget.get("consumed", 0)
        cost = budget.get("consumed_cost_usd", 0.0)
    except json.JSONDecodeError:
        print("Error: invalid budget JSON", file=sys.stderr)
        sys.exit(1)

    # Parse guardrails if provided
    guardrails_count = 0
    if args.guardrails:
        try:
            guardrails = json.loads(args.guardrails)
            guardrails_count = len(guardrails) if isinstance(guardrails, list) else 0
        except json.JSONDecodeError:
            pass

    # Format values
    today = date.today().strftime("%Y-%m-%d")
    commit_short = args.commit[:7] if args.commit else "N/A"
    budget_limit_k = args.budget_limit // 1000
    consumed_k = consumed // 1000
    budget_pct = int((consumed / args.budget_limit * 100)) if args.budget_limit > 0 else 0

    # Build table
    print("## Review Configuration\n")
    print("| Parameter | Value |")
    print("|-----------|-------|")
    print(f"| Date | {today} |")
    print(f"| Commit | {commit_short} |")
    print(f"| Profile | {args.profile} |")
    if args.preset:
        print(f"| Preset | {args.preset} |")
    specialists = ", ".join(s.strip() for s in args.specialists.split(","))
    print(f"| Specialists | {specialists} |")
    print(f"| Iterations | {args.iterations} |")
    print(f"| Budget consumed | {consumed_k}K / {budget_limit_k}K ({budget_pct}%) |")
    print(f"| Estimated cost | ~${cost:.2f} |")
    if args.flags:
        print(f"| Flags | {args.flags} |")
    if guardrails_count > 0:
        print(f"| Guardrails triggered | {guardrails_count} |")


if __name__ == "__main__":
    main()
