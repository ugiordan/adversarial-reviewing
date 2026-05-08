#!/usr/bin/env python3
"""Parse red team audit output and create deep dive dispatch directories."""
import json
import os
import re
import sys
from pathlib import Path


def parse_audit_flags(text):
    """Extract flagged finding IDs from red team auditor output."""
    flags = []
    for line in text.splitlines():
        m = re.match(r"FLAG:\s*(\S+-\d+)\s*[-:]\s*(.*)", line)
        if m:
            flags.append({"finding_id": m.group(1), "concern": m.group(2).strip()})
    return flags


def main():
    if len(sys.argv) < 3:
        print("Usage: prepare_deep_dives.py <audit_output.md> <dispatch_dir>",
              file=sys.stderr)
        sys.exit(1)

    audit_path = sys.argv[1]
    dispatch_base = sys.argv[2]

    text = Path(audit_path).read_text()
    flags = parse_audit_flags(text)

    if not flags:
        print(json.dumps({"flags": 0, "deep_dives": []}))
        sys.exit(0)

    deep_dives = []
    for flag in flags:
        fid = flag["finding_id"]
        dd_dir = os.path.join(dispatch_base, f"DEEP-DIVE-{fid}")
        os.makedirs(dd_dir, exist_ok=True)
        Path(os.path.join(dd_dir, "dispatch-config.yaml")).write_text(
            f"dispatch_version: '3.0'\nagent_id: DEEP-DIVE-{fid}\n"
            f"phase: red-team-deep-dive\niteration: 1\n"
            f"output_path: {os.path.join(dd_dir, 'output.md')}\n"
            f"target_finding: {fid}\n"
        )
        Path(os.path.join(dd_dir, "agent-instructions.md")).write_text(
            f"Re-examine finding {fid}.\n\n"
            f"Red team concern: {flag['concern']}\n\n"
            f"Provide a concrete code trace or withdraw the finding.\n"
        )
        Path(os.path.join(dd_dir, "finding-to-verify.md")).write_text(
            f"# Deep Dive: {fid}\n\nRed team concern: {flag['concern']}\n"
        )
        Path(os.path.join(dd_dir, "output.md")).write_text("")
        deep_dives.append({"finding_id": fid, "dispatch_path": dd_dir})

    print(json.dumps({"flags": len(flags), "deep_dives": deep_dives}, indent=2))


if __name__ == "__main__":
    main()
