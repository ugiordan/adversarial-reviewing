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

## Status Block Format

The orchestrator outputs a status block at each phase transition and after each self-refinement iteration. This gives the user visibility into review progress without requiring them to parse agent tool calls.

```
┌─────────────────────────────────────────────────┐
│  ADVERSARIAL REVIEW: <topic>                    │
│  <phase_name>  [<progress_detail>]              │
├──────────┬──────────┬───────────────────────────┤
│ Agent    │ Status   │ Findings                  │
├──────────┼──────────┼───────────────────────────┤
│ SEC      │ DONE     │ 5 → 3 (converged)         │
│ PERF     │ RUNNING  │ 4                         │
│ QUAL     │ DONE     │ 7 → 6                     │
│ CORR     │ PENDING  │ -                         │
│ ARCH     │ DONE     │ 3 → 3 (converged)         │
├──────────┴──────────┴───────────────────────────┤
│ Budget: ████████░░░░░░  127K / 350K (36%)       │
└─────────────────────────────────────────────────┘
```

## Field Definitions

| Field | Source | Description |
|-------|--------|-------------|
| `<topic>` | Step 1 invocation parsing | Review topic name |
| `<phase_name>` | Current phase | "Phase 1: Self-Refinement", "Phase 2: Challenge Round", "Phase 3: Resolution" |
| `<progress_detail>` | Phase-specific | Iteration N/M for Phase 1, "Iteration N" for Phase 2, empty for Phase 3 |
| Agent Status | Agent dispatch state | `DONE`, `RUNNING`, `PENDING`, `CONVERGED`, `FAILED` |
| Findings | Per-agent finding count | Current count, or `prev → curr` on iteration 2+. Append `(converged)` when stable. |
| Budget bar | `track-budget.sh status` | Visual bar + consumed/limit tokens + percentage |

## Agent Status Values

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet dispatched this iteration |
| `RUNNING` | Agent dispatched, awaiting response |
| `DONE` | Agent completed this iteration |
| `CONVERGED` | Agent's findings stabilized (no further iterations) |
| `FAILED` | Agent failed validation (max retries exhausted) |

## When to Output

Output a status block at these points:

1. **Phase 1 start:** After cache initialization, before dispatching iteration 1 agents. All agents show `PENDING`.
2. **Phase 1 iteration complete:** After each iteration's agents finish and findings are validated. Show finding counts and convergence status.
3. **Phase 2 start:** Before dispatching challenge round. Show total findings entering challenge.
4. **Phase 2 iteration complete:** After each challenge iteration. Show positions collected.
5. **Phase 3 complete:** After resolution. Show final validated/dismissed/escalated counts.

Do NOT output a status block for every individual agent completion within a parallel dispatch. One block per iteration boundary is sufficient.

## Budget Bar Construction

Build the budget bar from `track-budget.sh status` output:

```
consumed_pct = (consumed / limit) * 100
filled_blocks = round(consumed_pct / 100 * 14)
empty_blocks = 14 - filled_blocks
bar = "█" * filled_blocks + "░" * empty_blocks
```

Display as: `Budget: <bar>  <consumed_K>K / <limit_K>K (<pct>%)`

## Minimal Mode

For `--quick` reviews (2 specialists, 2 iterations), the status blocks are still output but the table is naturally smaller. No special handling needed.
