"""Programmatic pattern coverage verification.

After each agent completes, compares pattern-hits against the agent's
output findings. Produces a structured coverage gap report that gets
injected into the next iteration's dispatch directory.

Follows the rfe-creator pattern: verification is deterministic Python,
not agent-generated summaries from memory.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml


def check_coverage(
    dispatch_dir: str,
    agent_prefix: str,
) -> dict:
    """Check if agent output addresses all pattern hits.

    Returns {
        "total_patterns": int,
        "addressed": int,
        "gaps": [{"pattern_id": str, "grep": str, "hits": [{"file": str, "line": int}]}],
        "gap_report_md": str,
    }
    """
    checklist_path = os.path.join(dispatch_dir, "detection-checklist.yaml")
    output_path = os.path.join(dispatch_dir, "output.md")

    if not os.path.isfile(checklist_path) or not os.path.isfile(output_path):
        return {"total_patterns": 0, "addressed": 0, "gaps": [], "gap_report_md": ""}

    try:
        with open(checklist_path) as f:
            checklist = yaml.safe_load(f) or {}
    except Exception:
        return {"total_patterns": 0, "addressed": 0, "gaps": [], "gap_report_md": ""}

    patterns = checklist.get("patterns", [])
    if not isinstance(patterns, list):
        return {"total_patterns": 0, "addressed": 0, "gaps": [], "gap_report_md": ""}

    try:
        output = Path(output_path).read_text(errors="replace")
    except OSError:
        return {"total_patterns": 0, "addressed": 0, "gaps": [], "gap_report_md": ""}

    output_lower = output.lower()

    hit_patterns = [p for p in patterns if isinstance(p, dict) and p.get("status") == "hits_found"]
    total = len(hit_patterns)
    if total == 0:
        return {"total_patterns": 0, "addressed": 0, "gaps": [], "gap_report_md": ""}

    gaps = []
    addressed = 0

    for p in hit_patterns:
        pattern_id = p.get("id", "")
        grep_str = p.get("grep", "")
        hits = p.get("hits", [])
        if not hits:
            continue

        hit_files = {h.get("file", "") for h in hits if isinstance(h, dict)}
        hit_basenames = {os.path.basename(f) for f in hit_files if f}

        is_addressed = False

        if pattern_id and pattern_id.lower() in output_lower:
            is_addressed = True

        if not is_addressed and grep_str and grep_str.lower() in output_lower:
            is_addressed = True

        if not is_addressed:
            finding_files = set(re.findall(r'File:\s*(.+?)(?:\n|$)', output))
            finding_basenames = {os.path.basename(f.strip()) for f in finding_files}
            if hit_basenames & finding_basenames:
                is_addressed = True

        if is_addressed:
            addressed += 1
        else:
            gaps.append({
                "pattern_id": pattern_id,
                "grep": grep_str,
                "category": p.get("category", ""),
                "hits": [{"file": h.get("file", ""), "line": h.get("line", 0)}
                         for h in hits[:3] if isinstance(h, dict)],
            })

    gap_report = _format_gap_report(gaps, total, addressed)

    return {
        "total_patterns": total,
        "addressed": addressed,
        "gaps": gaps,
        "gap_report_md": gap_report,
    }


def _format_gap_report(gaps: list[dict], total: int, addressed: int) -> str:
    """Format coverage gaps as markdown for injection into next iteration."""
    if not gaps:
        return ""

    lines = [
        "## Coverage Gaps (Programmatically Verified)\n",
        f"Pattern coverage: {addressed}/{total} addressed. "
        f"**{len(gaps)} patterns with hits were NOT addressed.**\n",
        "You MUST address each gap below. For each: produce a finding "
        "OR explain with specific evidence why it is not an issue.\n",
    ]

    for gap in gaps:
        lines.append(f"### GAP: {gap['pattern_id']} ({gap['grep']})")
        lines.append(f"Category: {gap['category']}")
        lines.append("Hits that were NOT addressed:")
        for h in gap["hits"]:
            lines.append(f"- {h['file']}:{h['line']}")
        lines.append("")

    return "\n".join(lines)
