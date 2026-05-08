"""PostToolUse hook: validates structural requirements of agent output."""
from __future__ import annotations

import json
import re
import sys

_FINDING_PATTERN = re.compile(
    r"^###\s+\w+-\d+.*$", re.MULTILINE
)
_SEVERITY_PATTERN = re.compile(
    r"\*\*Severity[:*]*\s*(Critical|Important|Minor)", re.IGNORECASE
)
_CONFIDENCE_PATTERN = re.compile(
    r"\*\*Confidence[:*]*\s*(High|Medium|Low)", re.IGNORECASE
)
_EVIDENCE_PATTERN = re.compile(
    r"\*\*Evidence[:*]*", re.IGNORECASE
)
_NO_FINDINGS_PATTERN = re.compile(r"NO_FINDINGS_REPORTED")

_COMPARATIVE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bhowever\b",
        r"\balternatively\b",
        r"\bon the other hand\b",
        r"\bcould also be\b",
        r"\bcompared to\b",
        r"\bcounter-?argument\b",
        r"\bnot necessarily\b",
        r"\bmight not be\b",
        r"\bcould be interpreted\b",
        r"\bfalse positive\b",
    ]
]


def check_finding_structure(output: str) -> dict:
    if _NO_FINDINGS_PATTERN.search(output):
        return {"has_findings": False, "valid_no_findings": True, "count": 0}
    findings = _FINDING_PATTERN.findall(output)
    has_severity = bool(_SEVERITY_PATTERN.search(output))
    has_confidence = bool(_CONFIDENCE_PATTERN.search(output))
    has_evidence = bool(_EVIDENCE_PATTERN.search(output))
    return {
        "has_findings": len(findings) > 0,
        "valid_no_findings": False,
        "count": len(findings),
        "has_severity": has_severity,
        "has_confidence": has_confidence,
        "has_evidence": has_evidence,
    }


def check_comparative_reasoning(output: str) -> dict:
    for pattern in _COMPARATIVE_PATTERNS:
        if pattern.search(output):
            return {"has_comparative": True}
    return {"has_comparative": False}


if __name__ == "__main__":
    hook_input = json.loads(sys.stdin.read())
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Agent":
        sys.exit(0)

    tool_output = hook_input.get("tool_output", "")
    structure = check_finding_structure(tool_output)
    comparative = check_comparative_reasoning(tool_output)

    warnings = []
    if not structure["has_findings"] and not structure.get("valid_no_findings"):
        warnings.append("No finding template or NO_FINDINGS_REPORTED marker found")
    if structure["has_findings"] and not comparative["has_comparative"]:
        warnings.append("No comparative reasoning detected in findings")

    if warnings:
        print(json.dumps({
            "warnings": warnings,
            "structure": structure,
            "comparative": comparative,
        }), file=sys.stderr)
