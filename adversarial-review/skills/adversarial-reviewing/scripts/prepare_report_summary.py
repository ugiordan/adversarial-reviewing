#!/usr/bin/env python3
"""Pre-process findings for the report agent."""
import json
import os
import sys
from pathlib import Path


def collect_findings(cache_dir):
    """Collect all agent output files with findings."""
    findings = []
    dispatch_dir = os.path.join(cache_dir, "dispatch")
    if not os.path.isdir(dispatch_dir):
        return findings
    for entry in sorted(os.listdir(dispatch_dir)):
        entry_path = os.path.join(dispatch_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        output = os.path.join(entry_path, "output.md")
        if os.path.isfile(output):
            content = Path(output).read_text()
            if content.strip() and len(content.strip()) > 50:
                findings.append({"source": entry, "content": content})
    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: prepare_report_summary.py <cache_dir>", file=sys.stderr)
        sys.exit(1)

    cache_dir = sys.argv[1]
    findings = collect_findings(cache_dir)

    parts = [f"# Review Findings Summary\n\nTotal sources: {len(findings)}\n"]
    for f in findings:
        parts.append(f"## From: {f['source']}\n\n{f['content'][:5000]}\n")

    print("\n".join(parts))


if __name__ == "__main__":
    main()
