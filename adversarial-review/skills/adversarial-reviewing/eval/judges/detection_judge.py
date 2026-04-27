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

    metrics = compute_metrics(findings, gt_list)
    return metrics, None


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
    """Parse structured findings from review report text."""
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
