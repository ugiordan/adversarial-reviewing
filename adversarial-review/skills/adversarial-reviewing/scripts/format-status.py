#!/usr/bin/env python3
"""Format the progress status block for adversarial review.

Usage:
  format-status.py --topic <name> --phase <phase> [options]

Options:
  --topic <name>          Review topic name
  --phase <name>          Phase name (e.g. "Phase 1: Self-Refinement")
  --progress <detail>     Progress detail (e.g. "Iteration 2/3")
  --agents <json>         JSON array: [{"name":"SEC","status":"DONE","findings":"5 -> 3"}]
  --budget-json <json>    JSON from track-budget.sh status
  --budget-limit <n>      Budget limit in tokens

Output: formatted status block to stdout.
"""

import json
import math
import sys


def build_budget_line(budget_json: dict, limit: int) -> str:
    consumed = budget_json.get("consumed", 0)
    cost = budget_json.get("consumed_cost_usd", 0)
    pct = (consumed / limit * 100) if limit > 0 else 0
    filled = round(pct / 100 * 14)
    empty = 14 - filled
    bar = "\u2588" * filled + "\u2591" * empty
    return f" Budget: {bar}  {consumed // 1000}K / {limit // 1000}K ({int(pct)}%)  ~${cost:.2f} "


def build_block(topic: str, phase: str, progress: str,
                agents: list, budget_line: str) -> str:
    # Build content lines
    title_line = f"  ADVERSARIAL REVIEW: {topic}  "
    if progress:
        phase_line = f"  {phase}  [{progress}]  "
    else:
        phase_line = f"  {phase}  "

    # Agent table columns
    col1_header = "Agent"
    col2_header = "Status"
    col3_header = "Findings"

    col1_w = max(len(col1_header), max((len(a["name"]) for a in agents), default=0)) + 2
    col2_w = max(len(col2_header), max((len(a["status"]) for a in agents), default=0)) + 2
    col3_w = max(len(col3_header), max((len(a.get("findings", "")) for a in agents), default=0)) + 2

    table_w = col1_w + 1 + col2_w + 1 + col3_w  # +1 for each separator

    inner_w = max(table_w, len(title_line), len(phase_line), len(budget_line))

    # Recalculate col3 to absorb extra width
    col3_w = inner_w - col1_w - 1 - col2_w - 1

    def pad(text: str) -> str:
        return f"\u2502{text:<{inner_w}}\u2502"

    def hline(left, mid1, mid2, right, fill="\u2500"):
        c1 = fill * col1_w
        c2 = fill * col2_w
        c3 = fill * (inner_w - col1_w - 1 - col2_w - 1)
        return f"{left}{c1}{mid1}{c2}{mid2}{c3}{right}"

    def cell_row(a, b, c):
        return f"\u2502 {a:<{col1_w - 2}} \u2502 {b:<{col2_w - 2}} \u2502 {c:<{col3_w - 2}} \u2502"

    lines = []
    # Top border
    lines.append(f"\u250c{'\u2500' * inner_w}\u2510")
    # Title + phase
    lines.append(pad(title_line.ljust(inner_w)))
    lines.append(pad(phase_line.ljust(inner_w)))
    # Header separator with T-junctions
    lines.append(hline("\u251c", "\u252c", "\u252c", "\u2524"))
    # Header row
    lines.append(cell_row(col1_header, col2_header, col3_header))
    # Header-body separator
    lines.append(hline("\u251c", "\u253c", "\u253c", "\u2524"))
    # Agent rows
    for a in agents:
        lines.append(cell_row(a["name"], a["status"], a.get("findings", "")))
    # Bottom of agent table with inverted T-junctions
    lines.append(hline("\u251c", "\u2534", "\u2534", "\u2524"))
    # Budget line
    lines.append(pad(budget_line.ljust(inner_w)))
    # Bottom border
    lines.append(f"\u2514{'\u2500' * inner_w}\u2518")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Format progress status block")
    parser.add_argument("--topic", required=True, help="Review topic name")
    parser.add_argument("--phase", required=True, help="Phase name")
    parser.add_argument("--progress", default="", help="Progress detail")
    parser.add_argument("--agents", required=True, help="JSON array of agent status objects")
    parser.add_argument("--budget-json", default="{}", help="JSON from track-budget.sh status")
    parser.add_argument("--budget-limit", type=int, default=800000, help="Budget limit in tokens")
    args = parser.parse_args()

    try:
        agents = json.loads(args.agents)
    except json.JSONDecodeError as e:
        print(f"Error: --agents is not valid JSON: {e}", file=sys.stderr)
        print(f"Expected a JSON array like: '[{{\"name\":\"SEC\",\"status\":\"DONE\",\"findings\":\"3\"}}]'", file=sys.stderr)
        sys.exit(1)

    if not isinstance(agents, list):
        print(f"Error: --agents must be a JSON array, got {type(agents).__name__}", file=sys.stderr)
        sys.exit(1)

    for i, agent in enumerate(agents):
        if not isinstance(agent, dict):
            print(f"Error: agent at index {i} is not an object: {agent!r}", file=sys.stderr)
            sys.exit(1)
        for required_key in ("name", "status"):
            if required_key not in agent:
                print(f"Error: agent at index {i} is missing required key '{required_key}'", file=sys.stderr)
                print(f"Each agent object needs at least 'name' and 'status' keys.", file=sys.stderr)
                sys.exit(1)

    try:
        budget = json.loads(args.budget_json)
    except json.JSONDecodeError as e:
        print(f"Error: --budget-json is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    budget_line = build_budget_line(budget, args.budget_limit)
    block = build_block(args.topic, args.phase, args.progress, agents, budget_line)
    print(block)


if __name__ == "__main__":
    main()
