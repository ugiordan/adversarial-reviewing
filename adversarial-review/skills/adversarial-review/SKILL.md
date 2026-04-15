---
name: adversarial-review
description: Multi-agent adversarial review with isolated specialists, programmatic validation, and evidence-based resolution. Use for reviewing code, designs, or documentation from multiple perspectives.
---

# Adversarial Review

## Overview

This skill spawns multiple specialist sub-agents in fully isolated environments to review code, documentation, or designs from different perspectives. Agents self-refine their findings through internal iteration. The orchestrator mediates all cross-agent communication with programmatic validation via shell scripts — agents never see each other's raw output. Findings are resolved through evidence-based debate with transparent agreement labeling — the report clearly shows whether findings achieved full consensus, majority agreement, or remain disputed.

**Architecture:** Secured [Blackboard pattern](https://en.wikipedia.org/wiki/Blackboard_%28design_pattern%29) — the sanitized findings pool is the shared blackboard, specialist agents are knowledge sources, and the orchestrator is the controller. Unlike classic Blackboard, all reads/writes are mediated through programmatic validation — agents never access the blackboard directly.

**Type:** Rigid — follow the protocol exactly.

## When to Use

- Reviewing code, designs, or documentation from multiple perspectives
- Pre-merge review requiring thoroughness beyond single-agent review
- Verification step after implementation
- Security-sensitive changes needing dedicated specialist attention
- Architecture decisions that benefit from adversarial challenge

## When NOT to Use

- Simple code formatting or style-only changes
- Trivial changes (typos, one-line fixes) that don't benefit from multi-perspective review
- Quick experiments or prototyping
- Tasks where speed matters more than thoroughness
- Changes where the scope is too small to warrant multi-agent overhead

## Checklist

The orchestrator creates tasks dynamically based on the configuration:

- [ ] **Step 1:** Parse invocation flags and resolve scope
- [ ] **Step 2:** Confirm scope with user (MANDATORY — never skip)
- [ ] **Step 3:** Initialize cache (delegate to cache initialization procedure)
- [ ] **Step 4:** Phase 1 — Self-refinement (delegate to `phases/self-refinement.md`)
- [ ] **Step 5:** Phase 2 — Challenge round (delegate to `phases/challenge-round.md`; devil's advocate mode if single-specialist)
- [ ] **Step 6:** Phase 3 — Resolution (delegate to `phases/resolution.md`; simplified if single-specialist)
- [ ] **Step 7:** Phase 4 — Report (delegate to `phases/report.md`)
- [ ] **Step 8:** Phase 5 — Remediation (delegate to `phases/remediation.md`; only when `--fix`, code profile only)

---

## Step 1: Invocation Parsing

Parse the user's invocation to determine profile, specialist selection, mode, and budget.

### Profile Flag

| Flag | Profile | Description |
|------|---------|-------------|
| *(none)* | `code` | Source code review (default, current behavior) |
| `--profile strat` | `strat` | Strategy document review |

The profile determines the agent set, templates, reference modules, and validation mode. Read the profile config:

```bash
scripts/profile-config.sh profiles/<profile> <key>
```

### Specialist Flags (Code Profile)

| Flag | Specialist | Agent File |
|------|-----------|------------|
| `--security` | Security Auditor | `profiles/code/agents/security-auditor.md` |
| `--performance` | Performance Analyst | `profiles/code/agents/performance-analyst.md` |
| `--quality` | Code Quality Reviewer | `profiles/code/agents/code-quality-reviewer.md` |
| `--correctness` | Correctness Verifier | `profiles/code/agents/correctness-verifier.md` |
| `--architecture` | Architecture Reviewer | `profiles/code/agents/architecture-reviewer.md` |

### Specialist Flags (Strat Profile)

| Flag | Specialist | Agent File |
|------|-----------|------------|
| `--security` | Security Analyst | `profiles/strat/agents/security-analyst.md` |
| `--feasibility` | Feasibility Analyst | `profiles/strat/agents/feasibility-analyst.md` |
| `--architecture` | Architecture Reviewer | `profiles/strat/agents/architecture-reviewer.md` |
| `--user-impact` | User Impact Analyst | `profiles/strat/agents/user-impact-analyst.md` |
| `--scope` | Scope & Completeness Analyst | `profiles/strat/agents/scope-completeness-analyst.md` |

If no specialist flags are provided, activate **all 5 specialists** for the active profile.

### Mode Flags

| Flag | Effect |
|------|--------|
| `--delta` | Delta mode — re-review only changes since last review. Also overrides max iterations to 2 (matching minimum, so exactly 2 iterations always run). See `protocols/delta-mode.md`. When `.adversarial-review/last-cache.json` exists, prompts user to reuse previous cache. |
| `--save` | Write report to file. Does NOT commit to git. |
| `--topic <name>` | Override the auto-derived topic name for the review. |
| `--budget <tokens>` | Override the default 500K token budget. |
| `--force` | Override the 200-file hard ceiling. Requires explicit budget confirmation. |
| `--fix` | Enable Phase 5 (Remediation). Classifies findings, drafts Jiras, creates worktree branches, implements fixes, and proposes PRs. |
| `--diff` | Enable diff-augmented input with change-impact graph. Auto-enabled by `--delta`. |
| `--diff --range <range>` | Specify git commit range for diff (e.g., `main..HEAD`, `HEAD~3..HEAD`) |
| `--triage <source>` | Evaluate external review comments. Source: `pr:<N>`, `file:<path>`, or `-` (stdin) |
| `--gap-analysis` | Include coverage gap analysis in triage report (auto-enabled by `--thorough --triage`) |
| `--update-references` | Run `scripts/update-references.sh` before starting review. If used alone (without files/dirs), runs update and exits. If combined with review flags, runs update then proceeds with review. |
| `--list-references` | Show all discovered reference modules and exit. Ignores all other flags. |
| `--keep-cache` | Preserve cache after review. Writes `.adversarial-review/last-cache.json` with session hex + commit SHA. Prints session hex for reuse. |
| `--reuse-cache <hex>` | Reuse an existing cache by session hex. Validates manifest (SHA-256 per file + commit SHA). Skips code/template/reference population. Findings regenerated. |
| `--strict-scope` | Reject (not demote) out-of-scope findings and patches |
| `--fix --dry-run` | Preview remediation without writing anything |
| `--arch-context [url\|path]` | Fetch architecture context for strat profile. Default repo: `opendatahub-io/architecture-context`. Strat profile only. |

### Flag Compatibility

| Flag | Code profile | Strat profile |
|------|-------------|---------------|
| `--delta`, `--diff`, `--triage`, `--fix` | Yes | No (error) |
| `--arch-context` | No (error) | Yes |
| `--save`, `--budget`, `--quick`, `--thorough` | Yes | Yes |
| `--keep-cache`, `--reuse-cache` | Yes | Yes |
| `--strict-scope` | Yes | Yes |

> **Note:** `--strict-scope` is an orchestrator-level flag. `validate-output.sh` always emits scope violations as warnings; the orchestrator decides whether to demote or reject based on `--strict-scope`.

### Flag Interaction: Cache Flags

| Combination | Behavior |
|------------|----------|
| `--delta` + `--reuse-cache` | **Mutually exclusive.** Error: "Use --delta for auto-discovery or --reuse-cache for explicit reuse, not both." |
| `--diff` + `--reuse-cache` | **Mutually exclusive.** Error: "--diff creates a minimal cache from changed files; --reuse-cache expects a complete cache." |
| `--delta` + `--keep-cache` | Composable. Reuses previous cache if confirmed, preserves after completion. |
| `--reuse-cache` + `--keep-cache` | Composable. Reuses specified cache and preserves after completion. |
| `--diff` + `--delta` | Composable. Delta discovers previous cache; diff limits scope to changed files. |

### Preset Profiles

Presets are decoupled from profiles. Which specialists are selected for `--quick` depends on the profile's `quick_specialists` config.

| Flag | Code Profile | Strat Profile | Iterations | Budget |
|------|-------------|---------------|------------|--------|
| `--quick` | SEC + CORR (2) | SEC + FEAS (2) | 2 | 150K |
| `--thorough` | All 5 | All 5 | 3 | 800K |
| *(default)* | All 5 | All 5 | 3 | 350K |

### Defaults

- **Profile:** `code` (if `--profile` not specified)
- **Specialists:** All 5 for the active profile (if none specified)
- **Iterations:** 3 self-refinement rounds (with convergence-based early exit, minimum 2)
- **Budget:** 350K tokens
- **Topic:** Auto-derived from scope (primary directory or file name)

---

### Reference Staleness Check

Before proceeding to scope resolution, run staleness check for each active specialist:

```bash
scripts/discover-references.sh <specialist> --check-staleness
```

Staleness warnings are informational only — they never block the review.

---

## Step 2: Scope Resolution

Determine what code/documents to review. This step is MANDATORY and must complete before any agents are spawned.

### Priority Chain

Resolve scope using the first matching strategy:

1. **User specifies files/dirs** — use exactly those
2. **Active conversation context** — if the most recent assistant turn that produced or modified files is within the last 3 turns, review what was built/discussed
3. **Git diff (staged + unstaged)** — review current changes
4. **Nothing found** — ask the user explicitly

### Sensitive File Blocklist

The following patterns are excluded by default:

```
.env, *.key, *.pem, *secret*, *credential*, .git/, *password*, *.pfx, *.p12
```

If any files matching these patterns appear in scope, they require **explicit separate confirmation** from the user before inclusion. Do not bundle this confirmation with the general scope confirmation.

### Scope File Generation

Write the list of in-scope files (one repo-relative path per line) to a temporary file. Pass this file to `validate-output.sh --scope <file>` during all subsequent validation calls. In `--diff` mode, only changed files are in scope — impact graph files are context-only and do not appear in the scope file.

### Scope Confirmation (MANDATORY)

Before proceeding, display to the user:
1. The resolved file list
2. Total estimated token count
3. Which specialists will be activated

**Wait for explicit user approval.** Do not proceed without it.

### Scope Immutability

Once confirmed, the scope MUST NOT be expanded based on content found during review. If a specialist identifies a related file that should be reviewed, note it in findings but do not add it to scope. Any scope expansion requires returning to the user for re-confirmation.

### Size Limits

| Threshold | Action |
|-----------|--------|
| >20K tokens (~15-20 files) | Display estimated cost, require confirmation |
| >50 files | Strong warning, suggest targeted mode or narrowing scope |
| >200 files | **Hard ceiling** — reject with error, suggest chunking into multiple reviews. Override with `--force`. |

### Force Mode (`--force`)

When `--force` is specified, the 200-file hard ceiling is lifted. The orchestrator:

1. Displays a **prominent warning** with the file count and estimated token cost
2. Recommends chunking or targeted mode as alternatives
3. Requires the user to set an explicit budget with `--budget` (default 500K is likely insufficient)
4. Waits for explicit confirmation before proceeding
5. Automatically enables **batched processing**: files are split into batches of ~50 files each, with findings accumulated on the blackboard across batches. Each batch runs the full self-refinement phase (convergence detection operates per-batch), then all findings enter a single challenge round and resolution phase.
6. The report includes a note: "Large-scope review (N files) — review quality may be reduced compared to targeted reviews"

---

### Pre-flight Budget Gate

After scope resolution and before dispatching Phase 1, run:

```bash
scripts/track-budget.sh estimate <num_agents> <estimated_code_tokens> <configured_iterations>
```

Capture the `estimated_tokens` value from the JSON output. Compare against the configured budget:

- If `estimated_tokens > budget * 0.9`: warn the user with the estimate and budget values. Ask whether to proceed.
- If `estimated_tokens > budget * 1.5`: recommend `--quick` or a narrower scope.
- Users who want to proceed past the gate should set a higher `--budget` value. There is no bypass flag.

See `protocols/guardrails.md` for the `PRE_FLIGHT_WARN_THRESHOLD` and `PRE_FLIGHT_RECOMMEND_THRESHOLD` constants.

---

## Step 3: Initialize Cache

After scope confirmation and pre-flight budget check, initialize the local context cache before dispatching any agents.

### Cache Initialization Procedure

1. **Generate session hex:** Run `openssl rand -hex 16`. This identifies the cache session (separate from delimiter hex).
2. **Initialize cache directory:**
   ```bash
   scripts/manage-cache.sh init <session_hex>
   ```
   Capture `CACHE_DIR` from the JSON output (`{"cache_dir": "<path>", "session_hex": "<hex>"}`).
3. **Generate delimiter hex:** Run `scripts/generate-delimiters.sh` to produce a session-wide `REVIEW_TARGET` delimiter hex. Collision-check against all scope files.
4. **Populate code:**
   ```bash
   CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh populate-code <scope_file> <delimiter_hex>
   ```
5. **Populate templates:**
   ```bash
   REVIEW_PROFILE=<profile> CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh populate-templates
   ```
6. **Populate references:**
   ```bash
   REVIEW_PROFILE=<profile> CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh populate-references
   ```

   `REVIEW_PROFILE` selects the profile directory for templates and references (`code` or `strat`). Defaults to `code` if not set.
7. **Generate navigation:**
   ```bash
   CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh generate-navigation 1 1
   ```
8. **Set cleanup trap** (via Bash tool):
   ```bash
   trap "CACHE_DIR='$CACHE_DIR' '$SCRIPT_DIR/manage-cache.sh' cleanup" EXIT HUP INT TERM
   ```
   **Skip this step if `--keep-cache` is specified.** Note: in agent-tool execution models (e.g., Claude Code Bash tool), the trap may not persist across invocations. The `cleanup_stale` function in `manage-cache.sh` provides a reliability backstop.
9. **Export `CACHE_DIR`** — all subsequent steps use this path.

**Session-wide delimiters:** In cache mode, a single `REVIEW_TARGET` delimiter hex is shared across all agents (see `protocols/input-isolation.md` Session-Wide Delimiter Relaxation). `FIELD_DATA` markers in sanitized findings retain per-field unique hex values.

**Failure:** If any step 2-7 fails, abort the review with error. See the Cache Errors table in Error Handling.

### `--reuse-cache <hex>` Override

When `--reuse-cache` is specified, replace steps 2-7 above with:

1. Validate hex: must match `^[a-f0-9]{32}$`.
2. Scan `$TMPDIR` for directories matching `adversarial-review-cache-<hex>-*`.
3. Run `scripts/manage-cache.sh validate-cache <path>`. If invalid, abort with mismatch details.
4. Set `CACHE_DIR` to the resolved path. Skip all populate steps.
5. Clear findings: `rm -rf "$CACHE_DIR/findings/"*` then `mkdir -p "$CACHE_DIR/findings"`.
6. Regenerate navigation: `scripts/manage-cache.sh generate-navigation 1 1`.

### `--delta` Auto-Discovery

When `--delta` is specified, check for `.adversarial-review/last-cache.json` in the repo root before cache initialization:

- **If found:** Display the session hex and commit SHA. Ask user to confirm reuse.
- **If confirmed:** Follow the `--reuse-cache` flow above with the discovered hex.
- **If declined or not found:** Proceed with normal cache initialization.

### `--keep-cache` Post-Review

After Phase 4 (Report) completes:

1. Write `.adversarial-review/last-cache.json`:
   ```json
   {"session_hex": "<hex>", "commit_sha": "<HEAD>"}
   ```
2. Print: "Cache preserved. Reuse with `--reuse-cache <hex>`"

---

## Step 4: Phase 1 — Self-Refinement

Delegate to `phases/self-refinement.md`.

### Agent Dispatch Procedure

Agent dispatch uses the local context cache (initialized in Step 3). For the detailed cache-based prompt composition and iteration flow, see `phases/self-refinement.md`.

Summary:

1. **Compose minimal prompt (~2,825 tokens)** — role definition, delimiter values, finding template, and cache navigation block pointing agents to `{CACHE_DIR}`. Agents read code from the cache via the Read tool.

2. **Spawn agents in parallel** — dispatch via the host platform's subagent mechanism. Each agent reads `navigation.md` first, then code files from the cache.

3. **Validate and cache findings** — run `manage-cache.sh populate-findings` on each agent's output (replaces separate `validate-output.sh` invocation). This validates, sanitizes, splits findings, and generates the summary table.

4. **Track budget** — after each agent completes, update the budget tracker with per-agent tracking.

   ```bash
   scripts/track-budget.sh add <iteration_char_count> --agent <role_prefix> --per-agent-cap <cap>
   scripts/track-budget.sh status
   ```

### Iteration Hard Cap and Budget Enforcement

Before dispatching each iteration, the orchestrator checks **all three** conditions. If any fails, stop iterating for that agent and use the last iteration's output.

1. **Iteration hard cap:** `iteration_count < MAX_ITERATIONS` (see `protocols/guardrails.md` for values by profile: default 4, quick 2, thorough 4). If exceeded, emit `FORCED_CONVERGENCE` to the guardrail trip log.
2. **Global budget:** `track-budget.sh status` must not return `exceeded: true`. If exceeded, emit `BUDGET_EXCEEDED` to the guardrail trip log.
3. **Agent-level budget:** The response from `track-budget.sh add --agent` must not return `agent_exceeded: true`. If exceeded, emit `AGENT_BUDGET_EXCEEDED` to the guardrail trip log.

After each iteration, check remaining budget. If budget is exceeded, complete the current iteration but do not start another. Proceed to resolution.

### Severity Inflation Check

After all specialists complete self-refinement, compute the severity distribution for each specialist. If any specialist has:

- More than 50% of findings at **Critical** severity, or
- More than 80% of findings at **Critical + Important** combined

emit a `SEVERITY_INFLATION` warning to the guardrail trip log. Include this warning in the specialist's challenge round context so challengers can scrutinize severity assignments.

See `protocols/guardrails.md` for the `SEVERITY_INFLATION_CRITICAL_THRESHOLD` and `SEVERITY_INFLATION_COMBINED_THRESHOLD` constants.

---

## Step 5: Phase 2 — Challenge Round

Delegate to `phases/challenge-round.md`.

In this phase, specialists challenge each other's findings through structured debate. The orchestrator mediates all communication — agents never see each other's raw output. See `protocols/mediated-communication.md` for the mediation protocol. Challenge prompts use `profiles/<profile>/templates/challenge-response-template.md`.

**Single-specialist mode:** When only 1 specialist is active, Phase 2 runs a devil's advocate pass instead of cross-agent debate (see `profiles/<profile>/agents/devils-advocate.md` and the Single-Specialist Mode section in `phases/challenge-round.md`). Phase 2 is NOT skipped — it runs in devil's advocate mode.

---

## Step 6: Phase 3 — Resolution

Delegate to `phases/resolution.md`.

The orchestrator synthesizes challenges and defenses, applies consensus rules, and produces the final validated finding set. Convergence detection uses `scripts/detect-convergence.sh`. Deduplication uses `scripts/deduplicate.sh`.

**Cache interaction:** Phase 3 reads deduplicated findings from `{CACHE_DIR}/findings/`. No cache writes — deduplication and ranking operate on the finding files already in the cache.

---

## Step 7: Phase 4 — Report

Delegate to `phases/report.md`.

Generate the final report using the profile's report template: `profiles/<profile>/templates/report-template.md` (or `profiles/code/templates/delta-report-template.md` for delta mode, code profile only).

**Code profile:** The report includes up to 14 sections:

- Executive summary (Section 1)
- Review configuration (Section 2) — conditional, review parameters summary
- Validated findings with consensus status (Sections 3-6)
- Dismissed findings (Section 7)
- Challenge round findings (Section 8)
- Co-located findings (Section 9)
- **Remediation summary** (Section 10) — severity-sorted action list with remediation roadmap, blocked items, and top priorities. Always present, even without `--fix`.
- **Change Impact** (Section 11) — conditional, when `--diff` is active
- **Review Metrics** (Section 12) — challenge round statistics
- **Guardrails Triggered** (Section 13) — populated from the guardrail trip log
- **Audit Log** (Section 14) — external actions taken during `--fix` and `--triage`

**Strat profile:** The report includes up to 10 sections (see `profiles/strat/templates/report-template.md`):
- Executive summary with verdict agreement level (Section 1)
- Review configuration (Section 2)
- Per-strategy review with verdict tables and categorized findings (Section 3)
- Cross-strategy patterns (Section 4, when reviewing 2+ strategies)
- Architecture context citations (Section 5, when architecture context loaded)
- Dismissed findings (Section 6)
- Challenge round highlights (Section 7)
- Remediation roadmap (Section 8)
- Methodology notes (Section 9)
- Metadata (Section 10)

If `--save` was specified, write the report to `docs/reviews/YYYY-MM-DD-<topic>-review.md`.

**NEVER auto-commit.** The `--save` flag writes the file only.

**Cache interaction:** The final report reads from `{CACHE_DIR}/findings/` for all consensus findings. If `--keep-cache` is specified, write `.adversarial-review/last-cache.json` with session hex and commit SHA before cleanup.

---

## Single-Specialist Mode

When only one specialist is active (e.g., `--security` alone), the full multi-agent protocol is unnecessary. Instead:

1. **Phase 1: Self-refinement** — The specialist reviews and self-refines as normal
2. **Phase 2: Devil's advocate pass** — Instead of cross-agent debate, Phase 2 runs using `profiles/<profile>/agents/devils-advocate.md` to challenge the specialist's findings. The originator responds once. See `phases/challenge-round.md` Single-Specialist Mode section.
3. **Phase 3: Simplified resolution** — Findings the specialist maintained are included with reduced-confidence flag. Findings withdrawn or conceded are dismissed. See `phases/resolution.md` Single-Specialist Mode section.
4. **Phase 4: Report** — Generate report with a disclaimer noting that findings were not cross-validated by other specialists
5. **Phase 5: Remediation** — Runs normally when `--fix` is specified (independent of specialist count)

---

## Step 8: Phase 5 — Remediation

**Only when `--fix` is specified. Code profile only.** Delegate to `phases/remediation.md`. If `--fix` is used with `--profile strat`, emit an error: "Phase 5 (Remediation) is not available for the strat profile. Strategy findings require manual revision of the strategy documents."

This phase transforms validated findings into tracked work items:

1. **Classify** each finding as `jira` (needs Jira ticket before PR), `chore` (direct PR), or `blocked` (needs external approval)
2. **Group** related findings into logical Jira tickets or chore batches
3. **Draft Jira descriptions** using `templates/jira-template.md` and present for user approval
4. **Create worktrees** for each work item (one branch per Jira, one per chore batch)
5. **Implement fixes** in isolation, commit with proper references
6. **Propose PRs** for user confirmation

### Classification Criteria

| Category | Criteria |
|----------|----------|
| **Jira** | Design decision needed, backward compat implications, cross-team impact, needs investigation, severity Important+ with non-trivial fix |
| **Chore** | Self-contained fix, no design decision, single component, fix is obvious from the finding |
| **Blocked** | Needs external approval (architect, cross-team), depends on upstream change, requires RFC/proposal before implementation |

### Worktree Strategy

Each Jira group gets its own worktree and branch (`fix/<jira-id>-<description>`).
Chore findings are batched into small groups (max 8-10 per batch) sharing a worktree and branch (`chore/security-hardening-batch-<N>`).

### Confirmation Gates

The remediation phase has **four mandatory confirmation gates**:
1. Proceed with remediation (initial confirmation after Phase 4 report)
2. Finding classification (jira vs chore vs blocked, with already-fixed status)
3. Jira ticket drafts (with "What We Have Now" / "How We Fix It" reasoning)
4. PR proposals

The orchestrator NEVER proceeds past a gate without explicit user approval.

**Cache interaction:** Unless `--keep-cache` is specified, the cleanup trap (set during cache initialization in Step 3) removes the cache directory. If `--keep-cache` is active, the trap is skipped and the cache is preserved for future `--reuse-cache` use.

---

## Error Handling

### Agent Failures

| Scenario | Response |
|----------|----------|
| Agent timeout (120s default) | Continue with remaining agents, note gap in report |
| Agent crash | Same as timeout |
| Malformed output | Spawn a fresh agent with the validation error message; max 2 retry attempts |
| All agents fail | Abort review — minimum 1 agent required to proceed |

### Edge Cases

| Scenario | Response |
|----------|----------|
| Zero findings from all agents | Skip Phases 2-3 and 5. Phase 4 still runs — generate report with "all clear" executive summary and empty sections. If `--save`, write the report file. |
| Budget exceeded mid-iteration | Complete current iteration, stop further iterations. If in Phase 1: skip Phase 2 and proceed to Phase 3 (No-Debate Resolution). If in Phase 2: proceed to Phase 3 with positions collected so far. |
| No shell execution available | Fall back to LLM-based validation with disclaimer in report |
| All findings dismissed in challenge | Report with "all clear" executive summary |

### Cache Errors

| Scenario | Response |
|----------|----------|
| `manage-cache.sh init` fails | Abort review with error |
| `populate-code` fails (collision, missing file) | Abort review — cache integrity cannot be guaranteed |
| `populate-templates` or `populate-references` fails | Abort review — agents need templates and references |
| `populate-findings` fails | Spawn fresh agent with error, max 2 retries. Exclude agent if retries exhausted. |
| `validate-cache` fails on `--reuse-cache` | Abort with mismatch details |
| `generate-navigation` fails | Non-fatal warning — agents use mandatory reads list from prompt |
| Cache directory disappears mid-review | Abort review — unrecoverable |
| `last-cache.json` missing on `--delta` | Treat as not found — create new cache, inform user |

---

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

---

## Guardrail Trip Log

The orchestrator maintains an in-memory list of guardrail events throughout the review. Each entry contains:

```
{timestamp, guardrail_id, agent (optional), details}
```

Guardrail events are appended whenever a guardrail fires (e.g., `FORCED_CONVERGENCE`, `BUDGET_EXCEEDED`, `AGENT_BUDGET_EXCEEDED`, `SCOPE_VIOLATION`, `SEVERITY_INFLATION`, `WEAK_EVIDENCE`, `DESTRUCTIVE_PATTERN`, `MAX_FINDINGS_EXCEEDED`).

The trip log is rendered in the final report as a `## Guardrails Triggered` section. If no guardrails fired during the review, the section reads "None."

See `protocols/guardrails.md` for the full list of guardrail definitions, constants, thresholds, and enforcement behavior.

---

## Token Budget Protocol

Budget management uses `scripts/track-budget.sh`. See `protocols/token-budget.md` for full specification.

```bash
# Initialize budget at start
scripts/track-budget.sh init <budget_limit>

# Add token consumption after each agent operation (file path or char count)
scripts/track-budget.sh add <file_or_char_count>

# Check remaining budget before starting new iteration
scripts/track-budget.sh status

# Estimate total cost before starting a review
scripts/track-budget.sh estimate <num_agents> <code_tokens> <iterations> [num_work_items]
```

If `status` returns `"exceeded": true`, do not start the next iteration. Proceed to resolution with findings collected so far.

---

## Convergence Detection

Between self-refinement iterations, check if agents have converged (finding set unchanged). See `protocols/convergence-detection.md`.

```bash
scripts/detect-convergence.sh <iteration_N_output> <iteration_N_minus_1_output>
```

If an agent has converged, skip further iterations for that agent. If all agents have converged, proceed directly to Phase 2 (devil's advocate mode for single-specialist).

---

## Delta Mode

When `--delta` is specified, follow `protocols/delta-mode.md`:

1. Locate the previous review report (by topic name)
2. Diff the current code against the state at last review
3. Review only changed code, referencing previous findings for context
4. Use `templates/delta-report-template.md` for the output

---

## File Structure Reference

```
skills/adversarial-review/
  SKILL.md                              # This file — main orchestrator
  config/
    model-config.yml.example            # Future multi-model routing (v2)
  profiles/
    code/                               # Code review profile
      config.yml                        # Profile configuration (agents, templates, settings)
      agents/                           # Code-specific specialist prompts
        security-auditor.md             # SEC specialist
        performance-analyst.md          # PERF specialist
        code-quality-reviewer.md        # QUAL specialist
        correctness-verifier.md         # CORR specialist
        architecture-reviewer.md        # ARCH specialist
        devils-advocate.md              # Single-specialist challenge agent
      templates/                        # Code-specific output templates
        finding-template.md             # Finding format (File/Lines evidence)
        challenge-response-template.md  # Challenge response format
        report-template.md              # Report format (14 sections)
        delta-report-template.md        # Delta review report format
        sanitized-document-template.md  # Sanitized cross-agent message format
        jira-template.md                # Jira ticket template (--fix)
        triage-*.md                     # Triage mode templates
      references/                       # Code-specific reference modules
        security/                       # Security references (OWASP, ASVS, k8s)
    strat/                              # Strategy document review profile
      config.yml                        # Profile configuration (agents, templates, settings)
      agents/                           # Strat-specific specialist prompts
        feasibility-analyst.md          # FEAS specialist
        architecture-reviewer.md        # ARCH specialist
        security-analyst.md             # SEC specialist
        user-impact-analyst.md          # USER specialist
        scope-completeness-analyst.md   # SCOP specialist
        devils-advocate.md              # Single-specialist challenge agent
      templates/                        # Strat-specific output templates
        finding-template.md             # Finding format (Document/Citation evidence)
        challenge-response-template.md  # Challenge response format (with Verdict)
        report-template.md              # Report format (10 sections, verdict-based)
      references/                       # Strat-specific reference modules
        all/                            # References for all strat specialists
  phases/
    self-refinement.md                  # Phase 1 procedure (profile-aware)
    challenge-round.md                  # Phase 2 procedure (profile-aware)
    resolution.md                       # Phase 3 procedure (verdict resolution for strat)
    report.md                           # Phase 4 procedure (profile-aware)
    remediation.md                      # Phase 5 procedure (code profile only, --fix)
  protocols/
    input-isolation.md                  # Delimiter-based code isolation
    mediated-communication.md           # Cross-agent message mediation
    convergence-detection.md            # Finding set stability detection
    delta-mode.md                       # Re-review protocol (code profile only)
    token-budget.md                     # Budget tracking protocol
    injection-resistance.md             # Two-tier injection detection
    guardrails.md                       # Guardrail definitions, constants, enforcement
    audit-log.md                        # External action audit log format
    destructive-patterns.txt            # Regex patterns for destructive command detection
  scripts/
    generate-delimiters.sh              # Produces unique code delimiters
    validate-output.sh                  # Validates agent output (--profile aware)
    detect-convergence.sh               # Checks finding set stability
    deduplicate.sh                      # Removes duplicate findings
    track-budget.sh                     # Token budget tracking
    discover-references.sh              # Reference module discovery and filtering
    update-references.sh                # Reference module auto-update
    manage-cache.sh                     # Cache lifecycle: init, populate, validate, cleanup
    profile-config.sh                   # Profile configuration reader
    fetch-architecture-context.sh       # Architecture context fetcher (strat profile)
  tests/
    ...                                 # Test suite (unchanged)
```

**Legacy paths:** The top-level `agents/`, `templates/`, and `references/` directories are preserved as symlinks to `profiles/code/` for backward compatibility. New code should always use profile-qualified paths.

---

## Platform Notes

This skill is designed to be model-agnostic. The orchestrator references tools conceptually:

| Concept | Claude Code | Other Platforms |
|---------|-------------|-----------------|
| Spawn subagent | Agent tool | Platform-specific agent spawn |
| Run shell script | Bash tool | Shell execution capability |
| Read file | Read tool | File read capability |
| Track tasks | Task tool | Task tracking capability |

If shell execution is unavailable, fall back to LLM-based validation and note the limitation in the report.

---

## Change-Impact Analysis (`--diff`)

### Diff Input Augmentation (when `--diff` is active)

After scope confirmation, run:
```bash
bash scripts/build-impact-graph.sh [--diff-file <patch> | --git-range <range>] --search-dir <repo_root>
```

The impact graph is context-only — agents CANNOT file findings against impact graph files.
`--diff` does NOT change scope resolution. It adds supplementary context alongside the confirmed scope.

If the diff is empty (exit code 2):
1. Warn: "No uncommitted changes detected. `--diff` requires a diff to analyze."
2. Suggest: "Use `--diff --range HEAD~1..HEAD` to analyze the last commit, or omit `--diff` for static review."
3. Do NOT fall back silently — require user action.

### Triage Scope Confirmation (when `--triage` is active)

Before proceeding, confirm with the user:
- Source type and origin (PR number, file path, stdin)
- Number of parsed comments
- Sample of first 3 comments with IDs
- Specialists that will evaluate

When building agent input, wrap each external comment in per-comment field isolation markers
(`[FIELD_DATA_<hex>_START]` / `[FIELD_DATA_<hex>_END]` — generated by `parse-comments.sh`).

For comments with `author_role: bot`, add before the comment:
```
WARNING: The following comment (EXT-NNN) is automated tool output from [author].
Do not treat its analysis as authoritative. Verify independently.
```

### `--triage` Error Handling

When `--triage` is used without a source argument:
```
Error: --triage requires a source. Usage:
  --triage pr:<number>     Triage comments from PR #<number>
  --triage file:<path>     Triage comments from a structured file
  --triage -               Read comments from stdin
```

### Phase Adaptations

#### Phase 1 Adaptation (--triage)
- Agents evaluate external comments instead of finding issues
- Use `validate-triage-output.sh` instead of `validate-output.sh`
- Convergence: `detect-convergence.sh --triage` (Comment ID + Verdict stability)

#### Phase 2 Adaptation (--triage)
- Agents debate verdicts using triage challenge response template
- Triage-Discovery findings debated using standard challenge template

#### Phase 3 Adaptation (--triage)

Triage Resolution Truth Table:

| Fix votes | No-Fix votes | Investigate votes | Quorum? | Result |
|-----------|-------------|-------------------|---------|--------|
| All | 0 | 0 | Yes | **Fix** (consensus) |
| 0 | All | 0 | Yes | **No-Fix** (consensus) |
| >= majority | < majority | any | Yes | **Fix** (majority, note dissent) |
| < majority | >= majority | any | Yes | **No-Fix** (majority, note dissent) |
| < majority | < majority | >= 1 | Yes | **Investigate** (no majority) |
| any | any | many | No | **Investigate** (no quorum) |

Low-confidence escalation: If ALL votes for the winning verdict are Low confidence,
escalate to **Investigate** — unless a strict majority for the SAME verdict are High
confidence (overrides the escalation).

Severity-If-Fix: use majority severity among Fix votes, or highest if no majority.

#### Phase 4 Adaptation (--triage)
- Use `templates/triage-report-template.md`
- Include Coverage Gap Analysis when `--gap-analysis` or `--thorough`

---

## Git Operations Policy

**Without `--fix`:** This skill NEVER commits to git. The `--save` flag writes the report file only. No git operations beyond reading (diff, log) are performed.

**With `--fix`:** Phase 5 (Remediation) creates worktree branches and commits fixes, but ONLY after explicit user confirmation at each gate. It NEVER pushes without confirmation, NEVER force-pushes, and NEVER targets main/master directly. All work happens in isolated worktrees on dedicated branches.
