# Progress Display & Task Tracking

## Task Tracking

Create tasks dynamically based on specialist count and phase progression. Example for a 5-specialist, 2-iteration review:

```
Task: Parse invocation and resolve scope          [Step 1-2]
Task: Initialize cache                             [Step 3]
Task: SEC self-refinement (iteration 1)            [Step 4]
Task: PERF self-refinement (iteration 1)           [Step 4]
Task: QUAL self-refinement (iteration 1)           [Step 4]
Task: CORR self-refinement (iteration 1)           [Step 4]
Task: ARCH self-refinement (iteration 1)           [Step 4]
Task: SEC self-refinement (iteration 2)            [Step 4]
Task: PERF self-refinement (iteration 2)           [Step 4]
Task: QUAL self-refinement (iteration 2)           [Step 4]
Task: CORR self-refinement (iteration 2)           [Step 4]
Task: ARCH self-refinement (iteration 2)           [Step 4]
Task: Challenge round                              [Step 5]
Task: Resolution                                   [Step 6]
Task: Final report                                 [Step 7]
Task: Classify findings (jira/chore/blocked)       [Step 8, --fix only]
Task: Draft Jira tickets                           [Step 8, --fix only]
Task: Implement fixes (per work item)              [Step 8, --fix only]
Task: Propose PRs                                  [Step 8, --fix only]
```

Update task status as each completes. For single-specialist mode, Phase 2 runs in devil's advocate mode (not skipped). Phase 5 tasks are only created when `--fix` is specified.

## Status Block

The orchestrator outputs a status block at each phase transition and after each self-refinement iteration. Generate it using the formatting script:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/format-status.py \
  --topic "<topic>" \
  --phase "<phase_name>" \
  --progress "<progress_detail>" \
  --agents '<json_array>' \
  --budget-json '<track-budget.sh status output>' \
  --budget-limit <budget>
```

The `--agents` JSON array contains one object per specialist:

```json
[
  {"name": "SEC", "status": "DONE", "findings": "7 -> 3"},
  {"name": "CORR", "status": "CONVERGED", "findings": "2 -> 2 (converged)"},
  {"name": "ARCH", "status": "PENDING", "findings": ""}
]
```

Display the script output to the user verbatim.

## Agent Status Values

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet dispatched this iteration |
| `RUNNING` | Agent dispatched, awaiting response |
| `DONE` | Agent completed this iteration |
| `CONVERGED` | Agent's findings stabilized (no further iterations) |
| `FAILED` | Agent failed validation (max retries exhausted) |

## Findings Field Format

- First iteration: current count (e.g. `5`)
- Subsequent iterations: `prev -> curr` (e.g. `7 -> 3`)
- When stable: append `(converged)` (e.g. `2 -> 2 (converged)`)

## When to Output

Output a status block at these points:

1. **Phase 1 start:** After cache initialization, before dispatching iteration 1 agents. All agents show `PENDING`.
2. **Phase 1 iteration complete:** After each iteration's agents finish and findings are validated. Show finding counts and convergence status.
3. **Phase 2 start:** Before dispatching challenge round. Show total findings entering challenge.
4. **Phase 2 iteration complete:** After each challenge iteration. Show positions collected.
5. **Phase 3 complete:** After resolution. Show final validated/dismissed/escalated counts.

Do NOT output a status block for every individual agent completion within a parallel dispatch. One block per iteration boundary is sufficient.

## Minimal Mode

For `--quick` reviews (2 specialists, 2 iterations), the status blocks are still output but the table is naturally smaller. No special handling needed.
