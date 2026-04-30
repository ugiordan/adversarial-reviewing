#!/usr/bin/env python3
"""Validate adversarial review findings against schema and severity ceiling rules.

Each finding must have required fields with correct formats. Severity is
constrained by the source trust level: a finding from an Internal source
cannot be rated Critical because the threat surface doesn't support it.

Subcommands:
    validate <file>           Validate findings in a single file (exit 0/1)
    schema                    Print the validation schema as JSON
    batch-validate <glob>     Validate multiple files matching a glob pattern

Exit codes:
    0  All findings valid (or schema printed)
    1  Validation errors found or runtime error
"""

import argparse
import glob as glob_module
import json
import re
import sys
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ["finding_id", "severity", "source_trust", "file", "title", "evidence"]

VALID_SEVERITIES = ["Critical", "Important", "Minor"]

# CORR-004: Common aliases that map to canonical severity values.
# Agents or constraints may use these labels. Normalize before validation.
SEVERITY_ALIASES: Dict[str, str] = {
    "High": "Important",
    "Moderate": "Minor",
}

VALID_SOURCE_TRUST = ["External", "Authenticated", "Privileged", "Internal", "N/A"]

FINDING_ID_PATTERN = r"^[A-Z]+-\d{3}$"

SEVERITY_CEILING: Dict[str, str] = {
    "External": "Critical",
    "Authenticated": "Critical",
    "Privileged": "Important",
    "Internal": "Minor",
    "N/A": "Critical",
}

SEVERITY_ORDER: Dict[str, int] = {
    "Critical": 3,
    "Important": 2,
    "Minor": 1,
}


# ---------------------------------------------------------------------------
# Field name mapping (markdown label -> dict key)
# ---------------------------------------------------------------------------

FIELD_LABELS = {
    "Finding ID": "finding_id",
    "Severity": "severity",
    "Source Trust": "source_trust",
    "File": "file",
    "Title": "title",
    "Evidence": "evidence",
}

# Reverse: dict key -> markdown label (for error messages)
KEY_TO_LABEL = {v: k for k, v in FIELD_LABELS.items()}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_finding(finding: dict) -> Tuple[bool, List[str]]:
    """Validate a single finding dict.

    Returns (ok, errors) where ok is True if the finding passes all checks,
    and errors is a list of human-readable error strings.
    """
    errors: List[str] = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        value = finding.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            label = KEY_TO_LABEL.get(field, field)
            errors.append(f"Missing or empty required field: {field} ({label})")

    # If critical fields are missing, skip further validation
    fid = finding.get("finding_id", "")
    severity = finding.get("severity", "")
    source_trust = finding.get("source_trust", "")

    # CORR-004: Normalize severity aliases to canonical values before validation
    if severity in SEVERITY_ALIASES:
        severity = SEVERITY_ALIASES[severity]
        finding["severity"] = severity

    # Validate finding_id format
    if fid and not re.match(FINDING_ID_PATTERN, fid):
        errors.append(
            f"Invalid finding_id format: '{fid}'. "
            f"Must match {FINDING_ID_PATTERN} (e.g., SEC-001)"
        )

    # Validate severity enum
    if severity and severity not in VALID_SEVERITIES:
        errors.append(
            f"Invalid severity: '{severity}'. "
            f"Must be one of: {', '.join(VALID_SEVERITIES)}"
        )

    # Validate source_trust enum
    if source_trust and source_trust not in VALID_SOURCE_TRUST:
        errors.append(
            f"Invalid source_trust: '{source_trust}'. "
            f"Must be one of: {', '.join(VALID_SOURCE_TRUST)}"
        )

    # Severity ceiling enforcement
    if (
        severity in VALID_SEVERITIES
        and source_trust in SEVERITY_CEILING
    ):
        ceiling = SEVERITY_CEILING[source_trust]
        if SEVERITY_ORDER.get(severity, 0) > SEVERITY_ORDER.get(ceiling, 0):
            errors.append(
                f"Severity '{severity}' exceeds ceiling for source_trust "
                f"'{source_trust}' (max: {ceiling})"
            )

    ok = len(errors) == 0
    return ok, errors


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_findings(text: str) -> List[dict]:
    """Parse structured findings from markdown text.

    Expects findings formatted as:
        Finding ID: SEC-001
        Severity: Critical
        Source Trust: External
        File: cmd/main.go
        Title: SQL injection
        Evidence: Unsanitized input at line 42

    Returns a list of finding dicts with snake_case keys.
    """
    findings: List[dict] = []

    # Split on "Finding ID:" to isolate each finding block
    blocks = re.split(r"(?=(?:^|\n)\s*Finding ID\s*:)", text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if not re.search(r"Finding ID\s*:", block):
            continue

        finding = _parse_block(block)
        if finding and finding.get("finding_id"):
            findings.append(finding)

    return findings


def _parse_block(block: str) -> dict:
    """Parse a single finding block into a dict with snake_case keys."""
    finding: dict = {}
    current_key = None
    current_lines: List[str] = []

    for line in block.split("\n"):
        stripped = line.strip()

        matched = False
        for label, key in FIELD_LABELS.items():
            pattern = rf"^{re.escape(label)}\s*:\s*(.*)$"
            m = re.match(pattern, stripped, re.IGNORECASE)
            if m:
                # Save previous field
                if current_key is not None:
                    finding[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = [m.group(1).strip()]
                matched = True
                break

        if not matched and current_key is not None:
            # Continuation line for multi-line field values
            current_lines.append(stripped)

    # Save last field
    if current_key is not None:
        finding[current_key] = "\n".join(current_lines).strip()

    return finding


# ---------------------------------------------------------------------------
# File validation
# ---------------------------------------------------------------------------

def validate_file(path: str) -> dict:
    """Validate all findings in a file.

    Returns a summary dict with keys:
        valid (bool): True if all findings pass validation
        total (int): Number of findings parsed
        errors (int): Number of findings with errors
        details (list): Per-finding validation results
        error (str, optional): File-level error message
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return {"valid": False, "total": 0, "errors": 0, "details": [], "error": f"File not found: {path}"}
    except OSError as e:
        return {"valid": False, "total": 0, "errors": 0, "details": [], "error": str(e)}

    findings = parse_findings(text)
    if not findings:
        return {"valid": True, "total": 0, "errors": 0, "details": []}

    details = []
    error_count = 0

    for finding in findings:
        ok, errs = validate_finding(finding)
        fid = finding.get("finding_id", "unknown")
        details.append({
            "finding_id": fid,
            "valid": ok,
            "errors": errs,
        })
        if not ok:
            error_count += 1

    return {
        "valid": error_count == 0,
        "total": len(findings),
        "errors": error_count,
        "details": details,
    }


# ---------------------------------------------------------------------------
# Schema output
# ---------------------------------------------------------------------------

def get_schema() -> dict:
    """Return the validation schema as a serializable dict."""
    return {
        "required_fields": REQUIRED_FIELDS,
        "finding_id_pattern": FINDING_ID_PATTERN,
        "valid_severities": VALID_SEVERITIES,
        "valid_source_trust": VALID_SOURCE_TRUST,
        "severity_ceiling": SEVERITY_CEILING,
        "severity_order": SEVERITY_ORDER,
    }


# ---------------------------------------------------------------------------
# CLI subcommands
# ---------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a single findings file. Exit 0 if valid, 1 if errors."""
    result = validate_file(args.file)

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))

    if not result["valid"]:
        return 1
    return 0


def cmd_schema(_args: argparse.Namespace) -> int:
    """Print the validation schema as JSON."""
    print(json.dumps(get_schema(), indent=2))
    return 0


def cmd_batch_validate(args: argparse.Namespace) -> int:
    """Validate multiple files matching a glob pattern."""
    files = sorted(glob_module.glob(args.pattern, recursive=True))
    if not files:
        print(f"No files matched pattern: {args.pattern}", file=sys.stderr)
        return 1

    all_valid = True
    summary = []

    for path in files:
        result = validate_file(path)
        result["file"] = path
        summary.append(result)
        if not result["valid"]:
            all_valid = False

    output = {
        "files_checked": len(files),
        "all_valid": all_valid,
        "results": summary,
    }
    print(json.dumps(output, indent=2))

    return 0 if all_valid else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate adversarial review findings against schema.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    p_validate = subparsers.add_parser(
        "validate",
        help="Validate findings in a single file (exit 0 if valid, 1 if errors)",
    )
    p_validate.add_argument("file", help="Path to findings markdown file")

    # schema
    subparsers.add_parser(
        "schema",
        help="Print the validation schema as JSON",
    )

    # batch-validate
    p_batch = subparsers.add_parser(
        "batch-validate",
        help="Validate multiple files matching a glob pattern",
    )
    p_batch.add_argument("pattern", help="Glob pattern for files to validate")

    args = parser.parse_args()

    if args.command == "validate":
        return cmd_validate(args)
    elif args.command == "schema":
        return cmd_schema(args)
    elif args.command == "batch-validate":
        return cmd_batch_validate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
