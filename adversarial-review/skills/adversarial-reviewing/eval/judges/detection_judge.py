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
    """Extract structured findings from the skill's output artifacts."""
    files = outputs.get("files", {})

    for _path, content in sorted(files.items()):
        if not content or not isinstance(content, str):
            continue
        parsed = _parse_findings_from_text(content)
        if parsed:
            return parsed

    stdout = outputs.get("stdout", "")
    if stdout:
        parsed = _parse_findings_from_text(stdout)
        if parsed:
            return parsed

    return []


def _parse_findings_from_text(text):
    """Parse structured findings from review report text.

    Supports two formats:
    1. Structured fields: Finding ID: X / Severity: Y / Title: Z / Evidence: W
    2. Markdown headers: ### F-001: Title / **Severity:** High / **File:** path
    """
    findings = _parse_structured_format(text)
    if not findings:
        findings = _parse_markdown_format(text)
    return findings


def _parse_structured_format(text):
    """Parse findings with explicit Finding ID / Severity / Title / Evidence fields."""
    findings = []
    finding_pattern = re.compile(
        r'Finding\s+ID:\s*(\S+).*?'
        r'Severity:\s*(Critical|Important|Minor).*?'
        r'(?:Source\s+Trust:\s*(\S+).*?)?'
        r'(?:File:\s*(.+?)(?:\n|$).*?)?'
        r'Title:\s*(.+?)(?:\n|$).*?'
        r'Evidence:\s*(.+?)(?=\nRecommend|\nVerdict|\nFinding\s+ID:|\Z)',
        re.DOTALL | re.IGNORECASE
    )
    for match in finding_pattern.finditer(text):
        findings.append({
            "finding_id": match.group(1).strip(),
            "severity": match.group(2).strip(),
            "source_trust": (match.group(3) or "").strip(),
            "file": (match.group(4) or "").strip(),
            "title": match.group(5).strip(),
            "evidence": match.group(6).strip()[:2000],
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

        sev_match = re.search(r'\*\*Severity:\*\*\s*(\w+)', body)
        severity_raw = sev_match.group(1).strip() if sev_match else "Minor"
        severity = _SEVERITY_MAP.get(severity_raw.lower(), severity_raw)

        file_match = re.search(r'\*\*File:\*\*\s*`?([^`\n]+)`?', body)
        file_path = file_match.group(1).strip() if file_match else ""
        file_path = re.sub(r':\d+[-–]\d+$|:\d+$', '', file_path)
        file_path = re.sub(r'\s*\(lines?\s+\d+[-–]\d+\)$', '', file_path)

        source_match = re.search(r'\*\*Source:\*\*\s*(\S+)', body)
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
