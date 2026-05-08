import os


# Domain affinity hints: map agent prefix patterns to their primary review domains.
# Used to route specialists to the findings most relevant to their expertise.
_DOMAIN_AFFINITY = {
    "SEC": "security",
    "CORR": "correctness",
    "ARCH": "architecture",
    "PERF": "performance",
    "API": "api-design",
    "NFR": "non-functional",
    "TEST": "testing",
}


def _get_domain_hint(agent_prefix: str) -> str:
    """Return domain affinity hint for an agent prefix."""
    for prefix_pattern, domain in _DOMAIN_AFFINITY.items():
        if agent_prefix.startswith(prefix_pattern):
            return domain
    return ""


def compose_extensions(base_prompt: str, iteration: int, cache_dir: str) -> str:
    parts = []
    parts.append("\n## Challenge Round Instructions")

    # Two-tier finding access: summary for all, detail only for challenged findings
    summary_path = os.path.join(cache_dir, "cross-agent-summary.md")
    findings_dir = os.path.join(cache_dir, "findings")
    if os.path.exists(summary_path):
        parts.append(f"Read the cross-agent summary at: {summary_path}")
        parts.append(
            "Use the summary for an overview of all findings. "
            "Only read the full detail files when you need to challenge "
            "or deeply evaluate a specific finding."
        )
    if os.path.isdir(findings_dir) and os.listdir(findings_dir):
        parts.append(
            f"Detailed per-agent findings are in: {findings_dir}"
        )
        parts.append(
            "Read detailed findings only for items you intend to challenge. "
            "Do not re-read everything; focus on findings in your domain."
        )

    # Domain affinity routing hint
    parts.append(
        "\n### Domain Routing"
    )
    parts.append(
        "Focus your review on findings that fall within your specialization. "
        "Challenge findings outside your domain only when you have strong, "
        "code-backed evidence."
    )

    if iteration >= 3:
        parts.append(
            "\n### Iteration 3 Constraints"
        )
        parts.append(
            "**No new findings allowed in this iteration.** "
            "Evidence-based rebuttals only. Every claim must include "
            "file:line citations from the reviewed code. "
            "Focus exclusively on resolving disputed findings from "
            "previous iterations."
        )
    else:
        parts.append(
            "\nNew findings are allowed in this iteration, but prioritize "
            "challenging existing findings over introducing new ones."
        )

    return "\n".join(parts)
