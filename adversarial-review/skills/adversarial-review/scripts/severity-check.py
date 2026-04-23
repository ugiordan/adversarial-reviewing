#!/usr/bin/env python3
"""Check for severity inflation in specialist findings."""

import argparse
import json
import re
import sys
from pathlib import Path

CRITICAL_THRESHOLD = 50
COMBINED_THRESHOLD = 80


def parse_severity(file_path):
    """Extract severity from a finding file."""
    pattern = re.compile(r'^Severity:\s*(Critical|Important|Minor)\s*$', re.IGNORECASE)
    with open(file_path) as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                return match.group(1).capitalize()
    return None


def analyze_findings(findings_map):
    """Analyze findings and detect inflation. findings_map: {specialist: [severities]}"""
    result = {"specialists": {}, "any_inflation": False}

    for specialist, severities in findings_map.items():
        total = len(severities)
        if total == 0:
            continue

        critical = sum(1 for s in severities if s == "Critical")
        important = sum(1 for s in severities if s == "Important")
        minor = sum(1 for s in severities if s == "Minor")

        critical_pct = (critical / total) * 100
        combined_pct = ((critical + important) / total) * 100
        inflation = critical_pct > CRITICAL_THRESHOLD or combined_pct > COMBINED_THRESHOLD

        result["specialists"][specialist] = {
            "total": total,
            "critical": critical,
            "important": important,
            "minor": minor,
            "critical_pct": round(critical_pct, 1),
            "combined_pct": round(combined_pct, 1),
            "inflation_warning": inflation
        }

        if inflation:
            result["any_inflation"] = True

    return result


def main():
    parser = argparse.ArgumentParser(description="Check severity inflation in findings")
    parser.add_argument("path", nargs="?", help="Findings directory")
    parser.add_argument("--file", help="Single findings file")
    parser.add_argument("--specialist", help="Specialist prefix (required with --file)")
    args = parser.parse_args()

    findings_map = {}

    if args.file:
        if not args.specialist:
            print("Error: --specialist required with --file", file=sys.stderr)
            sys.exit(1)
        severity = parse_severity(args.file)
        findings_map[args.specialist] = [severity] if severity else []
    elif args.path:
        findings_dir = Path(args.path)
        for subdir in findings_dir.iterdir():
            if not subdir.is_dir():
                continue
            specialist = subdir.name
            severities = []
            for finding_file in subdir.glob("*.md"):
                severity = parse_severity(finding_file)
                if severity:
                    severities.append(severity)
            if severities:
                findings_map[specialist] = severities
    else:
        parser.print_help()
        sys.exit(1)

    result = analyze_findings(findings_map)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
