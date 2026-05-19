import os


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
    for prefix_pattern, domain in _DOMAIN_AFFINITY.items():
        if agent_prefix.startswith(prefix_pattern):
            return domain
    return ""


def compose_extensions(base_prompt: str, iteration: int, cache_dir: str) -> str:
    parts = []
    parts.append("\n## Challenge Round: Adversarial Review + Blind Spots")

    parts.append(
        "\nThis round has two tasks: challenge validated findings and "
        "investigate remaining blind spots."
    )

    parts.append("\n### Task A: Challenge Validated Findings")
    summary_path = os.path.join(cache_dir, "cross-agent-summary.md")
    findings_dir = os.path.join(cache_dir, "findings")
    if os.path.exists(summary_path):
        parts.append(f"Read the cross-agent summary at: {summary_path}")
    if os.path.isdir(findings_dir) and os.listdir(findings_dir):
        parts.append(
            f"Detailed per-agent findings are in: {findings_dir}\n"
            "Read details only for findings you intend to challenge."
        )

    parts.append(
        "\nTry to disprove each finding. Read the cited evidence and check "
        "if it actually demonstrates the claimed vulnerability.\n"
        "- `CONFIRMED <ID>`: evidence holds after adversarial review\n"
        "- `WITHDRAWN <ID>: <reason>`: evidence does not support the claim"
    )

    parts.append("\n### Task B: Blind Spot Scan")
    parts.append(
        "Read coverage-report.md to see which files and directories "
        "were NOT examined in iterations 1-2. Investigate remaining "
        "uncovered areas. Report new findings only from blind spots, "
        "using the standard finding template."
    )

    parts.append("\n### Domain Routing")
    parts.append(
        "Focus your review on findings within your specialization. "
        "Challenge findings outside your domain only with strong, "
        "code-backed evidence."
    )

    if iteration >= 3:
        parts.append("\n### Convergence Constraints")
        parts.append(
            "**No new findings allowed.** Evidence-based rebuttals only. "
            "Every claim must include file:line citations."
        )

    return "\n".join(parts)
