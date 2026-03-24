# Token Budget Protocol

## Purpose

Constrain total token consumption to prevent runaway costs. The budget is tracked mechanically by a shell script and enforced by the orchestrator.

## Implementation

**Script:** `scripts/track-budget.sh`

## Configuration

| Parameter | Default | Override |
|-----------|---------|----------|
| Budget limit | 500,000 tokens | `--budget <tokens>` |

### Review Profiles

Pre-configured profiles adjust both specialist count and budget:

| Profile | Flag | Specialists | Budget |
|---------|------|-------------|--------|
| Quick | `--quick` | 2 | 200,000 |
| Default | (none) | 5 | 500,000 |
| Thorough | `--thorough` | 5 | 800,000 |

A custom `--budget` flag overrides the profile's default budget while keeping its specialist count.

## Budget Estimation

Before starting a review, the orchestrator estimates total token cost:

```
total = (agents x code_tokens x iterations)     # Phase 1: self-refinement
      + cross_agent_debate_overhead              # Phase 2: debate
      + fixed_overhead                           # Phases 3-4: resolution + report
      + remediation_overhead                     # Phase 5: fix agents (if --fix)
```

The Phase 2 debate overhead is computed as:
```
agents x agents x avg_findings x finding_size x iterations
```

With defaults: `avg_findings = 5`, `finding_size = 500 tokens`.

Phases 3-4 use a fixed overhead of 10,000 tokens.

When `--fix` is specified, Phase 5 adds an estimated overhead per work item:
```
remediation_overhead = num_work_items x 15000  # ~15K tokens per fix agent
```
This is a rough estimate — actual cost depends on fix complexity.

**Script invocation:**
```bash
scripts/track-budget.sh estimate <num_agents> <code_tokens> <iterations> [num_work_items]
```

The optional `num_work_items` parameter (default 0) adds Phase 5 remediation overhead to the estimate. The `init` action returns a `state_file` path in its JSON output — the caller must set `BUDGET_STATE_FILE` to this value before calling `add` or `status`.

## Token Counting

Tokens are estimated using the **char/4 heuristic**: divide character count by 4 to approximate token count. When a platform-specific token counting API is available, it is preferred over the heuristic.

**Script invocation:**
```bash
scripts/track-budget.sh add <file_or_char_count>
```

The script accepts either a file path (counts its bytes) or a raw character count.

## Budget Lifecycle

1. **Init:** `scripts/track-budget.sh init <budget_limit>` — creates state file
2. **Track:** `scripts/track-budget.sh add <consumption>` — records consumption after each agent call
3. **Check:** `scripts/track-budget.sh status` — returns remaining budget and exceeded flag
4. **Enforce:** orchestrator checks status before each iteration

## Per-Iteration Context Cap

Each iteration's sanitized document payload (the code under review, wrapped in isolation delimiters) is capped at **50,000 tokens**. If the input exceeds this cap, it is truncated with a marker indicating truncation occurred. This cap is independent of the overall budget.

## Truncation Behavior

When the budget is exhausted mid-review:

1. The **current iteration completes** — it is not interrupted mid-generation
2. **No further iterations** are started — both self-refinement and debate stop
3. The review proceeds directly to **resolution and report generation** with findings collected so far
4. The final report includes a note that the review was budget-truncated

The orchestrator never kills an in-progress agent call. Budget enforcement happens at iteration boundaries.

## State Management

Budget state is stored in a temporary file created via `mktemp /tmp/adversarial-review-budget-XXXXXXXXXX`. The path is tracked via the `BUDGET_STATE_FILE` environment variable. The state file contains:

```json
{"limit": <int>, "consumed": <int>}
```

The `status` action computes `remaining` and `exceeded` dynamically from these values.

## References

- `scripts/track-budget.sh` — budget tracking implementation
- `protocols/convergence-detection.md` — iteration bounds that interact with budget
- `protocols/delta-mode.md` — delta reviews use the same budget mechanism
