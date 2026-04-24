#!/usr/bin/env python3
"""Normalize and canonicalize adversarial-review finding output for stability.

LLM outputs are non-deterministic. Two runs on the same code can produce
findings with slightly different wording, ordering, or formatting. This script
provides normalization and cross-run stability analysis.

Subcommands:
    normalize <findings_file>     Normalize a findings markdown file
    diff <file_a> <file_b>        Compare two finding sets for stability
    canonical-order <json_file>   Sort findings JSON into canonical order

Exit codes:
    0  Success
    1  Error
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Normalization rules
# ---------------------------------------------------------------------------

SEVERITY_CANONICAL = {
    "critical": "Critical",
    "important": "Important",
    "minor": "Minor",
    "trivial": "Trivial",
}

CONFIDENCE_CANONICAL = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

# Known specialist prefixes
KNOWN_PREFIXES = {"SEC", "PERF", "QUAL", "CORR", "ARCH"}

# Fields in canonical output order
FIELD_ORDER = [
    "Finding ID",
    "Specialist",
    "Severity",
    "Confidence",
    "Source Trust",
    "File",
    "Lines",
    "Title",
    "Evidence",
    "Recommended fix",
]


def normalize_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs to single space, normalize line endings."""
    # Normalize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of spaces/tabs (not newlines) to single space
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_file_path(path: str) -> str:
    """Strip leading ./, collapse //, use forward slashes."""
    path = path.strip()
    path = path.replace("\\", "/")
    # Collapse multiple slashes
    path = re.sub(r"/+", "/", path)
    # Strip leading ./
    path = re.sub(r"^(\./)+", "", path)
    return path


def normalize_line_range(lines_str: str) -> str:
    """Parse various line range formats to canonical 'N-M' or 'N'.

    Handles: '42-58', '42 to 58', '42', 'L42-L58', 'L42', 'lines 42-58'.
    """
    lines_str = lines_str.strip()
    # Remove 'L' prefix, 'lines' prefix
    cleaned = re.sub(r"(?i)^lines?\s*", "", lines_str)
    cleaned = cleaned.replace("L", "").replace("l", "")

    # Try range with 'to'
    m = re.match(r"(\d+)\s*(?:to|-)\s*(\d+)", cleaned)
    if m:
        start, end = int(m.group(1)), int(m.group(2))
        if start == end:
            return str(start)
        return f"{start}-{end}"

    # Single line
    m = re.match(r"(\d+)", cleaned)
    if m:
        return m.group(1)

    # Can't parse, return as-is
    return lines_str


def normalize_finding_id(fid: str) -> str:
    """Uppercase prefix, zero-padded 3-digit number. SEC-001, not sec-1."""
    fid = fid.strip()
    m = re.match(r"([A-Za-z]+)-(\d+)", fid)
    if m:
        prefix = m.group(1).upper()
        number = int(m.group(2))
        return f"{prefix}-{number:03d}"
    return fid


def normalize_severity(value: str) -> str:
    """Title case severity."""
    return SEVERITY_CANONICAL.get(value.strip().lower(), value.strip())


def normalize_confidence(value: str) -> str:
    """Title case confidence."""
    return CONFIDENCE_CANONICAL.get(value.strip().lower(), value.strip())


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_finding_block(block: str) -> Optional[Dict[str, str]]:
    """Parse a single finding block into a dict with raw field values."""
    finding: Dict[str, str] = {}
    current_field: Optional[str] = None
    current_value_lines: List[str] = []

    for line in block.split("\n"):
        stripped = line.strip()

        matched = False
        for field in FIELD_ORDER:
            pattern = rf"^{re.escape(field)}\s*:\s*(.*)$"
            m = re.match(pattern, stripped, re.IGNORECASE)
            if m:
                if current_field:
                    finding[current_field] = "\n".join(current_value_lines).strip()
                current_field = field
                current_value_lines = [m.group(1).strip()]
                matched = True
                break

        if not matched and current_field:
            current_value_lines.append(stripped)
        elif not matched and not current_field and stripped:
            # Skip lines before the first field
            pass

    if current_field:
        finding[current_field] = "\n".join(current_value_lines).strip()

    return finding if finding.get("Finding ID") else None


def parse_findings_from_markdown(text: str) -> List[Dict[str, str]]:
    """Parse all finding blocks from markdown text."""
    findings = []
    blocks = re.split(r"(?=Finding ID\s*:)", text)
    for block in blocks:
        block = block.strip()
        if not block or not re.match(r"Finding ID\s*:", block):
            continue
        # Strip code fences
        block = re.sub(r"^```\w*\n?", "", block)
        block = re.sub(r"\n?```$", "", block)
        finding = parse_finding_block(block)
        if finding:
            findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_finding(finding: Dict[str, str]) -> Dict[str, str]:
    """Apply all normalization rules to a parsed finding."""
    normalized: Dict[str, str] = {}

    for field in FIELD_ORDER:
        value = finding.get(field, "")
        if not value:
            continue

        if field == "Finding ID":
            value = normalize_finding_id(value)
        elif field == "Severity":
            value = normalize_severity(value)
        elif field == "Confidence":
            value = normalize_confidence(value)
        elif field == "File":
            value = normalize_file_path(value)
        elif field == "Lines":
            value = normalize_line_range(value)
        elif field in ("Evidence", "Recommended fix", "Title"):
            value = normalize_whitespace(value)
        else:
            value = value.strip()

        normalized[field] = value

    return normalized


def finding_sort_key(finding: Dict[str, str]) -> Tuple[str, str, int]:
    """Sort key: (prefix, file_path, start_line)."""
    fid = finding.get("Finding ID", "")
    m = re.match(r"([A-Z]+)-", fid)
    prefix = m.group(1) if m else "ZZZ"

    file_path = finding.get("File", "")

    lines_str = finding.get("Lines", "0")
    m = re.match(r"(\d+)", lines_str)
    start_line = int(m.group(1)) if m else 0

    return (prefix, file_path, start_line)


def format_finding_markdown(finding: Dict[str, str]) -> str:
    """Render a normalized finding as markdown."""
    lines = []
    for field in FIELD_ORDER:
        value = finding.get(field, "")
        if value:
            lines.append(f"{field}: {value}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fingerprinting (for diff matching)
# ---------------------------------------------------------------------------

def line_bucket(lines_str: str, bucket_size: int = 10) -> int:
    """Bucket line numbers for fuzzy matching."""
    m = re.match(r"(\d+)", lines_str)
    if m:
        return int(m.group(1)) // bucket_size
    return 0


def finding_fingerprint(finding: Dict[str, str]) -> str:
    """Generate fingerprint: prefix + file + line_bucket.

    Intentionally excludes title text because LLM rewording across runs
    makes title-based matching unreliable. Title similarity is computed
    separately during matching to break ties when multiple findings share
    the same prefix/file/bucket.
    """
    fid = finding.get("Finding ID", "")
    m = re.match(r"([A-Z]+)-", fid)
    prefix = m.group(1) if m else "UNK"

    file_path = finding.get("File", "").lower()
    bucket = line_bucket(finding.get("Lines", "0"))

    return f"{prefix}|{file_path}|{bucket}"


# ---------------------------------------------------------------------------
# Text similarity
# ---------------------------------------------------------------------------

def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity on word sets."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a and not words_b:
        return 1.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) if union else 1.0


# ---------------------------------------------------------------------------
# Subcommand: normalize
# ---------------------------------------------------------------------------

def cmd_normalize(args: argparse.Namespace) -> int:
    """Read a findings markdown file and output normalized version."""
    try:
        if args.findings_file == "-":
            text = sys.stdin.read()
        else:
            with open(args.findings_file, encoding="utf-8") as f:
                text = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {args.findings_file}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    findings = parse_findings_from_markdown(text)
    if not findings:
        if "NO_FINDINGS_REPORTED" in text:
            print("NO_FINDINGS_REPORTED")
            return 0
        print("Error: no findings found in input", file=sys.stderr)
        return 1

    normalized = [normalize_finding(f) for f in findings]
    normalized.sort(key=finding_sort_key)

    output_blocks = [format_finding_markdown(f) for f in normalized]
    print("\n\n".join(output_blocks))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: diff
# ---------------------------------------------------------------------------

def match_findings(
    findings_a: List[Dict[str, str]],
    findings_b: List[Dict[str, str]],
) -> Tuple[
    List[Tuple[Dict[str, str], Dict[str, str]]],
    List[Dict[str, str]],
    List[Dict[str, str]],
]:
    """Match findings by fingerprint. Returns (matched, a_only, b_only).

    When multiple findings share the same fingerprint (same specialist prefix,
    file, line bucket), uses title similarity as a tiebreaker to pick the
    best match.
    """
    fp_a = {i: finding_fingerprint(f) for i, f in enumerate(findings_a)}
    fp_b = {i: finding_fingerprint(f) for i, f in enumerate(findings_b)}

    # Build index from fingerprint to finding indices
    b_by_fp: Dict[str, List[int]] = {}
    for i, fp in fp_b.items():
        b_by_fp.setdefault(fp, []).append(i)

    matched: List[Tuple[Dict[str, str], Dict[str, str]]] = []
    matched_a_indices: set = set()
    matched_b_indices: set = set()

    for i, fp in fp_a.items():
        if fp not in b_by_fp:
            continue
        # Find best match by title similarity among candidates
        candidates = [j for j in b_by_fp[fp] if j not in matched_b_indices]
        if not candidates:
            continue
        best_j = max(
            candidates,
            key=lambda j: jaccard_similarity(
                findings_a[i].get("Title", ""),
                findings_b[j].get("Title", ""),
            ),
        )
        matched.append((findings_a[i], findings_b[best_j]))
        matched_a_indices.add(i)
        matched_b_indices.add(best_j)

    a_only = [findings_a[i] for i in range(len(findings_a)) if i not in matched_a_indices]
    b_only = [findings_b[i] for i in range(len(findings_b)) if i not in matched_b_indices]

    return matched, a_only, b_only


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare two normalized finding sets and report stability metrics."""
    try:
        with open(args.file_a, encoding="utf-8") as f:
            text_a = f.read()
        with open(args.file_b, encoding="utf-8") as f:
            text_b = f.read()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    findings_a = [normalize_finding(f) for f in parse_findings_from_markdown(text_a)]
    findings_b = [normalize_finding(f) for f in parse_findings_from_markdown(text_b)]

    if not findings_a and not findings_b:
        result = {
            "stability_score": 1.0,
            "matched_findings": 0,
            "unmatched_a_only": 0,
            "unmatched_b_only": 0,
            "field_stability": {},
            "details": [],
        }
        json.dump(result, sys.stdout, indent=2)
        print()
        return 0

    matched, a_only, b_only = match_findings(findings_a, findings_b)

    total_unique = len(matched) + len(a_only) + len(b_only)
    stability_score = len(matched) / total_unique if total_unique else 1.0

    # Field stability for matched findings
    severity_match = 0
    confidence_match = 0
    title_sim_total = 0.0
    evidence_sim_total = 0.0
    n_matched = len(matched)

    details: List[Dict[str, Any]] = []

    for fa, fb in matched:
        sev_same = fa.get("Severity", "") == fb.get("Severity", "")
        conf_same = fa.get("Confidence", "") == fb.get("Confidence", "")
        title_sim = jaccard_similarity(
            fa.get("Title", ""), fb.get("Title", "")
        )
        evidence_sim = jaccard_similarity(
            fa.get("Evidence", ""), fb.get("Evidence", "")
        )

        if sev_same:
            severity_match += 1
        if conf_same:
            confidence_match += 1
        title_sim_total += title_sim
        evidence_sim_total += evidence_sim

        details.append({
            "id_a": fa.get("Finding ID", ""),
            "id_b": fb.get("Finding ID", ""),
            "fingerprint": finding_fingerprint(fa),
            "severity_match": sev_same,
            "confidence_match": conf_same,
            "title_similarity": round(title_sim, 3),
            "evidence_similarity": round(evidence_sim, 3),
        })

    for f in a_only:
        details.append({
            "id_a": f.get("Finding ID", ""),
            "id_b": None,
            "fingerprint": finding_fingerprint(f),
            "status": "a_only",
        })

    for f in b_only:
        details.append({
            "id_a": None,
            "id_b": f.get("Finding ID", ""),
            "fingerprint": finding_fingerprint(f),
            "status": "b_only",
        })

    field_stability: Dict[str, float] = {}
    if n_matched > 0:
        field_stability = {
            "severity": round(severity_match / n_matched, 3),
            "confidence": round(confidence_match / n_matched, 3),
            "title": round(title_sim_total / n_matched, 3),
            "evidence": round(evidence_sim_total / n_matched, 3),
        }

    result: Dict[str, Any] = {
        "stability_score": round(stability_score, 3),
        "matched_findings": n_matched,
        "unmatched_a_only": len(a_only),
        "unmatched_b_only": len(b_only),
        "field_stability": field_stability,
        "details": details,
    }

    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


# ---------------------------------------------------------------------------
# Subcommand: canonical-order
# ---------------------------------------------------------------------------

def finding_json_sort_key(finding: Dict[str, Any]) -> Tuple[str, str, int]:
    """Sort key for JSON findings: (prefix, file, start_line)."""
    prefix = finding.get("specialist_prefix", "")
    if not prefix:
        fid = finding.get("finding_id", "")
        m = re.match(r"([A-Z]+)-", fid)
        prefix = m.group(1) if m else "ZZZ"

    file_path = finding.get("file", "")

    lines_str = finding.get("lines", "0")
    m = re.match(r"(\d+)", str(lines_str))
    start_line = int(m.group(1)) if m else 0

    return (prefix, file_path, start_line)


def cmd_canonical_order(args: argparse.Namespace) -> int:
    """Read findings JSON and output with canonical ordering."""
    try:
        if args.findings_json == "-":
            data = json.load(sys.stdin)
        else:
            with open(args.findings_json, encoding="utf-8") as f:
                data = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {args.findings_json}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    # Handle both raw list and wrapped object formats
    if isinstance(data, list):
        findings = data
        wrapper = None
    elif isinstance(data, dict) and "findings" in data:
        findings = data["findings"]
        wrapper = data
    else:
        print("Error: expected JSON array or object with 'findings' key", file=sys.stderr)
        return 1

    # Normalize fields in each finding before sorting
    for f in findings:
        if "finding_id" in f:
            f["finding_id"] = normalize_finding_id(f["finding_id"])
        if "severity" in f:
            f["severity"] = normalize_severity(f["severity"])
        if "confidence" in f:
            f["confidence"] = normalize_confidence(f["confidence"])
        if "file" in f:
            f["file"] = normalize_file_path(f["file"])
        if "lines" in f:
            f["lines"] = normalize_line_range(str(f["lines"]))
        # Re-derive specialist_prefix from normalized ID
        if "finding_id" in f:
            m = re.match(r"([A-Z]+)-", f["finding_id"])
            if m:
                f["specialist_prefix"] = m.group(1)

    findings.sort(key=finding_json_sort_key)

    if wrapper is not None:
        wrapper["findings"] = findings
        json.dump(wrapper, sys.stdout, indent=2)
    else:
        json.dump(findings, sys.stdout, indent=2)

    print()
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize and canonicalize adversarial-review finding output.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # normalize
    p_norm = subparsers.add_parser(
        "normalize",
        help="Normalize a findings markdown file",
    )
    p_norm.add_argument(
        "findings_file",
        help="Path to findings markdown file (use '-' for stdin)",
    )

    # diff
    p_diff = subparsers.add_parser(
        "diff",
        help="Compare two finding sets for stability metrics",
    )
    p_diff.add_argument("file_a", help="First findings file")
    p_diff.add_argument("file_b", help="Second findings file")

    # canonical-order
    p_canon = subparsers.add_parser(
        "canonical-order",
        help="Sort findings JSON into canonical order",
    )
    p_canon.add_argument(
        "findings_json",
        help="Path to findings JSON file (use '-' for stdin)",
    )

    args = parser.parse_args()

    if args.command == "normalize":
        return cmd_normalize(args)
    elif args.command == "diff":
        return cmd_diff(args)
    elif args.command == "canonical-order":
        return cmd_canonical_order(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
