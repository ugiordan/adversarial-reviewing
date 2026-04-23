#!/usr/bin/env python3
"""Format the scope confirmation display for adversarial review.

Usage:
  format-scope.py <scope_file> [options]

Arguments:
  scope_file              File with one path per line (repo-relative)

Options:
  --source-dir <dir>      Root directory to resolve file sizes (default: cwd)
  --specialists <list>    Comma-separated specialist list, e.g. "SEC,CORR,ARCH,QUAL,PERF"
  --budget-estimate <json> JSON from track-budget.sh estimate
  --budget-limit <n>      Configured budget limit in tokens
  --sensitive <list>      Comma-separated list of excluded sensitive files (if any)

Output: formatted scope confirmation block to stdout.
"""

import json
import os
import sys


def human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    k = size_bytes / 1024
    if k < 10:
        return f"{k:.1f}K"
    return f"{int(round(k))}K"


def estimate_tokens(total_chars: int) -> int:
    return int(total_chars / 4)


SPECIALIST_NAMES = {
    "SEC": "Security Auditor",
    "PERF": "Performance Analyst",
    "QUAL": "Code Quality Reviewer",
    "CORR": "Correctness Verifier",
    "ARCH": "Architecture Reviewer",
    "FEAS": "Feasibility Analyst",
    "USER": "User Impact Analyst",
    "SCOP": "Scope & Completeness Analyst",
}


def format_table(files: list, sizes: list) -> str:
    n_width = max(len(str(len(files))), 1)
    path_width = max((len(f) for f in files), default=4)
    size_width = max((len(s) for s in sizes), default=4)

    # Minimums for headers
    n_width = max(n_width, len("#"))
    path_width = max(path_width, len("File"))
    size_width = max(size_width, len("Size"))

    # Add padding (1 space each side)
    n_col = n_width + 2
    path_col = path_width + 2
    size_col = size_width + 2

    top = f"\u250c{'\u2500' * n_col}\u252c{'\u2500' * path_col}\u252c{'\u2500' * size_col}\u2510"
    hdr_sep = f"\u251c{'\u2500' * n_col}\u253c{'\u2500' * path_col}\u253c{'\u2500' * size_col}\u2524"
    bot = f"\u2514{'\u2500' * n_col}\u2534{'\u2500' * path_col}\u2534{'\u2500' * size_col}\u2518"

    def row(a, b, c):
        return f"\u2502 {a:<{n_width}} \u2502 {b:<{path_width}} \u2502 {c:<{size_width}} \u2502"

    lines = [top, row("#", "File", "Size"), hdr_sep]
    for i, (f, s) in enumerate(zip(files, sizes), 1):
        lines.append(row(str(i), f, s))
    lines.append(bot)
    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Format scope confirmation display")
    parser.add_argument("scope_file", help="File with one path per line")
    parser.add_argument("--source-dir", default=".", help="Root directory for resolving sizes")
    parser.add_argument("--specialists", default="", help="Comma-separated specialist prefixes")
    parser.add_argument("--budget-estimate", default="", help="JSON from track-budget.sh estimate")
    parser.add_argument("--budget-limit", type=int, default=0, help="Configured budget limit")
    parser.add_argument("--sensitive", default="", help="Comma-separated excluded sensitive files")
    args = parser.parse_args()

    # Read scope file
    with open(args.scope_file) as f:
        files = [line.strip().removeprefix("./") for line in f if line.strip()]

    if not files:
        print("No files in scope.", file=sys.stderr)
        sys.exit(1)

    # Resolve sizes
    source_dir = os.path.abspath(args.source_dir)
    sizes = []
    total_bytes = 0
    for fp in files:
        full = os.path.join(source_dir, fp)
        try:
            sz = os.path.getsize(full)
        except OSError:
            sz = 0
        sizes.append(human_size(sz))
        total_bytes += sz

    total_tokens = estimate_tokens(total_bytes)

    # Header
    print(f"Files ({len(files)} files, ~{total_tokens // 1000}K tokens):\n")

    # Table
    print(format_table(files, sizes))

    # Specialists
    if args.specialists:
        prefixes = [s.strip() for s in args.specialists.split(",") if s.strip()]
        spec_parts = []
        for p in prefixes:
            name = SPECIALIST_NAMES.get(p, p)
            spec_parts.append(f"{name} ({p})")
        print(f"\nSpecialists: {', '.join(spec_parts)}")

    # Budget
    if args.budget_estimate and args.budget_limit:
        try:
            est = json.loads(args.budget_estimate)
            est_tokens = est.get("estimated_tokens", 0)
            est_cost = est.get("estimated_cost_usd", 0)
            limit = args.budget_limit
            print(f"\nBudget: ~{est_tokens // 1000}K / {limit // 1000}K tokens (~${est_cost:.2f})")
        except (json.JSONDecodeError, KeyError):
            pass

    # Sensitive files
    if args.sensitive:
        excluded = [s.strip() for s in args.sensitive.split(",") if s.strip()]
        if excluded:
            print(f"\nExcluded sensitive files: {', '.join(excluded)}")
        else:
            print("\nNo sensitive files detected in scope.")
    else:
        print("\nNo sensitive files detected in scope.")


if __name__ == "__main__":
    main()
