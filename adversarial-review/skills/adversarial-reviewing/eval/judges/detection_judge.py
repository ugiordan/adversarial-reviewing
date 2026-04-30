#!/usr/bin/env python3
"""External code judge for agent-eval-harness.

Scores adversarial-reviewing findings against a ground truth corpus.
Loaded by the harness via importlib: module=eval.judges.detection_judge,
function=score_detection.

The scorer receives the harness's outputs dict containing:
- files: dict of {relative_path: content} from collected artifacts
- case_dir: path to the case directory (contains reference.yaml)
- stdout, stderr, exit_code, etc.

Returns (score, rationale) where score is detection_rate (0.0-1.0).
"""

import re
from pathlib import Path

from eval.score import load_ground_truth, compute_metrics


def score_detection(outputs=None, **kwargs):
    """Score adversarial-reviewing output against ground truth.

    Returns (float, str) where float is the detection rate (0.0-1.0)
    and str is a human-readable rationale.
    """
    metrics, err = _run_metrics(outputs)
    if err:
        return (0.0, err)

    dr = metrics["detection_rate"]
    tp = metrics["true_positives"]
    total = metrics["total_ground_truth"]
    fp = metrics["false_positives"]
    sa = metrics["severity_accuracy"]

    rationale = (
        f"Detection: {dr:.0%} ({tp}/{total}). "
        f"FP: {fp}/{metrics['total_findings']}. "
        f"Severity accuracy: {sa:.0%}. "
        f"Missed: {', '.join(m['id'] for m in metrics['missed'][:5])}"
    )

    return (dr, rationale)


def score_false_positive_rate(outputs=None, **kwargs):
    """Complementary judge: scores false positive rate (lower is better).

    Returns (bool, str) where bool is True if FP rate is under 30%.
    """
    metrics, err = _run_metrics(outputs)
    if err:
        return (False, err) if "ground truth" in err else (True, err)

    fpr = metrics["false_positive_rate"]
    fp = metrics["false_positives"]
    total = metrics["total_findings"]

    passed = fpr < 0.30
    rationale = f"FP rate: {fpr:.0%} ({fp}/{total}). {'PASS' if passed else 'FAIL: >30%'}"
    return (passed, rationale)


def score_severity_accuracy(outputs=None, **kwargs):
    """Complementary judge: scores severity classification accuracy.

    Returns (float, str) where float is severity accuracy (0.0-1.0).
    """
    metrics, err = _run_metrics(outputs)
    if err:
        return (0.0, err)

    sa = metrics["severity_accuracy"]
    correct = metrics["severity_correct"]
    total = metrics["severity_total"]

    return (sa, f"Severity accuracy: {sa:.0%} ({correct}/{total})")


def _run_metrics(outputs):
    """Load GT and findings, compute metrics. Returns (metrics, None) or (None, error_str)."""
    outputs = outputs or {}
    case_dir = outputs.get("case_dir", "")

    gt_path = Path(case_dir) / "reference.yaml" if case_dir else None
    if not gt_path or not gt_path.exists():
        return None, "No ground truth found in case directory"

    _metadata, gt_list = load_ground_truth(str(gt_path))
    gt_active = [g for g in gt_list if not g.get("duplicate_of")]
    if not gt_active:
        return None, "No ground truth entries (all empty or duplicates)"

    findings = _extract_findings(outputs)
    if not findings:
        return None, f"No findings extracted from output. Ground truth has {len(gt_active)} entries."

    quick_mode = _detect_quick_mode(outputs)
    metrics = compute_metrics(findings, gt_list, quick_mode=quick_mode)
    return metrics, None


def _detect_quick_mode(outputs):
    """Check if the run used --quick mode by inspecting the run metadata."""
    eval_params = outputs.get("eval_params", {})
    skill_args = eval_params.get("skill_args", "")
    if "--quick" in skill_args:
        return True

    case_dir = outputs.get("case_dir", "")
    if not case_dir:
        return False
    input_path = Path(case_dir) / "input.yaml"
    if not input_path.exists():
        return False
    try:
        import yaml
        with open(input_path) as f:
            data = yaml.safe_load(f) or {}
        prompt = data.get("prompt", "")
        return "--quick" in prompt
    except Exception:
        return False


def _extract_findings(outputs):
    """Extract structured findings from ALL output artifacts."""
    files = outputs.get("files", {})
    all_findings = []

    for _path, content in sorted(files.items()):
        if not content or not isinstance(content, str):
            continue
        parsed = _parse_findings_from_text(content)
        if parsed:
            all_findings.extend(parsed)

    if all_findings:
        return all_findings

    stdout = outputs.get("stdout", "")
    if stdout:
        parsed = _parse_findings_from_text(stdout)
        if parsed:
            return parsed

    return []


def _parse_findings_from_text(text):
    """Parse structured findings from review report text.

    Supports four formats:
    1. Structured fields: Finding ID: X / Severity: Y / Title: Z / Evidence: W
    2. Markdown headers: ### F-001: Title / **Severity:** High / **File:** path
    3. Narrative consensus: ### N. Title (Severity) [AGENT-NNN + ...] / **File:** path
    4. Table rows: | SEC-001 | Medium | `path` | description |
    Tries all parsers and returns the one that found the most findings.
    """
    results = []
    for parser in [_parse_structured_format, _parse_markdown_format,
                   _parse_narrative_format, _parse_table_format]:
        parsed = parser(text)
        if parsed:
            results.append(parsed)
    if not results:
        return []
    return max(results, key=len)


def _parse_structured_format(text):
    """Parse findings with explicit Finding ID / Severity / Title / Evidence fields.

    CORR-003: Uses a per-block field extraction approach instead of a single
    monolithic regex, so optional fields (Source Trust, File) are captured
    regardless of their presence or ordering relative to each other.
    """
    findings = []
    # Split text into blocks starting with "Finding ID:"
    blocks = re.split(r'(?=Finding\s+ID:)', text)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        fid_m = re.match(r'Finding\s+ID:\s*(\S+)', block)
        if not fid_m:
            continue
        sev_m = re.search(r'Severity:\s*(Critical|Important|Minor)', block, re.IGNORECASE)
        if not sev_m:
            continue
        st_m = re.search(r'Source\s+Trust:\s*(\S+)', block)
        file_m = re.search(r'File:\s*(.+?)(?:\n|$)', block)
        title_m = re.search(r'Title:\s*(.+?)(?:\n|$)', block)
        evidence_m = re.search(
            r'Evidence:\s*(.+?)(?=\nRecommend|\nVerdict|\nFinding\s+ID:|\Z)',
            block, re.DOTALL,
        )
        if not title_m:
            continue
        findings.append({
            "finding_id": fid_m.group(1).strip(),
            "severity": sev_m.group(1).strip(),
            "source_trust": (st_m.group(1).strip() if st_m else ""),
            "file": (file_m.group(1).strip() if file_m else ""),
            "title": title_m.group(1).strip(),
            "evidence": (evidence_m.group(1).strip()[:2000] if evidence_m else ""),
        })
    return findings


_SEVERITY_MAP = {
    "critical": "Critical",
    "high": "Important",
    "medium": "Minor",
    "low": "Minor",
    "informational": "Minor",
}


def _find_dismissed_ranges(text):
    """Find character ranges for Dismissed Findings sections.

    Returns a list of (start, end) tuples. A finding whose header falls
    within any range is considered dismissed. The range ends at the next
    ## heading or end of text, so findings in subsequent sections (e.g.
    Challenge Round) are NOT dismissed.
    """
    ranges = []
    section_pattern = re.compile(r'^##\s+', re.MULTILINE)
    dismissed_pattern = re.compile(
        r'^##\s+Dismissed\s+Findings', re.MULTILINE | re.IGNORECASE)
    for m in dismissed_pattern.finditer(text):
        start = m.start()
        next_section = section_pattern.search(text, m.end())
        end = next_section.start() if next_section else len(text)
        ranges.append((start, end))
    return ranges


def _parse_markdown_format(text):
    """Parse findings from markdown report with ### F-NNN: Title headers.

    Skips findings under a "Dismissed Findings" section or with
    DISMISSED/WITHDRAWN in the title.
    """
    dismissed_ranges = _find_dismissed_ranges(text)

    findings = []
    header_pattern = re.compile(
        r'^###\s+(F-\d+|SEC-\d+):\s*(.+?)$',
        re.MULTILINE
    )
    headers = list(header_pattern.finditer(text))
    for i, match in enumerate(headers):
        if any(start <= match.start() < end for start, end in dismissed_ranges):
            continue
        finding_id = match.group(1).strip()
        title = match.group(2).strip()
        if re.search(r'\b(DISMISSED|WITHDRAWN)\b', title):
            continue
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[match.end():end]

        sev_match = re.search(r'\*\*Severity(?::\*\*|\*\*:)\s*(\w+)', body)
        if not sev_match:
            sev_match = re.search(
                r'\|\s*Severity\s*\|\s*\*{0,2}(Critical|Important|High|Medium|Minor|Low)\*{0,2}',
                body, re.IGNORECASE)
        severity_raw = sev_match.group(1).strip() if sev_match else "Minor"
        severity = _SEVERITY_MAP.get(severity_raw.lower(), severity_raw)

        file_match = re.search(r'\*\*File(?::\*\*|\*\*:)\s*`?([^`\n]+)`?', body)
        if not file_match:
            file_match = re.search(
                r'\|\s*File\s*\|\s*`?([^`|\n]+)`?\s*\|', body)
        file_path = file_match.group(1).strip() if file_match else ""
        file_path = re.sub(r':\d+[-–]\d+$|:\d+$', '', file_path)
        file_path = re.sub(r'\s*\(lines?\s+\d+[-–]\d+\)$', '', file_path)

        source_match = re.search(r'\*\*Source(?::\*\*|\*\*:)\s*(\S+)', body)
        if not source_match:
            source_match = re.search(
                r'\|\s*Source\s+Trust\s*\|\s*(\S+)', body)
        source = source_match.group(1).strip() if source_match else ""

        evidence = body.strip()[:2000]

        findings.append({
            "finding_id": finding_id,
            "severity": severity,
            "source_trust": source,
            "file": file_path,
            "title": title,
            "evidence": evidence,
        })
    return findings


def _parse_narrative_format(text):
    """Parse findings from narrative consensus reports.

    Handles formats like:
      ### 1. Title (Severity) [AGENT-NNN + ...]
      ### Title (Severity) [AGENT-NNN]
      **File:** `path/to/file.go`:123
      **Description:** ...
    """
    dismissed_ranges = _find_dismissed_ranges(text)

    findings = []
    header_pattern = re.compile(
        r'^###\s+(?:\d+\.\s+)?(.+?)\s*'
        r'\((\w+(?:/\w+)?)\)\s*'
        r'\[([A-Z]+-\d+(?:\s*\+\s*[A-Z]+-?\d*(?:\s*\([^)]*\))?)*)\]',
        re.MULTILINE
    )
    headers = list(header_pattern.finditer(text))
    if not headers:
        header_pattern = re.compile(
            r'^###\s+(?:\d+\.\s+)?(.+?)\s*'
            r'\((\w+(?:/\w+)?)\)',
            re.MULTILINE
        )
        headers = list(header_pattern.finditer(text))

    for i, match in enumerate(headers):
        if any(start <= match.start() < end for start, end in dismissed_ranges):
            continue
        title = match.group(1).strip()
        if re.search(r'\b(DISMISSED|WITHDRAWN)\b', title):
            continue

        severity_raw = match.group(2).strip()
        severity = _SEVERITY_MAP.get(severity_raw.lower(), severity_raw)
        if severity not in ("Critical", "Important", "Minor"):
            severity = _SEVERITY_MAP.get(severity_raw.split("/")[0].lower(), "Minor")

        agent_refs = match.group(3).strip() if match.lastindex >= 3 else ""
        finding_ids = re.findall(r'([A-Z]+-\d+)', agent_refs)
        finding_id = finding_ids[0] if finding_ids else f"N-{i+1:03d}"

        end_pos = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[match.end():end_pos]

        file_match = re.search(r'\*\*File(?:s?|:\*\*|\*\*:)\s*`?([^`\n,]+)`?', body)
        if not file_match:
            file_match = re.search(r'`([a-zA-Z][\w/.-]+\.\w+)`(?::\d+)?', body)
        file_path = file_match.group(1).strip() if file_match else ""
        file_path = re.sub(r':\d+[-–]\d+$|:\d+$', '', file_path)

        source_match = re.search(r'\*\*Source\s*Trust(?::\*\*|\*\*:)\s*(\S+)', body)
        source = source_match.group(1).strip() if source_match else ""

        evidence = body.strip()[:2000]

        findings.append({
            "finding_id": finding_id,
            "severity": severity,
            "source_trust": source,
            "file": file_path,
            "title": title,
            "evidence": evidence,
        })
    return findings


def _parse_table_format(text):
    """Parse findings from markdown table rows.

    Handles: | SEC-001 | Medium | `path/to/file.go`:123 | Description |
    """
    dismissed_ranges = _find_dismissed_ranges(text)

    findings = []
    row_pattern = re.compile(
        r'^\|\s*([A-Z]+-\d+)\s*\|'
        r'\s*(\w+)\s*\|'
        r'\s*(.+?)\s*\|'
        r'\s*(.+?)\s*\|',
        re.MULTILINE
    )

    for match in row_pattern.finditer(text):
        if any(start <= match.start() < end for start, end in dismissed_ranges):
            continue

        finding_id = match.group(1).strip()
        severity_raw = match.group(2).strip()
        if severity_raw.lower() in ("id", "severity", "---"):
            continue
        severity = _SEVERITY_MAP.get(severity_raw.lower(), severity_raw)
        if severity not in ("Critical", "Important", "Minor"):
            severity = _SEVERITY_MAP.get(severity_raw.split("/")[0].lower(), "Minor")

        file_path = match.group(3).strip().strip('`')
        file_path = re.sub(r':\d+[-,]\d+[-,\d]*$|:\d+$', '', file_path)

        description = match.group(4).strip()

        findings.append({
            "finding_id": finding_id,
            "severity": severity,
            "source_trust": "",
            "file": file_path,
            "title": description[:200],
            "evidence": description[:2000],
        })
    return findings
