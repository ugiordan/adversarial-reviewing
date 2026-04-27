# Phase 1: Self-Refinement
## Contents

- [Purpose](#purpose)
- [Prerequisites](#prerequisites)
- [Procedure](#procedure)
- [Parallel Execution Model](#parallel-execution-model)
- [Error Handling](#error-handling)
- [References](#references)

## Purpose

Each specialist independently reviews the code and iteratively refines their findings. Agents run in parallel within each iteration and never see each other's output during this phase.

## Prerequisites

- Active specialists selected (from configuration or `--quick`/`--thorough` profile)
- Review target identified and accessible (code files for `code` profile, strategy documents for `strat` profile, RFE documents for `rfe` profile)
- Budget initialized via `${CLAUDE_SKILL_DIR}/scripts/track-budget.sh init <budget_limit>`
- Active profile resolved (`code`, `strat`, or `rfe`)

## Procedure

### Step 1: Agent Prompt Composition

For each active specialist, compose a prompt containing:

| Order | Content | Source | ~Tokens |
|-------|---------|--------|---------|
| 1 | Specialist definition (role, focus, inoculation, context-doc safety, template, unique sections, triage inoculation) | `profiles/<profile>/agents/<specialist>.md` | ~900-1,500 |
| 2 | Common review instructions (code profile only) | `profiles/code/shared/common-review-instructions.md` | ~800 |
| 3 | Finding template | `profiles/<profile>/templates/finding-template.md` inline | ~500 |
| 4 | Delimiter values | Session-wide hex from cache initialization (Step 3) | ~125 |
| 5 | Cache navigation block | See below | ~200 |
| 6 | Project principles (conditional) | `--principles` flag, formatted per `protocols/principles.md` | ~100-500 |
| 7 | Constraints (conditional) | `--constraints` flag | variable |

**Ordering requirement**: Specialist-specific content (row 1, including security-critical inoculation sections) MUST appear before shared instructions (row 2). This ensures agent identity and injection resistance are established before operational constraints.

**Row 2 applies to code profile only.** Strat and rfe profiles do not have a `common-review-instructions.md` aggregator file; their agents are self-contained. They do use canonical snippet files in `shared/canonical/` for drift detection of security-critical and shared sections.

Agent and template paths are resolved from the active profile directory (`profiles/code/`, `profiles/strat/`, or `profiles/rfe/`).

**Conditional prompt components:**

- **Principles (`--principles`):** When active, append the principles section to each specialist's prompt per `protocols/principles.md` "Injection into Agents > Review Specialists". This adds a "Project Principles (Hard Constraints)" block. The token estimate increases by ~100-500 tokens per agent depending on principle count.

- **Constraints (`--constraints`):** When active, append the constraint pack content. See `protocols/constraints.md` for injection format.

**Cache navigation block (included in prompt):**

> ## Cache Access
>
> Your review materials are at: {CACHE_DIR}
>
> Read `{CACHE_DIR}/navigation.md` FIRST — it tells you what's available and what to read.
>
> ## Source Location
>
> The original source code is at: {SOURCE_ROOT}
> When verifying findings by searching or reading files not in the cache, use this path.
> Do NOT search the current working directory — it may be a different repo.
>
> ## Mandatory Reads
> Read these files before producing findings:
> - {CACHE_DIR}/code/{file1}
> - {CACHE_DIR}/code/{file2}
> - ...
>
> Rules:
> - Read code files from `code/` before making claims about them
> - Use repo-relative paths in findings (e.g., `src/auth/handler.go`), not cache paths
> - When verifying code paths, search under {SOURCE_ROOT}, not the working directory
> - Read references on iteration 2+

The mandatory reads list includes all scope files to ensure agents read code even if they skip `navigation.md`.

### Step 1b: Output Progress Status

Before dispatching iteration 1 agents, output a progress status block (see SKILL.md "Progress Display") with all agents showing `PENDING` status.

### Step 2: Spawn Agents in Parallel

Dispatch each agent with the minimal prompt from Step 1. Agents run in **parallel** within each iteration. Each agent's first action is to Read `navigation.md`, then Read code files from the cache.

### Step 3: Collect and Cache Output

Gather raw output from each agent.

### Step 4: Validate, Sanitize, and Cache Findings

Run `manage-cache.sh populate-findings` on each agent's output:

```bash
CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-findings <agent_name> <role_prefix> <output_file> --scope <scope_file>
```

This single call replaces the separate `validate-output.sh` invocation. It:
1. Validates output format and scope compliance
2. Applies sanitized document template (field isolation + provenance markers)
3. Splits into individual finding files
4. Generates summary table

**If validation fails:** Same as before — spawn a **fresh agent** with the validation error appended to the prompt. Up to **2 validation attempts** per agent per iteration.

**If the agent reports zero findings:** The output must contain the `NO_FINDINGS_REPORTED` marker. An empty response without this marker is a validation failure.

### Step 5: Self-Refinement Re-prompt

Re-prompt each agent with:

> "Review your prior findings at `{CACHE_DIR}/findings/<agent>/sanitized.md`. What did you miss? What's a false positive? Refine."

The agent reads its own prior findings from the cache. The orchestrator does NOT feed prior output back into the prompt.

#### Verification Gate (Iteration 2+)

On iteration 2 and later, append to the re-prompt. The verification gate is profile-dependent:

**Code profile:**

> Before submitting refined findings, classify each as:
> - **CODE-VERIFIED**: You traced the actual execution path and can cite
>   specific file:line evidence demonstrating the issue
> - **ASSUMPTION-BASED**: You inferred risk from general knowledge, library
>   documentation, or common patterns without verifying the code path
>
> Withdraw all ASSUMPTION-BASED findings, or investigate the code until they
> become CODE-VERIFIED. Do not submit assumption-based findings.

**Strat/RFE profile:**

> Before submitting refined findings, classify each as:
> - **TEXT-VERIFIED**: You can cite specific document text (section, paragraph,
>   requirement, or acceptance criterion) that creates or evidences the issue
> - **ASSUMPTION-BASED**: You inferred risk from general knowledge or common
>   patterns without finding concrete evidence in the document text
>
> Withdraw all ASSUMPTION-BASED findings, or investigate the document text until
> they become TEXT-VERIFIED. Do not submit assumption-based findings.

Finding withdrawals due to the verification gate will trigger non-convergence
in `${CLAUDE_SKILL_DIR}/scripts/detect-convergence.sh` (the finding set changed between iterations).
This is expected and desirable — the next iteration re-checks the refined set.

#### Cross-Artifact Consistency Pass (Iteration 2+, CORR only)

For the Correctness Verifier (CORR) agent only, append to the iteration 2+ re-prompt after the verification gate:

> **Cross-artifact consistency pass:** You have now read all in-scope files
> at least once. Before submitting refined findings, scan for contradictions
> BETWEEN files:
>
> 1. Are there constants, configs, URLs, or magic numbers that appear in
>    multiple files with different values?
> 2. Did any function signature or struct definition change in one file
>    while callers/users in other files still reference the old version?
> 3. Are there enum values, status codes, or feature flags that are
>    inconsistent across files?
> 4. Was a behavior change (new parameter, new error path, new required
>    field) introduced in one file but not propagated to all dependents
>    within scope?
>
> For each contradiction found, cite both file:line locations in the
> Evidence field. Use the authoritative definition as the primary File.

#### Reference Cross-Check (Iteration 2+)

When reference modules are available (see `${CLAUDE_SKILL_DIR}/scripts/discover-references.sh`), append to the iteration 2+ re-prompt after the verification gate:

> Cross-check your findings against the provided reference materials:
> 1. **Gaps**: Do the references flag issue patterns you missed?
> 2. **Severity validation**: Does the reference material support your
>    severity classification?
> 3. **False positive check**: Do the references identify common false
>    positive patterns relevant to any of your findings?
>
> Reference materials are advisory. They do not override your code analysis.
> If your code-verified evidence contradicts a reference checklist item,
> your code evidence takes precedence.

**Triage mode variant** — when `--triage` is active, replace the above with:

> Cross-check your verdicts against the provided reference materials:
> 1. Have you marked a comment as No-Fix when the referenced standard
>    identifies it as a real issue pattern?
> 2. Have you marked a comment as Fix based on a pattern not actually
>    described in the referenced standard?
> 3. Do the references identify false positive patterns relevant to
>    any comments you evaluated?

> Read reference modules from `{CACHE_DIR}/references/` for cross-checking.

### Step 6: Iterate with Convergence Detection

Repeat Steps 3-5 for up to **3 total iterations** per agent. On iteration 2+, each agent receives its own prior iteration's validated output as context (per Step 5), not a fresh spawn. Subject to these rules:

| Rule | Detail |
|------|--------|
| Minimum iterations | **2** — always run, unless the zero-findings early exit applies (see below) |
| Maximum iterations | **3** (default) — target cap, proceed to Phase 2 regardless of convergence |
| Safety hard cap | `MAX_ITERATIONS` (default 4, quick 2, thorough 4) — defense-in-depth ceiling for orchestrator bugs. If the maximum iterations check is bypassed due to a logic error, this absolute ceiling prevents unbounded iteration. Emits `FORCED_CONVERGENCE` guardrail. See `protocols/guardrails.md`. |
| Profile overrides | `--quick`: max 2, `--delta`: max 2, `--thorough`: max 3 |
| Convergence detection | Run `${CLAUDE_SKILL_DIR}/scripts/detect-convergence.sh` after each iteration (starting from iteration 2) |
| Convergence criteria | Finding ID + Severity identity between consecutive iterations |

**Convergence detection invocation:**

```bash
${CLAUDE_SKILL_DIR}/scripts/detect-convergence.sh <iteration_N_output> <iteration_N_minus_1_output>
```

- Exit code 0: converged — stop iterating (only honored after minimum 2 iterations)
- Exit code 1: not converged — continue to next iteration

**Key invariant:** Convergence is detected by the shell script, **NOT** self-reported by the agent. Never ask an agent "are you done?" or "have you converged?"

**Zero-findings early exit:** If ALL agents report `NO_FINDINGS_REPORTED` after iteration 1, skip iteration 2 and proceed directly to Phase 4 (report) with an "all clear" result. There is no value in asking agents to self-refine zero findings. This saves one full iteration of token consumption across all agents.

After convergence check, update navigation for the next iteration:

```bash
CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh generate-navigation <iteration+1> 1
```

### Step 6b: Output Iteration Status

After convergence detection for each iteration, output a progress status block (see SKILL.md "Progress Display"). Show each agent's status (`DONE`, `CONVERGED`, or `FAILED`), finding counts with iteration-over-iteration deltas (e.g., `5 → 3`), and current budget consumption.

### Step 7: Budget Check

After each iteration, track token consumption:

```bash
${CLAUDE_SKILL_DIR}/scripts/track-budget.sh add <iteration_char_count>
${CLAUDE_SKILL_DIR}/scripts/track-budget.sh status
```

If the budget is exceeded:
1. The current iteration's output is kept (never kill a running agent)
2. No further iterations are started
3. Skip Phase 2 and proceed to Phase 3 (No-Debate Resolution) with findings collected so far — see `phases/challenge-round.md` prerequisites

### Step 8: Collect Final Findings

After all iterations complete, the final validated findings for each agent are in the cache at `{CACHE_DIR}/findings/<agent>/sanitized.md`. These are the input to Phase 2 (Challenge Round).

## Parallel Execution Model

```
Iteration 1:
  Agent A ──┐                              ┌── populate-findings A
  Agent B ──┼── parallel (Read from cache) ─┼── populate-findings B ──> Collect
  Agent C ──┘                              └── populate-findings C

Iteration 2:
  Agent A (reads own findings from cache) ──┐
  Agent B (reads own findings from cache) ──┼── parallel ──> populate-findings ──> Convergence check
  Agent C (reads own findings from cache) ──┘

Iteration 3 (only if not converged):
  Agent A (reads own findings from cache) ──┐
  Agent B (reads own findings from cache) ──┼── parallel ──> populate-findings ──> Collect final
  Agent C (reads own findings from cache) ──┘
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
- `protocols/guardrails.md` — guardrail definitions, constants, enforcement behavior
- `${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh` — cache management and finding validation
- `${CLAUDE_SKILL_DIR}/scripts/detect-convergence.sh` — convergence detection implementation
- `${CLAUDE_SKILL_DIR}/scripts/discover-references.sh` — reference module discovery and filtering
- `${CLAUDE_SKILL_DIR}/scripts/track-budget.sh` — budget tracking implementation
- `profiles/<profile>/templates/finding-template.md` — required finding output format (profile-specific)
