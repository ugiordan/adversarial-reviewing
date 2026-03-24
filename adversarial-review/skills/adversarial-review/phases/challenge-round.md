# Phase 2: Challenge Round

## Purpose

Specialists challenge each other's findings through structured debate. All communication is mediated by the orchestrator — agents never see raw output from other agents. The goal is to identify false positives, validate severity assessments, and surface missed issues.

## Prerequisites

- Phase 1 complete — validated findings from all specialists collected
- At least one finding exists (if zero findings from all agents, skip Phases 2-3 and 5 — Phase 4 generates an "all clear" report)
- Budget not yet exhausted (if exhausted in Phase 1, skip Phase 2 and proceed to Phase 3 with Phase 1 findings — Phase 3 uses No-Debate Resolution since no debate occurred)

## Procedure

### Step 1: Pre-Debate Deduplication

Run `scripts/deduplicate.sh` on all Phase 1 findings combined:

```bash
scripts/deduplicate.sh <all_phase1_findings>
```

This removes exact and near-duplicate findings across specialists before debate begins. Deduplicated findings are logged but excluded from the challenge round.

### Step 2: Assemble Sanitized Document

Build the sanitized document using `templates/sanitized-document-template.md`:

1. **Generate field-level isolation markers** — run `scripts/generate-delimiters.sh` for each field of each finding to produce unique hex tokens
2. **Add provenance markers** — tag each finding with `[PROVENANCE::Specialist_Name::VERIFIED]`
3. **Wrap field content** — enclose every field value in `[FIELD_DATA_<hex>_START]...[FIELD_DATA_<hex>_END]` markers
4. **Strip raw output** — include only validated finding fields; never include agent reasoning, self-refinement drafts, or intermediate output

See `protocols/mediated-communication.md` for the full mediation rules.

### Step 3: Context Cap Enforcement

Check the sanitized document size against the **50,000 token per-iteration context cap**.

If the cap is exceeded:
1. Include only **unresolved findings**, ordered by severity (Critical first, then Important, then Minor)
2. Summarize excluded findings as counts: "Additionally, N Important and M Minor findings were omitted due to context limits"
3. Omitted findings are not debated but are carried forward to resolution with their Phase 1 status

### Step 4: Broadcast and Collect Responses

Send the sanitized document to **all agents** (including the originator of each finding).

Each agent responds using `templates/challenge-response-template.md`:

```
Response to [FINDING-ID]:
Action: [Agree | Challenge | Abstain]
Severity assessment: [Critical | Important | Minor]    (required if Agree)
Evidence: [supporting or counter-evidence, max 2000 chars]
```

**New findings:** Agents may raise new findings in **iterations 1 and 2 only**. New findings are **prohibited in the final iteration** (iteration 3). New findings must use the standard finding template with `Source: Challenge Round` marker.

### Step 5: Validate Responses

Run `scripts/validate-output.sh` on each agent's challenge response.

- Failed validations: spawn fresh agent with error, up to 2 attempts (same as Phase 1)
- Invalid new findings are excluded

### Step 6: Drop Resolved Findings

After each iteration, identify **RESOLVED** findings — those where:
- All specialists who took a position chose **Agree**
- No challenges were raised

Resolved findings are removed from subsequent iterations to reduce context. They proceed directly to the report as consensus findings.

### Step 7: Detect Convergence

Run `scripts/detect-convergence.sh` on the challenge round output:

```bash
scripts/detect-convergence.sh <iteration_N_responses> <iteration_N_minus_1_responses>
```

Phase 2 convergence requires all of:
1. No new challenges raised
2. No position changes from previous iteration
3. No new findings added

Same iteration bounds as Phase 1:

| Rule | Detail |
|------|--------|
| Minimum iterations | **2** — always run |
| Maximum iterations | **3** (default) — hard cap |
| Profile overrides | `--quick`: max 2, `--delta`: max 2, `--thorough`: max 3 |
| Convergence honored | Only after minimum 2 iterations |

### Step 8: Budget Check

After each iteration:

```bash
scripts/track-budget.sh add <iteration_char_count>
scripts/track-budget.sh status
```

If exceeded: complete current iteration, skip remaining iterations, proceed to Phase 3.

### Step 9: Mini Self-Refinement for New Findings

After the challenge round completes, any new findings raised during Phase 2 undergo a **single mini self-refinement pass**:

1. Re-prompt the originator of each new finding: "Review this finding you raised during the challenge round. Refine if needed."
2. Validate the refined output
3. This is a single pass — no iteration loop

This ensures challenge-round findings receive at least minimal self-critique before resolution.

## Iteration Flow

### Iteration 1: Initial Challenges
- All agents receive the full sanitized document
- Agents respond with Agree/Challenge/Abstain for each finding
- New findings are **allowed**
- Resolved findings are dropped from subsequent iterations

### Iteration 2: Responses to Challenges
- Agents see updated document including iteration 1 challenges and any new findings from iteration 1
- Agents respond to updated positions
- New findings are **allowed**
- Iteration 2 new findings are included in the document
- Convergence check runs (but minimum 2 iterations always complete)

### Iteration 3: Final Positions (only if not converged)
- Agents see updated document including iteration 2 challenges and any new findings from iteration 2
- Agents state **final positions only**
- New findings are **prohibited** — validation rejects any new findings in this iteration
- After completion, proceed to Phase 3 regardless of convergence

## Single-Specialist Mode

When only 1 specialist is active:
- No cross-agent debate is possible
- Instead, run a **devil's advocate pass** using `agents/devils-advocate.md`
- The devil's advocate reviews the specialist's findings and challenges them
- The originator then responds once
- Proceed to Phase 3 with reduced-confidence flag

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Agent fails validation twice | Exclude that agent's responses for this iteration; use previous iteration's position or treat as Abstain |
| Context cap exceeded | Prioritize by severity, summarize omitted findings as counts |
| Budget exceeded | Complete current iteration, proceed to Phase 3 |
| New finding in iteration 3 | Validation rejects it; log the violation |
| All agents fail in an iteration | Use previous iteration's positions; proceed to Phase 3 |

## References

- `protocols/mediated-communication.md` — sanitization, provenance, and field isolation rules
- `protocols/input-isolation.md` — delimiter generation for field-level markers
- `protocols/convergence-detection.md` — Phase 2 convergence criteria
- `protocols/token-budget.md` — budget tracking and per-iteration context cap
- `scripts/deduplicate.sh` — pre-debate deduplication
- `scripts/generate-delimiters.sh` — field-level isolation marker generation
- `scripts/validate-output.sh` — response validation
- `scripts/detect-convergence.sh` — convergence detection
- `scripts/track-budget.sh` — budget tracking
- `templates/sanitized-document-template.md` — sanitized document format
- `templates/challenge-response-template.md` — challenge response format
- `templates/finding-template.md` — new finding format (with Source marker)
- `agents/devils-advocate.md` — single-specialist devil's advocate role
