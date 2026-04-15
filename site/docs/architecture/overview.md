# Design Overview

Adversarial Review is a multi-agent system where independent specialist agents analyze code or strategy documents, debate their findings, and produce a validated report. The core design principle is that no single agent's judgment is trusted: findings must survive structured adversarial scrutiny.

## Architecture

The system flows from user invocation through flag parsing, cache initialization, and context loading, then into the 5-phase review pipeline. Each phase has internal subcomponents shown in the expanded boxes below. The main pipeline is linear (phases run sequentially), but within each phase there are loops and conditional paths. Phase 5 (dashed) is optional.

```mermaid
graph TD
    USER["User invocation"] --> SKILL["SKILL.md\n(orchestration procedure)"]

    SKILL --> PARSE["Parse flags\n& resolve scope"]
    PARSE --> CACHE["Initialize cache\n(manage_cache.py)"]
    CACHE --> REFS["Discover references\n(discover_references.py)"]
    REFS --> CONTEXT["Fetch context\n(fetch-context.sh)"]

    CONTEXT --> P1["Phase 1: Self-Refinement"]
    P1 --> P2["Phase 2: Challenge Round"]
    P2 --> P3["Phase 3: Resolution"]
    P3 --> P4["Phase 4: Report"]
    P4 --> P5["Phase 5: Remediation"]

    subgraph P1_detail["Phase 1 internals"]
        direction TB
        SPAWN["Spawn isolated agents\n+ reference modules"] --> ITER["Iterate (2-3x)"]
        ITER --> VALIDATE["validate-output.sh"]
        VALIDATE --> CONVERGE["detect-convergence.sh"]
    end

    subgraph P2_detail["Phase 2 internals"]
        direction TB
        SANITIZE["Sanitize findings"] --> AFFINITY["Domain-aware routing\n(affinity matrix)"]
        AFFINITY --> ROUTE["Route challenges"]
        ROUTE --> DEFENSE["Collect defenses"]
        DEFENSE --> EVIDENCE["Evidence-based rebuttal\n(iteration 3)"]
    end

    subgraph P3_detail["Phase 3 internals"]
        direction TB
        DEDUP["deduplicate.py"] --> CLASSIFY["Classify agreement"]
        CLASSIFY --> RESOLVE["Resolve verdicts"]
    end

    subgraph P4_detail["Phase 4 internals"]
        direction TB
        REPORT["Assemble report"] --> META["Metadata block\n+ prompt versions"]
        META --> PERSIST["Finding persistence\n(fingerprint_findings.py)"]
        PERSIST --> NORM["Output normalization\n(normalize_findings.py)"]
    end

    subgraph P5_detail["Phase 5 internals"]
        direction TB
        FIX_CLASSIFY["Classify findings"] --> FIX_IMPL["Implement fixes"]
        FIX_IMPL --> FIX_VERIFY["Fix verification\n(re-invoke specialist)"]
        FIX_VERIFY --> |"incomplete"| FIX_IMPL
    end

    P1 -.-> P1_detail
    P2 -.-> P2_detail
    P3 -.-> P3_detail
    P4 -.-> P4_detail
    P5 -.-> P5_detail

    style P5 stroke-dasharray: 5 5
    style PERSIST stroke-dasharray: 3 3
    style NORM stroke-dasharray: 3 3
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

### Why domain-aware routing?

During the challenge round, agents receive a domain affinity hint that maps finding categories to their primary and adjacent domains. This reduces unnecessary Tier 2 reads (full finding files) by guiding agents to focus on findings in their domain. Agents can still challenge any finding, but the routing hint saves 40-60% of cross-agent token consumption compared to agents reading every finding in full.

### Why finding-aware reference selection?

Reference modules are filtered by specialist, but when truncation is needed under budget constraints, modules relevant to actual findings are prioritized. The `--finding-categories` flag lets the orchestrator pass Phase 1 finding categories to `discover_references.py`, which then truncates non-matching modules first. This keeps the most relevant reference material available even under tight budgets.

### Why finding persistence?

Without cross-run tracking, each review is a fresh start. Finding persistence fingerprints each finding based on its content (file, line bucket, title, specialist) and stores history in `.adversarial-review/findings-history.jsonl`. On subsequent runs, findings are classified as new, recurring, resolved, or regressed. This lets teams track whether issues are actually getting fixed and detect regressions.

### Why output normalization?

LLM outputs are non-deterministic. Running the same review twice produces findings with slightly different wording, ordering, and formatting. Normalization canonicalizes the output (consistent ordering, standardized formatting) so meaningful differences stand out from noise. Stability metrics quantify how much variance exists between runs.

### Why prompt versioning?

Agent prompts evolve over time. Without version tracking, there's no way to know which prompt version produced which findings. Content-based hashing in prompt frontmatter enables reproducibility analysis: if findings changed between runs, was it the code or the prompt that changed?

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
