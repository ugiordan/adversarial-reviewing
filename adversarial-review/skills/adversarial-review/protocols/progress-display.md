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

### Dynamic Width Algorithm

The status block width adapts to its content. **Never hardcode padding.** Follow this procedure:

1. **Compute column widths:**
   - Col 1 (Agent): `max(7, longest_agent_prefix + 2)` (minimum fits "Agent" + padding)
   - Col 2 (Status): `max(9, longest_status + 2)` (minimum fits "CONVERGED" + padding)
   - Col 3 (Findings): `max(10, longest_findings_text + 2)` (must fit "5 → 3 (converged)" etc.)

2. **Compute header/footer widths:**
   - Title line: `len("  ADVERSARIAL REVIEW: " + topic + " ")` 
   - Phase line: `len("  " + phase_name + "  [" + progress + "]" + " ")`
   - Budget line: `len(" Budget: " + bar + "  " + consumed + "K / " + limit + "K (" + pct + "%)  ~$" + cost + " ")`

3. **Inner width** = `max(col1 + 1 + col2 + 1 + col3, title_width, phase_width, budget_width)`

4. **Pad each line** to inner_width with trailing spaces before the closing `│`

5. **Column separator lines** use `─` to fill: col1 dashes + `┬`/`┼`/`┴` + col2 dashes + `┬`/`┼`/`┴` + remaining dashes to fill inner_width

### Example Output

```
┌────────────────────────────────────────────────────┐
│  ADVERSARIAL REVIEW: adversarial-review-hardening  │
│  Phase 1: Self-Refinement  [Iteration 2/2]         │
├──────────┬───────────┬─────────────────────────────┤
│ Agent    │ Status    │ Findings                    │
├──────────┼───────────┼─────────────────────────────┤
│ SEC      │ CONVERGED │ 7 → 3                       │
│ CORR     │ DONE      │ 1 → 2                       │
├──────────┴───────────┴─────────────────────────────┤
│ Budget: ████████████░░  105K / 150K (70%)  ~$0.76  │
└────────────────────────────────────────────────────┘
```

### Key Rules

- Every content line between `│...│` must have exactly `inner_width` characters between the border characters
- The top `┌─...─┐` and bottom `└─...─┘` lines have exactly `inner_width` dashes
- Column separator lines (`├─┬─┤`, `├─┼─┤`, `├─┴─┤`) must sum to exactly `inner_width` between borders
- Cell content is left-aligned with 1 leading space, padded with trailing spaces to fill the cell width

## Field Definitions

| Field | Source | Description |
|-------|--------|-------------|
| `<topic>` | Step 1 invocation parsing | Review topic name |
| `<phase_name>` | Current phase | "Phase 1: Self-Refinement", "Phase 2: Challenge Round", "Phase 3: Resolution" |
| `<progress_detail>` | Phase-specific | Iteration N/M for Phase 1, "Iteration N" for Phase 2, empty for Phase 3 |
| Agent Status | Agent dispatch state | `DONE`, `RUNNING`, `PENDING`, `CONVERGED`, `FAILED` |
| Findings | Per-agent finding count | Current count, or `prev → curr` on iteration 2+. Append `(converged)` when stable. |
| Budget | `track-budget.sh status` | Visual bar + consumed/limit tokens + percentage + estimated dollar cost |

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

## Budget Bar and Cost

Build the budget bar from `track-budget.sh status` output:

```
consumed_pct = (consumed / limit) * 100
filled_blocks = round(consumed_pct / 100 * 14)
empty_blocks = 14 - filled_blocks
bar = "█" * filled_blocks + "░" * empty_blocks
```

**Cost estimation:** Estimate dollar cost from total tokens consumed. Use approximate per-token rates for the model in use (e.g., Sonnet input $3/M + output $15/M, Opus input $15/M + output $75/M). Since exact input/output split is unavailable, estimate using a blended rate (e.g., ~$7/M for Sonnet agents, ~$40/M for Opus agents). Display as `~$X.XX` to indicate it's approximate.

Display as: `Budget: <bar>  <consumed_K>K / <limit_K>K (<pct>%)  ~$<cost>`

## Minimal Mode

For `--quick` reviews (2 specialists, 2 iterations), the status blocks are still output but the table is naturally smaller. No special handling needed.
