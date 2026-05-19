import os


def compose_extensions(base_prompt: str, iteration: int, cache_dir: str) -> str:
    if iteration <= 1:
        return ""
    parts = []
    parts.append("\n## Iteration {} Instructions".format(iteration))
    parts.append(
        "This iteration has two tasks: validate prior findings and "
        "expand coverage to areas not yet examined.\n"
    )

    parts.append("### Task A: Validate Prior Findings")
    parts.append(
        "For each finding in prior-findings.md, Read the cited file:line "
        "and verify the evidence holds. Output a verdict line:\n"
        "- `CONFIRMED <ID>`: evidence verified in code\n"
        "- `WITHDRAWN <ID>: <reason>`: evidence does not hold\n\n"
        "Be rigorous. A finding whose cited line doesn't show what "
        "the finding claims is WITHDRAWN, not CONFIRMED."
    )

    parts.append("\n### Task B: Expand to Uncovered Areas")
    parts.append(
        "Read coverage-report.md to see which files and directories "
        "were NOT examined in previous iterations. Focus your new "
        "investigation on those gaps.\n\n"
        "Report new findings only from uncovered areas, using the "
        "standard finding template under a '## New Findings' section."
    )

    return "\n".join(parts)
