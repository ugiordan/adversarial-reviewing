# Multi-Agent Isolation

Agent isolation is the core security property of the system. It ensures each specialist forms independent judgments without influence from other agents.

## Isolation model

Each specialist agent runs in its own context and receives only the delimited code under review plus its own prompt. Output goes through `validate-output.sh` for structural validation, then `detect-convergence.sh` checks if the finding set has stabilized. If not, the agent iterates. Budget tracking runs as a parallel monitor. The diagram shows the code profile agents (5 specialists); the strategy profile uses 6 specialists with the same isolation model.

```mermaid
flowchart TB
    subgraph Isolation["Isolated Agent Contexts"]
        direction LR
        SEC["SEC\nSecurity\nAuditor"]
        PERF["PERF\nPerformance\nAnalyst"]
        QUAL["QUAL\nCode Quality\nReviewer"]
        CORR["CORR\nCorrectness\nVerifier"]
        ARCH["ARCH\nArchitecture\nReviewer"]
    end

    CODE["Code Under Review"] --> |"delimited input\n(generate-delimiters.sh)"| Isolation
    REFS["Reference modules\n(discover_references.py)"] -.-> |"specialist-filtered"| Isolation

    SEC --> V1["validate-output.sh"]
    PERF --> V2["validate-output.sh"]
    QUAL --> V3["validate-output.sh"]
    CORR --> V4["validate-output.sh"]
    ARCH --> V5["validate-output.sh"]

    V1 & V2 & V3 & V4 & V5 --> CONV["detect-convergence.sh"]
    CONV --> |"converged"| NEXT["Phase 2"]
    CONV --> |"not converged"| Isolation

    BUDGET["track-budget.sh"] -.-> |"monitors"| Isolation

    style Isolation fill:#f0f4ff,stroke:#4a6fa5
    style BUDGET stroke-dasharray: 5 5
    style REFS stroke-dasharray: 3 3
```

## How isolation works in Claude Code

Claude Code's Agent tool spawns sub-agents as independent processes. Each specialist agent:

- Runs in its own agent context with a fresh conversation
- Receives only the code under review (wrapped in unique delimiters) and its own prompt
- Has no mechanism to access other agents' outputs
- Produces output that goes through the orchestrator before any other agent sees it

The orchestrator (SKILL.md) coordinates all communication. It:

1. Spawns agents with isolated inputs
2. Collects and validates outputs
3. Sanitizes findings before routing them as challenges
4. Strips provenance markers and raw output from cross-agent messages

## Mediated communication

During Phase 2 (challenge round), agents need to see each other's findings to challenge them. This happens through the orchestrator:

```mermaid
flowchart LR
    subgraph Orchestrator["Orchestrator (mediates all communication)"]
        direction TB
        SANITIZE["Sanitize findings\n(strip raw output)"]
        AFFINITY["Domain affinity routing\n(route by category)"]
        ROUTE["Route challenges\nto relevant specialists"]
        COLLECT["Collect defenses"]
        SANITIZE --> AFFINITY --> ROUTE
    end

    SPEC_A["Specialist A\nfindings"] --> SANITIZE
    ROUTE --> SPEC_B["Specialist B\nchallenges"]
    SPEC_B --> COLLECT
    COLLECT --> SPEC_A

    style Orchestrator fill:#fff4e6,stroke:#d4a843
    style AFFINITY fill:#e8f5e9,stroke:#28a745
```

Domain affinity routing (green) uses a specialist-to-category mapping to guide challenges to the most relevant reviewer. This is advisory: specialists can still challenge any finding, but the routing hint reduces unnecessary cross-agent token consumption by 40-60%.

Agents never see each other's raw output. They see sanitized finding summaries. This prevents:

- Prompt injection via crafted findings
- Context manipulation through embedded instructions
- Information leakage from one agent's internal reasoning

## Delimiter-based input isolation

Each specialist receives code wrapped in unique delimiters generated per-session:

```
<<<REVIEW_INPUT_a7f3b2c1>>>
[code under review]
<<<END_REVIEW_INPUT_a7f3b2c1>>>
```

Delimiters are:

- Generated randomly per session (not predictable)
- Unique per specialist (different delimiters for each agent)
- Validated in output (agent output cannot contain its own delimiters)

This prevents the reviewed code from containing fake delimiter boundaries that could trick agents into treating injected content as instructions.

## Degraded mode (Cursor, AGENTS.md)

In tools without sub-agent support, isolation is advisory only:

| Property | Multi-agent (Claude Code) | Single-agent (degraded) |
|----------|--------------------------|------------------------|
| Context separation | Enforced (separate processes) | Not available (same context) |
| Output sanitization | Enforced (orchestrator strips) | Advisory (agent compliance) |
| Delimiter isolation | Enforced (unique per agent) | Advisory (same context) |
| Provenance verification | Enforced (validated markers) | Not enforced |
| Injection detection | Programmatic (bash scripts) | Depends on shell access |

In degraded mode, the agent role-plays each specialist sequentially. There is no enforcement boundary. The agent is asked to avoid carrying context between personas, but this is not guaranteed.
