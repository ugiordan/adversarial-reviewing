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

import json
import os
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

    Returns (bool, str) where bool is True if FP rate is under 20%.
    """
    metrics, err = _run_metrics(outputs)
    if err:
        return (False, err) if "ground truth" in err.lower() else (True, err)

    fpr = metrics["false_positive_rate"]
    fp = metrics["false_positives"]
    total = metrics["total_findings"]

    passed = fpr < 0.20
    rationale = f"FP rate: {fpr:.0%} ({fp}/{total}). {'PASS' if passed else 'FAIL: >20%'}"
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


def score_evidence_quality(outputs=None, **kwargs):
    """Judge: verify findings cite real file paths that exist in the source.

    Returns (float, str) where float is percentage of findings with valid citations.
    """
    outputs = outputs or {}
    findings = _extract_findings(outputs)
    if not findings:
        return (1.0, "No findings to check")

    case_dir = outputs.get("case_dir", "")
    eval_params = outputs.get("eval_params", {})
    skill_args = eval_params.get("skill_args", "")

    source_root = ""
    for arg in skill_args.split():
        if os.path.isdir(arg):
            source_root = arg
            break

    if not source_root:
        return (1.0, "Cannot verify: source root not found in args")

    valid = 0
    invalid = []
    for f in findings:
        file_path = f.get("file", "")
        if not file_path:
            invalid.append(f.get("finding_id", "?") + ": no file cited")
            continue

        full = os.path.join(source_root, file_path)
        if os.path.isfile(full) or os.path.isdir(full.rstrip("/")):
            valid += 1
        else:
            if os.path.isfile(file_path):
                valid += 1
            else:
                invalid.append(f.get("finding_id", "?") + f": {file_path}")

    rate = valid / len(findings) if findings else 1.0
    detail = f"Evidence quality: {rate:.0%} ({valid}/{len(findings)} valid paths)"
    if invalid:
        detail += f". Invalid: {', '.join(invalid[:5])}"
    return (rate, detail)


def score_cost_efficiency(outputs=None, **kwargs):
    """Judge: cost per detected finding.

    Returns (float, str) where float is cost per finding (lower is better).
    """
    metrics, err = _run_metrics(outputs)
    outputs = outputs or {}
    cost = outputs.get("cost_usd", 0)
    if not cost:
        return (0.0, "Cost not tracked")

    if err or not metrics:
        return (cost, f"Total cost: ${cost:.2f}, no findings to divide by")

    tp = metrics.get("true_positives", 0)
    if tp == 0:
        return (cost, f"Total cost: ${cost:.2f}, 0 detections")

    cost_per = cost / tp
    total = metrics.get("total_findings", 0)
    return (cost_per, f"${cost_per:.2f}/finding ({tp} detections, ${cost:.2f} total, {total} raw findings)")


def _run_metrics(outputs):
    """Load GT and findings, compute metrics. Returns (metrics, None) or (None, error_str)."""
    outputs = outputs or {}
    case_dir = outputs.get("case_dir", "")

    gt_path = Path(case_dir) / "reference.yaml" if case_dir else None
    if not gt_path or not gt_path.exists():
        case_name = Path(case_dir).name if case_dir else ""
        if case_name:
            eval_dir = Path(__file__).resolve().parent.parent
            candidate = eval_dir / "dataset" / "cases" / case_name / "reference.yaml"
            if candidate.exists():
                gt_path = candidate
    if not gt_path or not gt_path.exists():
        return None, "No ground truth found in case directory"

    _metadata, gt_list = load_ground_truth(str(gt_path))
    gt_active = [g for g in gt_list if not g.get("duplicate_of")]
    if not gt_active:
        return None, "No ground truth entries (all empty or duplicates)"

    if not outputs.get("stdout") and not outputs.get("files") and case_dir:
        stdout_path = Path(case_dir) / "stdout.log"
        if stdout_path.exists():
            try:
                outputs = dict(outputs)
                outputs["stdout"] = stdout_path.read_text()
            except (OSError, UnicodeDecodeError):
                pass

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


_PROXIMITY_LINES = 5


def _finding_dedup_key(finding: dict) -> tuple[str, str, int | None]:
    """Build dedup info for a finding.

    Returns (key, basename, first_line_or_None).
    - key: primary dedup key (loc:basename:line or id:finding_id)
    - basename: file basename for proximity matching
    - first_line: parsed first line number, or None
    """
    file_path = finding.get("file", "").strip()
    basename = file_path.rsplit("/", 1)[-1] if file_path else ""

    lines = finding.get("lines", "")
    first_line = None
    if lines and basename:
        part = re.split(r'[\s,\-]', str(lines))[0]
        if part.isdigit():
            first_line = int(part)
            return (f"loc:{basename}:{first_line}", basename, first_line)

    fid = finding.get("finding_id", "")
    if fid:
        return (f"id:{fid}", basename, None)

    return (f"_anon_{id(finding)}", "", None)


def _extract_text_from_stdout(stdout: str) -> str:
    """Extract plain text from stdout, handling both raw text and JSONL formats."""
    if not stdout or not stdout.strip().startswith("{"):
        return stdout
    parts = []
    for line in stdout.splitlines():
        try:
            msg = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            parts.append(line)
            continue
        m = msg.get("message", {})
        content = m.get("content", [])
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, dict) and block.get("type") == "tool_result":
                    parts.append(str(block.get("content", "")))
    return "\n".join(parts)


def _extract_findings_from_subagents(case_dir: str) -> list[dict]:
    """Extract findings from subagent JSONL transcripts as a last resort."""
    subagent_dir = os.path.join(case_dir, "subagents")
    if not os.path.isdir(subagent_dir):
        return []
    all_text = []
    for fname in sorted(os.listdir(subagent_dir)):
        if not fname.endswith(".jsonl"):
            continue
        fpath = os.path.join(subagent_dir, fname)
        try:
            with open(fpath) as f:
                for line in f:
                    try:
                        msg = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    m = msg.get("message", {})
                    if m.get("role") != "assistant":
                        continue
                    content = m.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if "Finding ID:" in text or re.search(r'[A-Z]+-\d+', text):
                                    all_text.append(text)
        except (OSError, UnicodeDecodeError):
            continue
    if not all_text:
        return []
    combined = "\n\n".join(all_text)
    return _parse_findings_from_text(combined)


def _extract_findings(outputs):
    """Extract structured findings from agent output artifacts, deduped.

    Dedup strategy: two findings are the same if they point to the
    same file within 5 lines of each other. When file:line is absent,
    falls back to finding_id (only collides within exact ID match).

    REPORT files are excluded: they re-summarize agent findings with
    different formatting, causing false inflation. If no agent findings
    exist, falls back to REPORT and stdout.
    """
    files = outputs.get("files", {})
    agent_findings = []
    report_findings = []

    for _path, content in sorted(files.items()):
        if not content or not isinstance(content, str):
            continue
        parsed = _parse_findings_from_text(content)
        if not parsed:
            continue
        if "REPORT" in _path or "report" in _path:
            report_findings.extend(parsed)
        else:
            agent_findings.extend(parsed)

    all_raw = agent_findings
    if not all_raw:
        all_raw = report_findings
    if not all_raw:
        stdout = outputs.get("stdout", "")
        if stdout:
            text = _extract_text_from_stdout(stdout)
            parsed = _parse_findings_from_text(text)
            if parsed:
                all_raw = parsed
    if not all_raw:
        case_dir = outputs.get("case_dir", "")
        if case_dir:
            subagent_findings = _extract_findings_from_subagents(case_dir)
            if subagent_findings:
                all_raw = subagent_findings

    if not all_raw:
        return []

    seen_keys: set[str] = set()
    seen_ids: set[str] = set()
    seen_locations: dict[str, list[int]] = {}
    deduped: list[dict] = []
    for f in all_raw:
        fid = f.get("finding_id", "")
        if fid and fid in seen_ids:
            continue
        key, basename, first_line = _finding_dedup_key(f)
        if key in seen_keys:
            continue
        if first_line is not None and basename in seen_locations:
            if any(abs(first_line - ln) <= _PROXIMITY_LINES
                   for ln in seen_locations[basename]):
                continue
        seen_keys.add(key)
        if fid:
            seen_ids.add(fid)
        if first_line is not None and basename:
            seen_locations.setdefault(basename, []).append(first_line)
        deduped.append(f)
    return deduped


def _parse_findings_from_text(text):
    """Parse structured findings from review report text.

    Supports five formats:
    1. Structured fields: Finding ID: X / Severity: Y / Title: Z / Evidence: W
    2. Markdown headers: ### F-001: Title / **Severity:** High / **File:** path
    3. Narrative consensus: ### N. Title (Severity) [AGENT-NNN + ...] / **File:** path
    4. Table rows: | SEC-001 | Medium | `path` | description |
    5. Bold entries under severity headers: ### Important (N) / **SEC-001: Title**
    Tries all parsers and returns the one that found the most findings.
    """
    results = []
    for parser in [_parse_structured_format, _parse_markdown_format,
                   _parse_narrative_format, _parse_table_format,
                   _parse_bold_entry_format]:
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
    text = re.sub(r'\*\*([A-Za-z ]+):\*\*', r'\1:', text)
    text = re.sub(r'\*\*([A-Za-z ]+)\*\*:', r'\1:', text)
    blocks = re.split(r'(?=Finding\s+ID:)', text)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        fid_m = re.match(r'Finding\s+ID:\s*(\S+)', block)
        if not fid_m:
            continue
        sev_m = re.search(r'Severity:\s*(Critical|Important|High|Minor|Medium|Low)', block, re.IGNORECASE)
        if not sev_m:
            continue
        st_m = re.search(r'Source\s+Trust:\s*(\S+)', block)
        file_m = re.search(r'File:\s*(.+?)(?:\n|$)', block)
        lines_m = re.search(r'Lines?:\s*(.+?)(?:\n|$)', block)
        title_m = re.search(r'Title:\s*(.+?)(?:\n|$)', block)
        evidence_m = re.search(
            r'Evidence:\s*(.+?)(?=\nImpact|\nRecommend|\nVerdict|\nFinding\s+ID:|\Z)',
            block, re.DOTALL,
        )
        if not title_m:
            continue
        findings.append({
            "finding_id": fid_m.group(1).strip(),
            "severity": sev_m.group(1).strip(),
            "source_trust": (st_m.group(1).strip() if st_m else ""),
            "file": (file_m.group(1).strip() if file_m else ""),
            "lines": (lines_m.group(1).strip() if lines_m else ""),
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
    DISMISSED/WITHDRAWN/CONFIRMED in the title, or ADJUST SEVERITY verdicts.
    """
    dismissed_ranges = _find_dismissed_ranges(text)

    findings = []
    header_pattern = re.compile(
        r'^###\s+([A-Z]+-\d+):\s*(.+?)$',
        re.MULTILINE
    )
    headers = list(header_pattern.finditer(text))
    for i, match in enumerate(headers):
        if any(start <= match.start() < end for start, end in dismissed_ranges):
            continue
        finding_id = match.group(1).strip()
        title = match.group(2).strip()
        if re.search(r'\b(DISMISSED|WITHDRAWN|CONFIRMED)\b', title):
            continue
        if re.match(r'ADJUST\s+SEVERITY\b', title):
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
        if re.search(r'\b(DISMISSED|WITHDRAWN|CONFIRMED)\b', title):
            continue
        if re.match(r'ADJUST\s+SEVERITY\b', title):
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
        if severity_raw.lower() in ("id", "severity", "---",
                                     "confirmed", "withdrawn", "status"):
            continue
        severity = _SEVERITY_MAP.get(severity_raw.lower(), severity_raw)
        if severity not in ("Critical", "Important", "Minor"):
            severity = _SEVERITY_MAP.get(severity_raw.split("/")[0].lower(), "Minor")

        file_path = match.group(3).strip().strip('`')
        file_path = re.sub(r':\d+[-,]\d+[-,\d]*$|:\d+$', '', file_path)

        description = match.group(4).strip()

        if re.match(r'^(CONFIRMED|WITHDRAWN|ADJUST\s)', description, re.IGNORECASE):
            continue
        if not file_path or not re.search(r'[./]', file_path):
            continue

        findings.append({
            "finding_id": finding_id,
            "severity": severity,
            "source_trust": "",
            "file": file_path,
            "title": description[:200],
            "evidence": description[:2000],
        })
    return findings


def _parse_bold_entry_format(text):
    """Parse findings from bold entries under severity group headers.

    Handles report formats like:
      ### Important (5)
      **SEC-001: Title here**
      - File: path/to/file.go:123-456
      - Description text
      - Fix: recommendation

      ### Minor (7)
      **SEC-006: Another title**
      ...
    """
    dismissed_ranges = _find_dismissed_ranges(text)

    severity_sections = list(re.finditer(
        r'^###\s+(Critical|Important|Minor|High|Medium|Low)\s*\(\d+\)',
        text, re.MULTILINE | re.IGNORECASE
    ))
    if not severity_sections:
        return []

    findings = []
    for i, sec_match in enumerate(severity_sections):
        if any(start <= sec_match.start() < end
               for start, end in dismissed_ranges):
            continue
        severity_raw = sec_match.group(1).strip()
        severity = _SEVERITY_MAP.get(severity_raw.lower(), severity_raw)

        sec_end = (severity_sections[i + 1].start()
                   if i + 1 < len(severity_sections) else len(text))
        section_text = text[sec_match.end():sec_end]

        entry_pattern = re.compile(
            r'\*\*([A-Z]+-\d+):\s*(.+?)\*\*',
        )
        entries = list(entry_pattern.finditer(section_text))
        for j, entry in enumerate(entries):
            finding_id = entry.group(1).strip()
            title = entry.group(2).strip()

            entry_end = (entries[j + 1].start()
                         if j + 1 < len(entries) else len(section_text))
            body = section_text[entry.end():entry_end]

            file_match = re.search(
                r'-\s*File:\s*`?([^`\n,]+)`?', body)
            if not file_match:
                file_match = re.search(
                    r'`([a-zA-Z][\w/.-]+\.\w+)`', body)
            file_path = file_match.group(1).strip() if file_match else ""
            file_path = re.sub(r'\s*\(lines?\s+\d+[-–]\d+\)$', '',
                               file_path)
            file_path = re.sub(r':\d+[-–,]\d+[-,\d]*$|:\d+$', '',
                               file_path)

            evidence = body.strip()[:2000]

            findings.append({
                "finding_id": finding_id,
                "severity": severity,
                "source_trust": "",
                "file": file_path,
                "title": title,
                "evidence": evidence,
            })
    return findings
