import os


def compose_extensions(base_prompt: str, iteration: int, cache_dir: str) -> str:
    if iteration <= 1:
        return ""
    parts = []
    parts.append("\n## Self-Refinement Instructions (Iteration {})".format(iteration))
    parts.append(
        "Review your previous findings in the cache directory. "
        "For each finding, classify as CODE-VERIFIED (traced through actual code) "
        "or ASSUMPTION-BASED (inferred without full trace). "
        "Drop ASSUMPTION-BASED findings unless you can verify them this iteration."
    )

    # Point to populate-findings output (sanitized/split) when available,
    # falling back to raw outputs directory.
    findings_dir = os.path.join(cache_dir, "findings")
    prev_dir = os.path.join(cache_dir, "outputs")
    if os.path.isdir(findings_dir) and os.listdir(findings_dir):
        parts.append(
            f"\nReview your validated findings in: {findings_dir}"
        )
        parts.append(
            "These have been validated and sanitized by populate-findings. "
            "Use these as your authoritative prior findings, not raw outputs."
        )
    elif os.path.isdir(prev_dir):
        parts.append(f"\nPrevious outputs are in: {prev_dir}")

    parts.append(
        "\n### Classification Gate"
    )
    parts.append(
        "Every finding MUST include a classification tag:\n"
        "- **CODE-VERIFIED**: You traced the issue through actual source code "
        "(file path, line number, code snippet).\n"
        "- **ASSUMPTION-BASED**: You inferred the issue from patterns, naming, "
        "or documentation without a direct code trace.\n\n"
        "Only CODE-VERIFIED findings survive to the challenge round. "
        "ASSUMPTION-BASED findings must be promoted to CODE-VERIFIED "
        "in this iteration or they will be dropped."
    )

    return "\n".join(parts)
