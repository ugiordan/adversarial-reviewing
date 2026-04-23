# Token Budget Protocol

## Purpose

Constrain total token consumption to prevent runaway costs. The budget is tracked mechanically by a shell script and enforced by the orchestrator.

## Implementation

**Script:** `scripts/track-budget.sh`

## Configuration

| Parameter | Default | Override |
|-----------|---------|----------|
| Budget limit | 350,000 tokens | `--budget <tokens>` |
| Unlimited mode | off | `--no-budget` |

### Review Profiles

Pre-configured profiles adjust both specialist count and budget:

| Profile | Flag | Specialists | Budget |
|---------|------|-------------|--------|
| Quick | `--quick` | 2 | 150,000 |
| Default | (none) | 5 | 350,000 |
| Thorough | `--thorough` | 5 | 800,000 |

A custom `--budget` flag overrides the profile's default budget while keeping its specialist count. `--no-budget` disables the budget entirely (mutually exclusive with `--budget`).

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

1. **Init:** `scripts/track-budget.sh init <budget_limit>` — creates state file. Pass `0` for unlimited mode (`--no-budget`).
2. **Track:** `scripts/track-budget.sh add <consumption>` — records consumption after each agent call. In unlimited mode, consumption is tracked for reporting but never triggers enforcement.
3. **Check:** `scripts/track-budget.sh status` — returns remaining budget and exceeded flag. In unlimited mode, `exceeded` is always `false` and `remaining` is `"unlimited"`.
4. **Enforce:** orchestrator checks status before each iteration. Skipped entirely when `--no-budget` is active.

## Unlimited Mode (`--no-budget`)

When `--no-budget` is specified:

- Budget is initialized with limit `0`, which the script treats as unlimited
- `status` always returns `exceeded: false` and `remaining: "unlimited"`
- `add --agent` never returns `agent_exceeded: true`
- The pre-flight budget gate is skipped entirely
- Per-agent caps are disabled
- Budget rebalancing (`rebalance`) is a no-op
- Token consumption is still tracked and reported in the final report for visibility
- The iteration hard cap (`MAX_ITERATIONS`) and convergence detection still apply (these are not budget-gated)

## Per-Iteration Context Cap

Each iteration's context is capped at **40,000 tokens**. When the local context cache is active, this cap is enforced as advisory guidance in `navigation.md`: `manage-cache.sh generate-navigation` sorts files by size descending and lists which files fit within the cap, with remaining files marked as "read only if needed". Agents are expected to prioritize the included files. This cap is independent of the overall budget.

## Auto-Escalation

When the pre-flight budget estimate exceeds the configured budget, the orchestrator auto-proposes raising the budget rather than asking the user to manually set `--budget`. The flow:

1. Run `track-budget.sh estimate` to compute `estimated_tokens`
2. If `estimated_tokens > budget * 0.9` (warn threshold):
   - Display the estimate vs. budget mismatch to the user
   - Propose: "This review needs ~X tokens. Raise budget to X? [Y/n]"
   - If user confirms: raise the limit via `track-budget.sh update-limit <estimated_tokens>` (preserves existing consumption)
   - If user declines: proceed with the original budget (review may be truncated)
3. If `estimated_tokens > budget * 1.5` (recommend threshold):
   - Same as above, but also suggest `--quick` or narrower scope as alternatives
   - Propose: "This review needs ~X tokens (1.5x the budget). Raise budget to X, switch to --quick, or narrow scope?"

The auto-escalation is an orchestrator behavior: it re-initializes the budget tracker with the higher limit. The `--budget` flag value is effectively overridden for the session.

When `--no-budget` is active, the pre-flight gate is skipped entirely (auto-escalation never triggers).

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
