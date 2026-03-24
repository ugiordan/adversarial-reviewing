# Phase 1: Self-Refinement

## Purpose

Each specialist independently reviews the code and iteratively refines their findings. Agents run in parallel within each iteration and never see each other's output during this phase.

## Prerequisites

- Active specialists selected (from configuration or `--quick`/`--thorough` profile)
- Code under review identified and accessible
- Budget initialized via `scripts/track-budget.sh init <budget_limit>`

## Procedure

### Step 1: Generate Isolation Delimiters

Run `scripts/generate-delimiters.sh` to produce unique random delimiters for wrapping the code under review. Each agent receives its own delimiter pair to prevent cross-contamination.

```bash
scripts/generate-delimiters.sh <code_file>
```

The script outputs start/end delimiters in the format `===REVIEW_TARGET_<hex>_START===` / `===REVIEW_TARGET_<hex>_END===`. See `protocols/input-isolation.md` for full specification.

### Step 2: Spawn Agents in Parallel

For each active specialist, spawn an agent with **isolated context** containing:

1. **Role prompt** — the specialist's role file from `agents/<specialist>.md`, including inoculation instructions
2. **Self-refinement protocol** — instructions to review, then self-critique
3. **Isolated code** — the code under review wrapped in the agent's unique random delimiters, with anti-instruction wrapper text
4. **Finding template** — `templates/finding-template.md` defining the required output schema

Each agent operates independently. Agents within the same iteration run in **parallel** — do not serialize agent calls within an iteration.

### Step 3: Collect Initial Output

Gather the raw output from each agent after their first pass.

### Step 4: Validate Output

Run `scripts/validate-output.sh` on each agent's output.

```bash
scripts/validate-output.sh <agent_output_file> <role_prefix>
```

**If validation fails:**
1. Spawn a **fresh agent** (new context, no memory of the failed attempt) with the validation error message appended to the prompt
2. Allow up to **2 validation attempts** per agent per iteration
3. If both attempts fail, exclude the agent's findings for this iteration and log the failure

**If the agent reports zero findings**, the output must contain the `NO_FINDINGS_REPORTED` marker. An empty response without this marker is a validation failure.

### Step 5: Self-Refinement Re-prompt

Re-prompt each agent with validated output from their own prior iteration:

> "Review your own findings. What did you miss? What's a false positive? Refine."

The agent sees only its own previous findings — never another agent's output. This is a self-critique loop, not a debate.

### Step 6: Iterate with Convergence Detection

Repeat Steps 3-5 for up to **3 total iterations** per agent. On iteration 2+, each agent receives its own prior iteration's validated output as context (per Step 5), not a fresh spawn. Subject to these rules:

| Rule | Detail |
|------|--------|
| Minimum iterations | **2** — always run, even if output appears stable after iteration 1 |
| Maximum iterations | **3** (default) — hard cap, proceed to Phase 2 regardless of convergence |
| Profile overrides | `--quick`: max 2, `--delta`: max 2, `--thorough`: max 3 |
| Convergence detection | Run `scripts/detect-convergence.sh` after each iteration (starting from iteration 2) |
| Convergence criteria | Finding ID + Severity identity between consecutive iterations |

**Convergence detection invocation:**

```bash
scripts/detect-convergence.sh <iteration_N_output> <iteration_N_minus_1_output>
```

- Exit code 0: converged — stop iterating (only honored after minimum 2 iterations)
- Exit code 1: not converged — continue to next iteration

**Key invariant:** Convergence is detected by the shell script, **NOT** self-reported by the agent. Never ask an agent "are you done?" or "have you converged?"

### Step 7: Budget Check

After each iteration, track token consumption:

```bash
scripts/track-budget.sh add <iteration_char_count>
scripts/track-budget.sh status
```

If the budget is exceeded:
1. The current iteration's output is kept (never kill a running agent)
2. No further iterations are started
3. Skip Phase 2 and proceed to Phase 3 (No-Debate Resolution) with findings collected so far — see `phases/challenge-round.md` prerequisites

### Step 8: Collect Final Findings

After all iterations complete (via convergence, max iterations, or budget exhaustion), collect the **final validated findings** from each agent's last successful iteration.

These findings are the input to Phase 2 (Challenge Round).

## Parallel Execution Model

```
Iteration 1:
  Agent A ──┐
  Agent B ──┼── parallel ──> Validate ──> Collect
  Agent C ──┘

Iteration 2:
  Agent A (sees own iter-1 output) ──┐
  Agent B (sees own iter-1 output) ──┼── parallel ──> Validate ──> Convergence check
  Agent C (sees own iter-1 output) ──┘

Iteration 3 (only if not converged):
  Agent A (sees own iter-2 output) ──┐
  Agent B (sees own iter-2 output) ──┼── parallel ──> Validate ──> Collect final
  Agent C (sees own iter-2 output) ──┘
```

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Agent produces invalid output twice | Exclude agent's findings for this iteration; log failure |
| Delimiter collision (10 attempts) | Abort review with error — see `protocols/input-isolation.md` |
| No CSPRNG available | Abort review with error |
| Budget exceeded mid-phase | Complete current iteration, skip remaining iterations |
| All agents fail validation | Abort review — no findings to proceed with |

## References

- `protocols/input-isolation.md` — delimiter generation and anti-injection wrapping
- `protocols/convergence-detection.md` — convergence criteria and iteration bounds
- `protocols/token-budget.md` — budget tracking and enforcement
- `scripts/generate-delimiters.sh` — delimiter generation implementation
- `scripts/validate-output.sh` — output schema validation
- `scripts/detect-convergence.sh` — convergence detection implementation
- `scripts/track-budget.sh` — budget tracking implementation
- `templates/finding-template.md` — required finding output format
