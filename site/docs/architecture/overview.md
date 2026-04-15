# Design Overview

Adversarial Review is a multi-agent system where independent specialist agents analyze code or strategy documents, debate their findings, and produce a validated report. The core design principle is that no single agent's judgment is trusted: findings must survive structured adversarial scrutiny.

## Architecture

```mermaid
graph TD
    USER["User invocation"] --> SKILL["SKILL.md\n(orchestration procedure)"]

    SKILL --> PARSE["Parse flags\n& resolve scope"]
    PARSE --> CACHE["Initialize cache\n(manage-cache.sh)"]
    CACHE --> CONTEXT["Fetch context\n(fetch-context.sh)"]

    CONTEXT --> P1["Phase 1: Self-Refinement"]
    P1 --> P2["Phase 2: Challenge Round"]
    P2 --> P3["Phase 3: Resolution"]
    P3 --> P4["Phase 4: Report"]
    P4 --> P5["Phase 5: Remediation"]

    subgraph P1_detail["Phase 1 internals"]
        direction TB
        SPAWN["Spawn isolated agents"] --> ITER["Iterate (2-3x)"]
        ITER --> VALIDATE["validate-output.sh"]
        VALIDATE --> CONVERGE["detect-convergence.sh"]
    end

    subgraph P2_detail["Phase 2 internals"]
        direction TB
        SANITIZE["Sanitize findings"] --> ROUTE["Route challenges"]
        ROUTE --> DEFENSE["Collect defenses"]
        DEFENSE --> EVIDENCE["Evidence-based rebuttal\n(iteration 3)"]
    end

    subgraph P3_detail["Phase 3 internals"]
        direction TB
        DEDUP["deduplicate.sh"] --> CLASSIFY["Classify agreement"]
        CLASSIFY --> RESOLVE["Resolve verdicts"]
    end

    P1 -.-> P1_detail
    P2 -.-> P2_detail
    P3 -.-> P3_detail

    style P5 stroke-dasharray: 5 5
```

## Key design decisions

### Why multi-agent?

A single LLM pass produces findings that reflect one perspective. Multiple independent agents:

- Cover different failure modes (security vs. performance vs. correctness)
- Challenge each other's assumptions through structured debate
- Produce findings with transparent agreement levels
- Reduce false positives through adversarial scrutiny

### Why isolation?

Agents run in separate contexts with no access to each other's raw output. This prevents:

- **Anchoring bias**: Seeing another agent's findings before forming your own
- **Conformity pressure**: Adjusting findings to match what others said
- **Output manipulation**: Crafting output to influence another agent's behavior

### Why programmatic validation?

LLM outputs are unpredictable. Bash scripts validate structure, detect injection, and enforce guardrails independently of agent compliance. This means:

- Malformed findings are caught before they reach the report
- Injection attempts in reviewed code don't propagate to agent behavior
- Budget and scope constraints are enforced programmatically, not by asking agents nicely

### Why convergence detection?

Self-refinement without a stopping condition wastes tokens. Convergence detection compares finding sets between iterations and stops when the delta is below threshold. This typically saves 30-40% of the budget compared to fixed iteration counts.

## Component map

| Component | Location | Purpose |
|-----------|----------|---------|
| SKILL.md | `skills/adversarial-review/SKILL.md` | Main orchestration procedure |
| Phases | `phases/` | Per-phase execution procedures |
| Protocols | `protocols/` | Operational rules and constraints |
| Agents | `profiles/<profile>/agents/` | Specialist prompt definitions |
| Templates | `profiles/<profile>/templates/` | Output format definitions |
| References | `profiles/<profile>/references/` | Knowledge base modules |
| Scripts | `scripts/` | Validation and utility scripts |
| Tests | `tests/` | Test suite with fixtures |

## Execution flow

1. **Parse invocation**: Resolve target files, flags, profile, specialists
2. **Initialize cache**: Create temp directory, populate with code and context
3. **Phase 1**: Spawn isolated agents, self-refine with convergence detection
4. **Phase 2**: Mediated cross-agent challenge round
5. **Phase 3**: Deduplicate, classify agreement, resolve verdicts
6. **Phase 4**: Generate structured report
7. **Phase 5** (optional): Classify, draft Jira, implement fixes
8. **Cleanup**: Remove cache, output budget summary
