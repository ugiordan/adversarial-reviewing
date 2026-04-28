#!/usr/bin/env python3
"""Score adversarial-review findings against a ground truth corpus.

Compares structured findings (from findings-to-json.py) against a YAML
ground truth file and computes detection metrics.

Usage:
    score.py <findings.json> <ground-truth.yaml> [--output <results.json>]

Metrics computed:
    - Detection rate: true positives / total ground truth
    - False positive rate: findings not matching any ground truth / total findings
    - Severity accuracy: correct severity / total matched
    - Source trust accuracy: correct source trust / total matched (SEC only)
    - Token efficiency: detection rate / token count (if provided)

Matching algorithm:
    A finding matches a ground truth entry if ANY of these conditions hold:
    1. Same file path (exact or suffix match)
    2. Title contains any detection signal keyword
    3. Evidence contains >=2 detection signal keywords

Exit codes:
    0  Success
    1  Error
"""

import argparse
import json
import re
import sys

import yaml


def load_ground_truth(path):
    """Load and validate ground truth YAML."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data:
        return {}, []
    findings = data.get("findings", [])
    for gt in findings:
        if "detection_signals" not in gt:
            gt["detection_signals"] = []
    return data.get("metadata", {}), findings


def load_findings(path):
    """Load findings JSON (output of findings-to-json.py)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("findings", [])


def normalize_path(path):
    """Normalize file path for comparison."""
    if not path:
        return ""
    # Strip leading ./ or /
    path = re.sub(r"^[./]+", "", path)
    return path.lower()


def match_file(finding_file, gt_file):
    """Check if finding file matches ground truth file.

    Returns a match type string or None:
      "exact"     - specific file match (same file or suffix match)
      "directory" - GT is a directory prefix and finding is under it
      None        - no match
    """
    if not finding_file or not gt_file:
        return None
    f_norm = normalize_path(finding_file)
    gt_norm = normalize_path(gt_file)
    if f_norm == gt_norm:
        return "exact"
    if gt_norm.endswith("/") and f_norm.startswith(gt_norm):
        return "directory"
    if f_norm.endswith(gt_norm) and _at_path_boundary(f_norm, gt_norm):
        return "exact"
    if gt_norm.endswith(f_norm) and _at_path_boundary(gt_norm, f_norm):
        return "exact"
    return None


def _at_path_boundary(haystack, needle):
    """True if needle sits at a / boundary inside haystack."""
    pos = len(haystack) - len(needle)
    return pos == 0 or haystack[pos - 1] == "/"


def match_signals(text, signals):
    """Count how many detection signals appear in text."""
    if not text or not signals:
        return 0
    text_lower = text.lower()
    return sum(1 for s in signals if s.lower() in text_lower)


def match_finding_to_gt(finding, gt_list):
    """Try to match a finding to a ground truth entry. Returns (gt_entry, score) or (None, 0).

    Scoring:
      - Exact file match: +3
      - Directory prefix match: +1 (broad, needs signal confirmation)
      - Title signal hit: +2 per keyword
      - Evidence signal hits: +1 per keyword, only counted if >= 2 hits
        (single keyword in long evidence text is noise)

    A match requires score >= 4 AND at least one signal hit (title or
    evidence). File match alone is insufficient because different
    findings can exist in the same file.
    """
    best_match = None
    best_score = 0

    f_file = finding.get("file", "") or ""
    f_title = finding.get("title", "") or ""
    f_evidence = finding.get("evidence", "") or ""

    for gt in gt_list:
        score = 0
        gt_file = gt.get("file", "") or ""
        gt_signals = gt.get("detection_signals", [])

        file_type = match_file(f_file, gt_file)
        if file_type == "exact":
            score += 3
        elif file_type == "directory":
            score += 1

        title_hits = match_signals(f_title, gt_signals)
        score += title_hits * 2

        evidence_hits = match_signals(f_evidence, gt_signals)
        if evidence_hits >= 2:
            score += evidence_hits

        has_signal = title_hits > 0 or evidence_hits >= 2
        if score >= 4 and has_signal and score > best_score:
            best_score = score
            best_match = gt

    return best_match, best_score


def compute_metrics(findings, gt_list, token_count=None, quick_mode=False):
    """Compute all evaluation metrics.

    If quick_mode is True, GT entries with a scope_note field are excluded
    from the active set (they reference files outside the --quick scope
    and are expected misses).
    """
    gt_active = [g for g in gt_list if not g.get("duplicate_of")]
    if quick_mode:
        gt_active = [g for g in gt_active if not g.get("scope_note")]
    gt_ids = {g["id"] for g in gt_active}

    matched_gt = {}  # gt_id -> (finding, score)
    false_positives = []
    duplicate_detections = []
    severity_correct = 0
    severity_total = 0
    source_trust_correct = 0
    source_trust_total = 0

    for finding in findings:
        gt_match, score = match_finding_to_gt(finding, gt_active)
        if gt_match:
            gt_id = gt_match["id"]
            if gt_id not in matched_gt or score > matched_gt[gt_id][1]:
                if gt_id in matched_gt:
                    displaced = matched_gt[gt_id][0]
                    duplicate_detections.append(displaced)
                matched_gt[gt_id] = (finding, score)
            else:
                duplicate_detections.append(finding)
        else:
            false_positives.append({
                "finding_id": finding.get("finding_id", "unknown"),
                "title": finding.get("title", ""),
                "severity": finding.get("severity", ""),
                "file": finding.get("file", ""),
            })

    # Compute severity and source trust accuracy for matches
    for gt_id, (finding, _score) in matched_gt.items():
        gt_entry = next(g for g in gt_active if g["id"] == gt_id)

        # Severity accuracy
        f_sev = finding.get("severity", "").lower()
        gt_sev = gt_entry.get("severity", "").lower()
        if f_sev and gt_sev:
            severity_total += 1
            if f_sev == gt_sev:
                severity_correct += 1

        # Source trust accuracy (SEC findings only)
        f_st = finding.get("source_trust", "").lower()
        gt_st = gt_entry.get("source_trust", "").lower()
        if f_st and gt_st:
            source_trust_total += 1
            if f_st == gt_st:
                source_trust_correct += 1

    # Detected and missed
    detected_ids = set(matched_gt.keys())
    missed_ids = gt_ids - detected_ids
    missed = [g for g in gt_active if g["id"] in missed_ids]

    total_gt = len(gt_active)
    total_findings = len(findings)
    true_positives = len(detected_ids)
    fp_count = len(false_positives)

    metrics = {
        "detection_rate": true_positives / total_gt if total_gt > 0 else 0.0,
        "true_positives": true_positives,
        "false_positives": fp_count,
        "false_positive_rate": fp_count / total_findings if total_findings > 0 else 0.0,
        "total_ground_truth": total_gt,
        "total_findings": total_findings,
        "severity_accuracy": severity_correct / severity_total if severity_total > 0 else 0.0,
        "severity_correct": severity_correct,
        "severity_total": severity_total,
        "source_trust_accuracy": source_trust_correct / source_trust_total if source_trust_total > 0 else 0.0,
        "source_trust_correct": source_trust_correct,
        "source_trust_total": source_trust_total,
        "duplicate_detections": len(duplicate_detections),
        "detected": sorted(detected_ids),
        "missed": [{"id": m["id"], "severity": m.get("severity", ""),
                     "category": m.get("category", ""), "title": m.get("title", "")}
                    for m in missed],
        "false_positive_details": false_positives,
    }

    if token_count is not None and token_count > 0:
        metrics["token_count"] = token_count
        metrics["token_efficiency"] = true_positives / token_count * 1000  # detections per 1K tokens

    return metrics


def print_report(metrics):
    """Print human-readable scoring report."""
    dr = metrics["detection_rate"]
    tp = metrics["true_positives"]
    gt = metrics["total_ground_truth"]
    fp = metrics["false_positives"]
    tf = metrics["total_findings"]
    fpr = metrics["false_positive_rate"]
    sa = metrics["severity_accuracy"]
    sta = metrics["source_trust_accuracy"]

    print("=" * 60)
    print("IR Experiment Scoring Report")
    print("=" * 60)
    print(f"Detection rate:      {dr:.1%} ({tp}/{gt} ground truth found)")
    print(f"False positive rate: {fpr:.1%} ({fp}/{tf} findings unmatched)")
    print(f"Severity accuracy:   {sa:.1%} ({metrics['severity_correct']}/{metrics['severity_total']})")
    print(f"Source trust acc:    {sta:.1%} ({metrics['source_trust_correct']}/{metrics['source_trust_total']})")

    if "token_count" in metrics:
        print(f"Token count:         {metrics['token_count']:,}")
        print(f"Token efficiency:    {metrics['token_efficiency']:.2f} detections/1K tokens")

    if metrics["missed"]:
        print(f"\nMissed findings ({len(metrics['missed'])}):")
        for m in metrics["missed"]:
            print(f"  [{m['severity']}] {m['id']}: {m['title']}")

    if metrics["false_positive_details"]:
        print(f"\nFalse positives ({len(metrics['false_positive_details'])}):")
        for fp_item in metrics["false_positive_details"][:10]:  # cap at 10
            print(f"  {fp_item['finding_id']}: {fp_item['title'][:80]}")
        if len(metrics["false_positive_details"]) > 10:
            print(f"  ... and {len(metrics['false_positive_details']) - 10} more")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Score adversarial-review findings against ground truth."
    )
    parser.add_argument("findings", help="Path to findings JSON (from findings-to-json.py)")
    parser.add_argument("ground_truth", help="Path to ground truth YAML")
    parser.add_argument("--output", "-o", help="Write results JSON to file")
    parser.add_argument("--tokens", type=int, help="Token count for efficiency calculation")
    parser.add_argument("--run-id", help="Run identifier for tracking")
    parser.add_argument("--representation", help="IR representation label (R0-R5)")
    parser.add_argument("--model", help="Model used")
    parser.add_argument("--quiet", "-q", action="store_true", help="JSON output only")
    args = parser.parse_args()

    try:
        _metadata, gt_list = load_ground_truth(args.ground_truth)
        findings = load_findings(args.findings)
    except (FileNotFoundError, yaml.YAMLError, json.JSONDecodeError) as e:
        print(f"Error loading input: {e}", file=sys.stderr)
        sys.exit(1)

    metrics = compute_metrics(findings, gt_list, args.tokens)

    # Add run metadata
    if args.run_id:
        metrics["run_id"] = args.run_id
    if args.representation:
        metrics["representation"] = args.representation
    if args.model:
        metrics["model"] = args.model

    if not args.quiet:
        print_report(metrics)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        if not args.quiet:
            print(f"\nResults written to {args.output}")
    elif args.quiet:
        json.dump(metrics, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
