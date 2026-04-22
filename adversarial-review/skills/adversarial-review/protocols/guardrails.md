# Guardrails Protocol

## Purpose

Defines enforceable guardrails that the orchestrator checks programmatically during review execution. Each guardrail has a unique ID, threshold, enforcement behavior, and degraded-mode fallback.

## Constants

| Constant | Default | `--quick` | `--thorough` | `--delta` |
|----------|---------|-----------|--------------|-----------|
| `MAX_ITERATIONS` | 4 | 2 | 4 | 2 |
| `MAX_FINDINGS_PER_AGENT` | 50 | 50 | 50 | 50 |
| `MIN_EVIDENCE_CHARS` | 100 | 100 | 100 | 100 |
| `SEVERITY_INFLATION_CRITICAL_THRESHOLD` | 50% | 50% | 50% | 50% |
| `SEVERITY_INFLATION_COMBINED_THRESHOLD` | 80% | 80% | 80% | 80% |
| `AGENT_BUDGET_MULTIPLIER` | 1.5 | 1.5 | 1.5 | 1.5 |
| `PRE_FLIGHT_WARN_THRESHOLD` | 90% | 90% | 90% | 90% |
| `PRE_FLIGHT_RECOMMEND_THRESHOLD` | 150% | 150% | 150% | 150% |

## Guardrail Definitions

### SCOPE_VIOLATION

- **Trigger:** Finding references a file not in the review scope file.
- **Check:** `validate-output.sh --scope <file-list>`
- **Default action:** Demote to Minor severity, append `[out-of-scope]` to title.
- **Strict mode (`--strict-scope`):** Reject the finding entirely.
- **Scope file:** Generated during Step 2 (Scope Resolution). One repo-relative path per line. In `--diff` mode, includes only changed files — impact graph files remain out of scope.

### FORCED_CONVERGENCE

- **Trigger:** Agent reaches `MAX_ITERATIONS` without converging.
- **Check:** Orchestrator checks `iteration_count >= MAX_ITERATIONS` before dispatching.
- **Action:** Force-stop, use last iteration's output.

### MAX_FINDINGS_EXCEEDED

- **Trigger:** Agent output contains more than `MAX_FINDINGS_PER_AGENT` findings.
- **Check:** `validate-output.sh --max-findings <N>`
- **Action:** Treated as validation failure (existing retry model, max 2 retries). After all retries, take first N findings sorted by severity.

### BUDGET_EXCEEDED

- **Trigger:** Global budget exhausted.
- **Check:** `track-budget.sh status` after every iteration.
- **Action:** Skip remaining iterations (self-refinement), complete current exchange (challenge), stop after current fix (remediation).

### AGENT_BUDGET_EXCEEDED

- **Trigger:** Single agent exceeds per-agent cap.
- **Check:** `track-budget.sh add <chars> --agent <name>` returns `agent_exceeded: true`.
- **Action:** Skip remaining iterations for that agent.
- **Formula:** `per_agent_cap = ceil(total_budget / num_active_agents * 1.5)`
- **Adaptive rebalancing:** After Phase 1 completes, the orchestrator calls `track-budget.sh rebalance` to redistribute unused budget from low-activity agents (< 50% usage) to high-activity agents (> 75% usage). This prevents high-finding-count specialists from hitting their cap during Phase 2 while low-activity specialists leave tokens unused.

### WEAK_EVIDENCE / EVIDENCE_DEMOTED

- **Trigger:** Evidence field has < `MIN_EVIDENCE_CHARS` non-whitespace characters AND severity is Critical or Important.
- **Check:** `validate-output.sh` (always checked).
- **Action:** Warning emitted. Orchestrator auto-demotes to Minor.

### SEVERITY_INFLATION

- **Trigger:** > 50% of a specialist's findings are Critical, OR > 80% are Critical + Important.
- **Check:** Orchestrator calculates after self-refinement completes.
- **Action:** Informational warning. Included in challenge round context.

### PRINCIPLE_SEVERITY_ESCALATION

- **Trigger:** A specialist flags a principle violation (`--principles` active) at severity below Critical.
- **Check:** Orchestrator scans validated findings for titles matching `Principle violation: [*]` with severity != Critical.
- **Action:** Auto-escalate to Critical. Log the escalation with original severity and specialist.

### DESTRUCTIVE_PATTERN

- **Trigger:** Recommended fix or generated patch matches a destructive command pattern.
- **Check:** `validate-output.sh --check-fixes` (Phase 1/2) + orchestrator patch scan (Phase 5).
- **Action:** Warning. Orchestrator flags to user before applying.

## Guardrail Trip Log

The orchestrator maintains a list of guardrail events during the review. Each entry:

```
{timestamp, guardrail_id, agent (optional), details}
```

Rendered in the report as `## Guardrails Triggered`. If no guardrails fired: "None."

## Degraded Mode

In single-agent mode (Cursor/AGENTS.md), shell-dependent guardrails are enforced when shell is available, advisory otherwise. Shell availability = platform supports shell execution (Bash tool, terminal access).

| Guardrail | Multi-agent | Single-agent |
|-----------|------------|--------------|
| Scope confinement | Enforced | Advisory |
| Iteration hard cap | Enforced | Enforced if shell |
| Budget enforcement | Enforced | Enforced if shell |
| Agent-level budget cap | Enforced | N/A |
| Output size limit | Enforced | Enforced if shell |
| Remediation scope lock | Enforced | Advisory |
| Audit log | Enforced | Advisory |
| Destructive pattern check | Enforced | Enforced if shell |
| Evidence threshold | Enforced | Enforced if shell |
| Severity inflation | Informational | Advisory |
