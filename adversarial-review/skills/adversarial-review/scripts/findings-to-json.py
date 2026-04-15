#!/usr/bin/env python3
"""Convert adversarial-review findings to structured JSON.

Parses finding blocks from specialist output or resolved report and produces
machine-readable JSON with all metadata.

Usage:
    # Parse findings from a specialist output file
    findings-to-json.py <findings-file> [--profile strat|code]

    # Parse from stdin
    cat findings.md | findings-to-json.py - --profile strat

    # Parse and merge multiple files
    findings-to-json.py file1.md file2.md --merge

Output (stdout): JSON array of finding objects.

Exit codes:
    0  Success (findings found)
    1  Error
    2  No findings found (clean review)
"""

import argparse
import json
import re
import sys


# ---------------------------------------------------------------------------
# Finding field patterns — profile-aware
# ---------------------------------------------------------------------------

# Common fields across all profiles
COMMON_FIELDS = [
    "Finding ID", "Specialist", "Severity", "Confidence", "Title",
    "Evidence", "Recommended fix",
]

# Profile-specific fields
STRAT_FIELDS = COMMON_FIELDS + [
    "Category", "Document", "Citation", "Verdict",
]

CODE_FIELDS = COMMON_FIELDS + [
    "File", "Lines",
]

PROFILE_FIELDS = {
    "strat": STRAT_FIELDS,
    "code": CODE_FIELDS,
}


def normalize_field_name(name):
    """Convert field name to snake_case key."""
    return name.lower().replace(" ", "_").replace("-", "_")


def parse_finding_block(block, fields):
    """Parse a single finding block into a dict."""
    finding = {}
    current_field = None
    current_value_lines = []

    for line in block.split("\n"):
        line = line.strip()
        if not line:
            if current_field:
                current_value_lines.append("")
            continue

        # Check if line starts a new field
        matched = False
        for field in fields:
            pattern = rf"^{re.escape(field)}\s*:\s*(.*)$"
            m = re.match(pattern, line, re.IGNORECASE)
            if m:
                # Save previous field
                if current_field:
                    finding[normalize_field_name(current_field)] = (
                        "\n".join(current_value_lines).strip()
                    )
                current_field = field
                current_value_lines = [m.group(1).strip()]
                matched = True
                break

        if not matched and current_field:
            current_value_lines.append(line)

    # Save last field
    if current_field:
        finding[normalize_field_name(current_field)] = (
            "\n".join(current_value_lines).strip()
        )

    return finding if finding.get("finding_id") else None


def parse_findings(text, profile="strat"):
    """Parse all findings from text."""
    fields = PROFILE_FIELDS.get(profile, STRAT_FIELDS)
    findings = []

    # Split on "Finding ID:" to get individual blocks
    blocks = re.split(r"(?=Finding ID\s*:)", text)
    for block in blocks:
        block = block.strip()
        if not block or not block.startswith("Finding ID"):
            continue

        # Remove markdown code fence wrappers if present
        block = re.sub(r"^```\w*\n?", "", block)
        block = re.sub(r"\n?```$", "", block)

        finding = parse_finding_block(block, fields)
        if finding:
            findings.append(finding)

    return findings


def parse_overall_verdict(text):
    """Extract overall verdict from text."""
    m = re.search(
        r"OVERALL[_ ]VERDICT\s*:\s*(APPROVE|REVISE|REJECT)",
        text, re.IGNORECASE
    )
    if m:
        return m.group(1).upper()

    m = re.search(
        r"OVERALL\s+VERDICT\s*:\s*(Approve|Revise|Reject)",
        text
    )
    if m:
        return m.group(1).upper()

    return None


def enrich_finding(finding):
    """Add computed metadata to a finding."""
    # Severity numeric mapping
    severity_map = {"critical": 4, "important": 3, "minor": 2, "trivial": 1}
    sev = finding.get("severity", "").lower()
    finding["severity_numeric"] = severity_map.get(sev, 0)

    # Confidence numeric mapping
    conf_map = {"high": 1.0, "medium": 0.5, "low": 0.25}
    conf = finding.get("confidence", "").lower()
    finding["confidence_numeric"] = conf_map.get(conf, 0.0)

    # Extract specialist prefix from finding ID
    fid = finding.get("finding_id", "")
    m = re.match(r"([A-Z]+)-\d+", fid)
    if m:
        finding["specialist_prefix"] = m.group(1)

    # Evidence length as a quality signal
    evidence = finding.get("evidence", "")
    finding["evidence_length"] = len(evidence)

    # Citation type classification
    citation = finding.get("citation", "")
    if citation:
        if "not mentioned" in citation.lower() or "omission" in citation.lower():
            finding["citation_type"] = "omission"
        elif re.search(r"(?:section|ac|§)\s*[\d#]", citation, re.IGNORECASE):
            finding["citation_type"] = "specific"
        else:
            finding["citation_type"] = "general"

    return finding


def build_review_json(findings, verdict=None, metadata=None):
    """Build complete review JSON output."""
    # Compute summary statistics
    severity_counts = {}
    confidence_counts = {}
    category_counts = {}
    specialist_counts = {}

    for f in findings:
        sev = f.get("severity", "unknown").lower()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

        conf = f.get("confidence", "unknown").lower()
        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

        cat = f.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

        prefix = f.get("specialist_prefix", "UNK")
        specialist_counts[prefix] = specialist_counts.get(prefix, 0) + 1

    result = {
        "findings": findings,
        "summary": {
            "total_findings": len(findings),
            "by_severity": severity_counts,
            "by_confidence": confidence_counts,
            "by_category": category_counts,
            "by_specialist": specialist_counts,
        },
    }

    if verdict:
        result["overall_verdict"] = verdict

    if metadata:
        result["metadata"] = metadata

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Convert adversarial-review findings to structured JSON."
    )
    parser.add_argument(
        "files", nargs="+",
        help="Finding files to parse (use '-' for stdin)"
    )
    parser.add_argument(
        "--profile", default="strat", choices=["strat", "code"],
        help="Profile type for field detection (default: strat)"
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="Merge findings from multiple files into one output"
    )
    parser.add_argument(
        "--metadata", type=json.loads, default=None,
        help="Additional metadata JSON to include in output"
    )
    args = parser.parse_args()

    all_findings = []
    all_verdicts = []

    for filepath in args.files:
        if filepath == "-":
            text = sys.stdin.read()
        else:
            with open(filepath, encoding="utf-8") as f:
                text = f.read()

        findings = parse_findings(text, args.profile)
        for f in findings:
            enrich_finding(f)
            if not args.merge:
                f["source_file"] = filepath

        all_findings.extend(findings)

        verdict = parse_overall_verdict(text)
        if verdict:
            all_verdicts.append(verdict)

    if not all_findings:
        # Check for NO_FINDINGS_REPORTED in last processed file
        if filepath == "-":
            text_check = text
        else:
            with open(args.files[-1], encoding="utf-8") as f:
                text_check = f.read()
        if "NO_FINDINGS_REPORTED" in text_check:
            result = build_review_json([], verdict="APPROVE", metadata=args.metadata)
            json.dump(result, sys.stdout, indent=2)
            print()
            sys.exit(2)
        # No findings parsed and no explicit clean marker: still exit 2
        result = build_review_json([], metadata=args.metadata)
        json.dump(result, sys.stdout, indent=2)
        print()
        sys.exit(2)

    # Determine aggregate verdict (most conservative)
    aggregate_verdict = None
    if all_verdicts:
        if "REJECT" in all_verdicts:
            aggregate_verdict = "REJECT"
        elif "REVISE" in all_verdicts:
            aggregate_verdict = "REVISE"
        else:
            aggregate_verdict = "APPROVE"

    result = build_review_json(all_findings, aggregate_verdict, args.metadata)
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
