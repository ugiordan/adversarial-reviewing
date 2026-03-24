# Convergence Detection Protocol

## Purpose

Determine when iterative review has stabilized and further iterations would not produce meaningful changes. Convergence is detected mechanically by a shell script, never self-reported by agents.

## Implementation

**Script:** `scripts/detect-convergence.sh`

## Phase 1: Self-Refinement Convergence

During Phase 1, each specialist iterates on their findings independently. Convergence is detected by comparing the finding set between consecutive iterations.

**Criteria:** Finding ID + Severity identity between iterations.

The script extracts `Finding ID: <PREFIX>-<NNN>` and corresponding `Severity: <level>` pairs from each iteration's output, sorts them, and compares. If the sorted signature is identical, the phase has converged.

**Script invocation:**
```bash
scripts/detect-convergence.sh <iteration_N_file> <iteration_N_minus_1_file>
```

**Output:** JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `converged` | boolean | `true` if finding sets are identical, `false` otherwise |
| `added` | string[] | Finding ID:Severity pairs present in current but not previous iteration |
| `removed` | string[] | Finding ID:Severity pairs present in previous but not current iteration |

A severity change for a finding appears as a simultaneous `removed` (old severity) and `added` (new severity) entry.

- Exit code 0: converged
- Exit code 1: not converged

## Phase 2: Cross-Agent Debate Convergence

During Phase 2, specialists challenge each other's findings. Convergence requires all of:

1. **No new challenges** — no specialist raises a new objection
2. **No position changes** — no specialist changes their stance on an existing challenge
3. **No new findings** — no specialist adds findings they missed in Phase 1

These criteria are assessed by the orchestrator comparing structured output between debate iterations, not by asking agents whether they have converged.

## Iteration Bounds

| Parameter | Value |
|-----------|-------|
| Minimum iterations | 2 (always run, regardless of convergence) |
| Maximum iterations | 3 (hard cap, proceed to next phase even if not converged) |
| Delta mode override | Maximum reduced to 2 for both Phase 1 and Phase 2 (see `protocols/delta-mode.md`) |

The minimum of 2 iterations applies to both Phase 1 and Phase 2 independently. Even if the first iteration's output would match a hypothetical "empty" baseline, the second iteration still runs.

**Delta mode:** When `--delta` is specified, the maximum iterations are reduced to 2 (matching the minimum), so exactly 2 iterations always run. Convergence-based early exit cannot trigger in delta mode.

## Key Invariant

**Convergence is detected by the shell script, NOT self-reported by the agent.**

Agents are never asked "have you converged?" or "are you done?" The orchestrator runs `scripts/detect-convergence.sh` on the output files and uses the exit code to decide whether to continue iterating. This prevents agents from prematurely declaring convergence to reduce their workload.

## References

- `scripts/detect-convergence.sh` — convergence detection implementation
- `protocols/token-budget.md` — budget exhaustion can also terminate iterations early
