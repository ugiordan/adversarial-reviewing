#!/usr/bin/env python3
"""Deduplicate findings by file + overlapping line range + same specialist category.

Usage: deduplicate.py <findings_file> [--cross-specialist]
  --cross-specialist: flag cross-specialist overlaps as co-located instead of merging
Output: deduplicated findings to stdout
Exit 0 on success.
"""

import argparse
import re
import sys
from typing import Dict, List


SEVERITY_RANK = {"Critical": 3, "Important": 2, "Minor": 1}


def parse_findings(content: str) -> List[Dict]:
    """Parse finding blocks from content."""
    if "NO_FINDINGS_REPORTED" in content and not re.search(
        r"Finding ID: [A-Z]+-\d+", content
    ):
        return []

    blocks = re.split(r"(?=Finding ID: [A-Z]+-\d+)", content)
    blocks = [
        b.strip()
        for b in blocks
        if b.strip() and re.match(r"Finding ID:", b.strip())
    ]

    findings = []
    for block in blocks:
        fid = re.search(r"Finding ID: ([A-Z]+-\d+)", block)
        specialist = re.search(r"Specialist: (.+)", block)
        severity = re.search(r"Severity: (\w+)", block)
        file_path = re.search(r"File: (.+)", block)
        lines = re.search(r"Lines: (\d+)(?:-(\d+))?", block)

        if fid and file_path and lines:
            findings.append(
                {
                    "id": fid.group(1),
                    "specialist": specialist.group(1).strip() if specialist else "",
                    "severity": severity.group(1) if severity else "",
                    "file": file_path.group(1).strip(),
                    "line_start": int(lines.group(1)),
                    "line_end": int(lines.group(2))
                    if lines.group(2)
                    else int(lines.group(1)),
                    "block": block,
                    "merged": False,
                    "co_located": [],
                }
            )

    return findings


def deduplicate(
    findings: List[Dict], cross_specialist: bool = False
) -> List[Dict]:
    """Deduplicate findings by file + overlapping line range."""
    merged_ids: set = set()

    for i, a in enumerate(findings):
        if a["id"] in merged_ids:
            continue
        for j, b in enumerate(findings):
            if i >= j or b["id"] in merged_ids:
                continue
            if a["file"] == b["file"]:
                overlap = (
                    a["line_start"] <= b["line_end"]
                    and b["line_start"] <= a["line_end"]
                )
                if overlap:
                    a_cat = a["id"].split("-")[0]
                    b_cat = b["id"].split("-")[0]
                    if a_cat == b_cat:
                        if SEVERITY_RANK.get(b["severity"], 0) > SEVERITY_RANK.get(
                            a["severity"], 0
                        ):
                            a["severity"] = b["severity"]
                        a["line_start"] = min(a["line_start"], b["line_start"])
                        a["line_end"] = max(a["line_end"], b["line_end"])
                        a["block"] += (
                            "\n\n[MERGED FROM " + b["id"] + "]\n" + b["block"]
                        )
                        merged_ids.add(b["id"])
                    elif cross_specialist:
                        a["co_located"].append(b["id"])
                        b["co_located"].append(a["id"])

    return [f for f in findings if f["id"] not in merged_ids]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deduplicate findings by file + overlapping line range"
    )
    parser.add_argument("findings_file", help="Path to findings file")
    parser.add_argument(
        "--cross-specialist",
        action="store_true",
        help="Flag cross-specialist overlaps as co-located",
    )
    args = parser.parse_args()

    try:
        with open(args.findings_file) as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {args.findings_file}", file=sys.stderr)
        return 1

    findings = parse_findings(content)
    if not findings:
        print("NO_FINDINGS_REPORTED")
        return 0

    results = deduplicate(findings, args.cross_specialist)

    for f in results:
        print(f["block"])
        if f["co_located"]:
            print(f"\n[CO-LOCATED with: {', '.join(f['co_located'])}]")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
