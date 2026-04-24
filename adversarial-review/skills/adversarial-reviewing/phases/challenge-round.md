# Phase 2: Challenge Round
## Contents

- [Purpose](#purpose)
- [Prerequisites](#prerequisites)
- [Procedure](#procedure)
- [Iteration Flow](#iteration-flow)
- [Single-Specialist Mode](#single-specialist-mode)
- [Error Handling](#error-handling)
- [Triage Mode Adaptation (active when --triage is used)](#triage-mode-adaptation-active-when-triage-is-used)
- [References](#references)

## Purpose

Specialists challenge each other's findings through structured debate. All communication is mediated by the orchestrator — agents never see raw output from other agents. The goal is to identify false positives, validate severity assessments, and surface missed issues.

## Prerequisites

- Phase 1 complete — validated findings from all specialists collected
- At least one finding exists (if zero findings from all agents, skip Phases 2-3 and 5 — Phase 4 generates an "all clear" report)
- Budget not yet exhausted (if exhausted in Phase 1, skip Phase 2 and proceed to Phase 3 with Phase 1 findings — Phase 3 uses No-Debate Resolution since no debate occurred)

## Procedure

### Step 1: Pre-Debate Deduplication

Run `${CLAUDE_SKILL_DIR}/scripts/deduplicate.sh` on all Phase 1 findings combined (unchanged):

```bash
${CLAUDE_SKILL_DIR}/scripts/deduplicate.sh <all_phase1_findings>
```

### Step 2: Build Cross-Agent Summary

```bash
CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh build-summary
```

Merges all agents' `summary.md` files into `findings/cross-agent-summary.md`.

### Step 3: Generate Phase 2 Navigation

```bash
CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh generate-navigation <iteration> 2
```

Updates `navigation.md` for Phase 2. On subsequent challenge iterations, pass resolved finding IDs:

```bash
CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh generate-navigation <iteration> 2 --resolved-ids <resolved_file>
```

### Step 3.5: Generate Finding IDs File

Extract the ID column from `cross-agent-summary.md` into a file (one ID per line) for challenge validation:

```bash
FINDING_IDS_FILE=$(mktemp "${TMPDIR:-/tmp}/finding-ids.XXXXXX")
awk -F'|' 'NR>2 && NF>2 {gsub(/^[ \t]+|[ \t]+$/, "", $2); if ($2 != "") print $2}' \
    "$CACHE_DIR/findings/cross-agent-summary.md" > "$FINDING_IDS_FILE"
# Clean up after use (or at end of Phase 2 iteration):
# rm -f "$FINDING_IDS_FILE"
```

### Step 3b: Output Progress Status

Before dispatching challenge round agents, output a progress status block (see SKILL.md "Progress Display") showing "Phase 2: Challenge Round" with the total finding count entering challenge.

### Step 4: Broadcast via Cache and Collect Responses

Send each agent a minimal prompt (~2,825 tokens) with Phase 2 cache navigation:

> ## Cache Access — Phase 2
>
> Your review materials are at: {CACHE_DIR}
>
> Read `{CACHE_DIR}/navigation.md` FIRST.
>
> 1. Read `findings/cross-agent-summary.md` — overview of all findings
> 2. Read full finding files ONLY for findings you intend to challenge or that fall in your domain
> 3. You MUST Read the full finding before issuing a Challenge — you cannot challenge based on the summary alone
> 4. Use `templates/challenge-response-template.md` for your response format

**Two-tier finding access:**

- **Tier 1:** Agent reads `findings/cross-agent-summary.md` (~200 tokens) — ID, Severity, Category, File:Line, One-liner.
- **Tier 2:** Agent reads individual finding files (`findings/<agent>/<ID>.md`) only for findings they challenge or that fall in their domain.

**Domain affinity routing:**

When building the per-agent challenge prompt, include the domain affinity hint below to help agents prioritize which findings to read in full. This reduces token waste from agents reading findings far outside their expertise.

| Specialist | Primary domain (must read) | Adjacent domains (should read if relevant) |
|------------|---------------------------|-------------------------------------------|
| SEC | Injection, Auth, Crypto, Secrets, OWASP | Error handling, Input validation, Concurrency |
| PERF | Complexity, Memory, I/O, Caching, Concurrency | Scalability, Resource management |
| QUAL | SOLID, Duplication, Naming, Error handling, Tests | Documentation, API design |
| CORR | Logic errors, Edge cases, Race conditions, Invariants | Error handling, State management |
| ARCH | Coupling, Cohesion, Boundaries, Dependencies | API design, Extensibility |

For strat profile:

| Specialist | Primary domain (must read) | Adjacent domains (should read if relevant) |
|------------|---------------------------|-------------------------------------------|
| FEAS | Technical approach, Effort, Dependencies | Phasing, Risk |
| ARCH | Integration, Components, API contracts | Boundaries, Failure modes |
| SEC | Security risks, Auth, Data handling | Compliance, Threat mitigations |
| USER | Backward compat, Migration, API usability | Documentation, Learning curve |
| SCOP | Scope, Acceptance criteria, Completeness | NFR, Edge cases |
| TEST | Test strategy, Verification, AC testability | Integration tests, Performance tests |

For rfe profile:

| Specialist | Primary domain (must read) | Adjacent domains (should read if relevant) |
|------------|---------------------------|-------------------------------------------|
| REQ | Requirement clarity, Measurability, Completeness, Traceability | Acceptance criteria, User scenarios |
| FEAS | Technical approach, Effort, Dependencies | Phasing, Risk, Resource constraints |
| ARCH | Integration, API design, Component boundaries, Data flow | Scalability, Extensibility, Observability |
| SEC | Security risks, Auth, Data handling, Compliance | Threat mitigations, Access control |
| COMPAT | Breaking changes, Migration path, Backward compatibility, Deprecation | API versioning, Rollback safety, Client SDK impact |

The orchestrator appends to each agent's challenge prompt:

> **Domain routing hint:** Your primary domain covers: {primary_domains}. Prioritize reading full findings in these categories. For findings outside your domain, read the summary only and Abstain unless you have specific counter-evidence.

Agents are still free to challenge any finding (the hint is advisory, not enforced), but this guidance reduces unnecessary Tier 2 reads by ~40-60%.

**Interaction with domain-scoped voting pools:** The domain affinity table above is used for **routing** (advisory) during Phase 2 and for **report metadata** in Phase 3. It does NOT determine voting pool membership. Pool membership is behavioral: any specialist who takes an active position (Agree or Challenge) is in the pool, regardless of domain affinity. See `phases/resolution.md` Step 2 for the voting pool rules.

Each agent responds using `profiles/<profile>/templates/challenge-response-template.md`:

```
Response to [FINDING-ID]:
Action: [Agree | Challenge | Abstain]
Severity assessment: [Critical | Important | Minor]    (required if Agree)
Evidence: [supporting or counter-evidence, max 2000 chars]
```

**Strat/RFE profile addition:** When `has_verdicts: true`, challenge responses also include a `Verdict assessment: [Approve | Revise | Reject]` field for the overall document verdict.

**New findings:** Agents may raise new findings in **iterations 1 and 2 only**. New findings are **prohibited in the final iteration** (iteration 3). New findings must use the standard finding template with `Source: Challenge Round` marker.

### Step 4.5: Budget Enforcement Check

After each challenge exchange, check budget status:

```bash
${CLAUDE_SKILL_DIR}/scripts/track-budget.sh status
```

If `exceeded: true`, complete the current exchange but skip subsequent rounds. Emit `BUDGET_EXCEEDED` to the guardrail trip log. Proceed to Phase 3 with findings as-is.

### Reference Module Injection (Challenge Round)

When reference modules are available, they are included in the challenge round prompts using the same `REFERENCE_DATA` delimiter wrapping as Phase 1 iteration 2+. Challengers evaluating findings benefit from reference material to identify false positives or missed severity classifications.

The same specialist-filtered modules and delimiter isolation apply. See `protocols/input-isolation.md` for the REFERENCE_DATA delimiter specification and `${CLAUDE_SKILL_DIR}/scripts/discover-references.sh` for module discovery.

### Step 5: Validate Responses

Two distinct validation paths:

1. **Challenge responses:** Run `${CLAUDE_SKILL_DIR}/scripts/validate-output.sh` with challenge mode:
   ```bash
   ${CLAUDE_SKILL_DIR}/scripts/validate-output.sh <response_file> <role_prefix> --mode challenge --finding-ids <ids_file> --profile <profile>
   ```
2. **New findings raised during challenge:** Run through `manage-cache.sh populate-findings`:
   ```bash
   CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-findings <agent> <role_prefix> <new_findings_file> --scope <scope_file>
   ```

Failed validations: spawn fresh agent with error, up to 2 attempts (same as Phase 1).

### Step 6: Drop Resolved Findings

After each iteration, identify **RESOLVED** findings (all specialists chose **Agree**, no challenges).

Add resolved finding IDs to the resolved file (one per line). Resolved findings remain in the cache for audit but are omitted from `navigation.md` via `--resolved-ids` on the next `generate-navigation` call.

Resolved findings proceed directly to the report as consensus findings.

### Step 7: Detect Convergence

Run `${CLAUDE_SKILL_DIR}/scripts/detect-convergence.sh` on the challenge round output:

```bash
${CLAUDE_SKILL_DIR}/scripts/detect-convergence.sh <iteration_N_responses> <iteration_N_minus_1_responses>
```

Phase 2 convergence requires all of:
1. No new challenges raised
2. No position changes from previous iteration
3. No new findings added

| Rule | Detail |
|------|--------|
| Minimum iterations | **1** if unanimous early exit applies (see below), otherwise **2** |
| Maximum iterations | **3** (default) — hard cap |
| Profile overrides | `--quick`: max 2, `--delta`: max 2, `--thorough`: max 3 |
| Convergence honored | After minimum iterations completed |

**Unanimous early exit:** If ALL agents choose **Agree** on ALL findings in iteration 1 (zero Challenges, zero Abstains), skip iterations 2-3 and proceed directly to Phase 3. Full agreement on the first pass means debate is unnecessary. This saves 1-2 full iterations of token consumption. This early exit does NOT apply in `--thorough` mode, which always runs minimum 2 iterations.

### Step 7b: Output Iteration Status

After each challenge iteration's convergence check, output a progress status block (see SKILL.md "Progress Display"). Show challenge iteration progress, positions collected per agent (Agree/Challenge/Abstain counts), and current budget consumption.

### Step 8: Budget Check

After each iteration:

```bash
${CLAUDE_SKILL_DIR}/scripts/track-budget.sh add <iteration_char_count>
${CLAUDE_SKILL_DIR}/scripts/track-budget.sh status
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
- All agents read `findings/cross-agent-summary.md` from cache, then selectively read individual findings
- Agents respond with Agree/Challenge/Abstain for each finding
- New findings are **allowed**
- Resolved findings are dropped from subsequent iterations

### Iteration 2: Responses to Challenges
- Agents read updated `navigation.md` and selectively read findings
- Agents respond to updated positions
- New findings are **allowed**
- Iteration 2 new findings are included in the cache
- Convergence check runs (but minimum 2 iterations always complete)

### Iteration 3: Evidence-Based Rebuttal (only if not converged)

Iteration 3 is a structured rebuttal round, not a simple "final positions" collection. The goal is to force resolution through evidence rather than opinion.

- Agents read updated `navigation.md` and selectively read findings
- New findings are **prohibited** — validation rejects any new findings in this iteration
- For each finding with active disagreement (at least one Challenge after iteration 2):
  - **Challengers** must either:
    1. **Provide specific file:line evidence** demonstrating why the finding is invalid (e.g., "the call at `src/auth.go:42` is already guarded by `validateToken()` at line 38"), OR
    2. **Retract their challenge** and change position to Agree or Abstain
  - **Originators** must either:
    1. **Provide specific file:line evidence** demonstrating the vulnerability path exists, OR
    2. **Withdraw the finding**
  - Challenges or defenses without file:line citations are treated as retractions
- After completion, proceed to Phase 3 regardless of convergence

The rebuttal prompt appended to iteration 3 is profile-dependent:

**Code profile:**

> For each finding you are challenging or defending, you MUST cite specific file:line evidence.
>
> - If you are **challenging** a finding: show the specific code path that proves the finding is invalid (e.g., existing guard, unreachable code, wrong assumption about the call chain)
> - If you are **defending** a finding: show the specific code path that proves the vulnerability exists (e.g., unvalidated input at file:line flows to dangerous function at file:line)
> - If you cannot cite specific file:line evidence, **retract your position** (change to Agree or Abstain for challenges, Withdraw for defenses)
>
> Positions without evidence citations will be treated as retractions during resolution.

**Strat/RFE profile:**

> For each finding you are challenging or defending, you MUST cite specific document text evidence.
>
> - If you are **challenging** a finding: quote the specific document text that disproves the finding (e.g., the document already addresses this in section X, the acceptance criterion Y covers this case)
> - If you are **defending** a finding: quote the specific document text that creates the risk or gap (e.g., the technical approach in paragraph N proposes X without addressing Y)
> - If you cannot cite specific document text evidence, **retract your position** (change to Agree or Abstain for challenges, Withdraw for defenses)
>
> Positions without document text citations will be treated as retractions during resolution.

## Single-Specialist Mode

When only 1 specialist is active:
- No cross-agent debate is possible
- Instead, run a **devil's advocate pass** using `profiles/<profile>/agents/devils-advocate.md`
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

## Triage Mode Adaptation (active when --triage is used)

In triage mode, specialists debate **verdicts** rather than finding validity. The challenge response template is adapted:

```
Response to TRIAGE-<ROLE>-NNN (re: EXT-NNN):
Action: [Agree | Challenge | Abstain]
Verdict assessment: [Fix | No-Fix | Investigate]    (required if Agree or Challenge)
Evidence: [supporting or counter-evidence, max 2000 chars]
```

Triage-Discovery findings are debated using the standard challenge response template.

## References

- `protocols/mediated-communication.md` — sanitization, provenance, and field isolation rules
- `protocols/input-isolation.md` — delimiter generation for field-level markers and REFERENCE_DATA delimiter specification
- `protocols/convergence-detection.md` — Phase 2 convergence criteria
- `protocols/token-budget.md` — budget tracking and per-iteration context cap
- `protocols/guardrails.md` — guardrail definitions, constants, enforcement behavior
- `${CLAUDE_SKILL_DIR}/scripts/deduplicate.sh` — pre-debate deduplication
- `${CLAUDE_SKILL_DIR}/scripts/discover-references.sh` — reference module discovery and filtering
- `${CLAUDE_SKILL_DIR}/scripts/generate-delimiters.sh` — field-level isolation marker generation
- `${CLAUDE_SKILL_DIR}/scripts/validate-output.sh` — response validation
- `${CLAUDE_SKILL_DIR}/scripts/detect-convergence.sh` — convergence detection
- `${CLAUDE_SKILL_DIR}/scripts/track-budget.sh` — budget tracking
- `profiles/<profile>/templates/challenge-response-template.md` — challenge response format (profile-specific)
- `profiles/<profile>/templates/finding-template.md` — new finding format (profile-specific, with Source marker)
- `templates/sanitized-document-template.md` — sanitized document format (shared)
- `profiles/<profile>/agents/devils-advocate.md` — single-specialist devil's advocate role (profile-specific)
