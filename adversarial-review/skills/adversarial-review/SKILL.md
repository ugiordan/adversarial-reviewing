---
name: adversarial-review
description: Multi-agent adversarial review with isolated specialists, programmatic validation, and evidence-based resolution. Use for reviewing code, designs, or documentation from multiple perspectives.
license: Apache-2.0
compatibility: Requires agent platform with shell execution and subagent spawning capabilities, git, python3, openssl
metadata:
  author: ugiordan
  version: "1.0.0"
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
- [ ] **Step 1b:** Strat pipeline: Create + Quick Review + Adversarial Refine (delegate to `phases/strat-pipeline.md`; only when `--profile strat` without `--review-only`)
- [ ] **Step 2:** Confirm scope with user (MANDATORY — never skip; skipped in pipeline mode, scope is the refined strategy)
- [ ] **Step 3:** Initialize cache (delegate to `protocols/cache-initialization.md`)
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
| `--testability` | Testability Analyst | `profiles/strat/agents/testability-analyst.md` |

If no specialist flags are provided, activate **all specialists** for the active profile.

### Mode Flags

| Flag | Effect |
|------|--------|
| `--delta` | Delta mode — re-review only changes since last review. Also overrides max iterations to 2 (matching minimum, so exactly 2 iterations always run). See `protocols/delta-mode.md`. When `.adversarial-review/last-cache.json` exists, prompts user to reuse previous cache. |
| `--save` | Write report to file. Does NOT commit to git. |
| `--topic <name>` | Override the auto-derived topic name for the review. |
| `--budget <tokens>` | Override the default 350K token budget. |
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
| `--fix --converge` | After all fixes are applied (with fresh-context validation), run `--delta --quick` to catch cross-fix interactions. User confirmation gate between each cycle. Max 3 cycles. Only auto-fixes Critical/Important findings from convergence cycles. See Convergence Loop below. |
| `--context <label>=<source>` | Inject labeled supplementary context. `source` is a git repo URL, local directory, or file path. `label` tells agents how to use the context (e.g., `architecture`, `compliance`, `threat-model`). Repeatable: multiple `--context` flags allowed. Works with both profiles. |
| `--constraints <path>` | Load enforceable constraint pack (YAML). Constraints set severity floors for findings: violations are automatically flagged at the constraint's specified severity or higher. The path can be a directory (loads `constraints.yaml` from it) or a direct YAML file. `.md` reference files in the same directory are loaded as constraint reference modules. Works with both profiles. |
| `--persist` | Enable cross-run finding persistence. Fingerprints findings and stores history in `.adversarial-review/findings-history.jsonl`. On subsequent runs, classifies findings as new/recurring/resolved/regressed. Adds persistence section to report. |
| `--normalize` | Normalize finding output for stability. Sorts findings canonically (specialist, file, line), standardizes formatting. Reduces noise when comparing runs. |
| `--review-only` | Skip pipeline create/refine steps. Review the input document directly. Strat profile only. Default behavior when `--profile strat` was invoked before pipeline was added. |
| `--confirm` | Show refined strategy for user approval before full review. Strat pipeline only. |
| `--principles <path>` | Load project-level design principles from a YAML file. Principles are injected into all refine agents and review specialists as hard constraints. Violations are flagged as Critical findings. Works with strat profile only. See `protocols/principles.md` for YAML format. |
| `--arch-context <repo@ref>` | Fetch architecture context from a specific git ref (tag, branch, or commit SHA). Syntax: `org/repo@ref`. The `@ref` suffix is optional; without it, uses default branch. Strat profile only. |

### Flag Compatibility

| Flag | Code profile | Strat profile |
|------|-------------|---------------|
| `--delta`, `--diff`, `--triage`, `--fix` | Yes | No (error) |
| `--context` | Yes | Yes |
| `--constraints` | Yes | Yes |
| `--save`, `--budget`, `--quick`, `--thorough` | Yes | Yes |
| `--keep-cache`, `--reuse-cache` | Yes | Yes |
| `--strict-scope` | Yes | Yes |
| `--persist`, `--normalize` | Yes | Yes |
| `--principles` | No (error) | Yes |
| `--arch-context` | No (error) | Yes |
| `--review-only` | No (error) | Yes |

> **Note:** `--strict-scope` is an orchestrator-level flag. `validate-output.sh` always emits scope violations as warnings; the orchestrator decides whether to demote or reject based on `--strict-scope`.

### Flag Interaction: Cache Flags

| Combination | Behavior |
|------------|----------|
| `--delta` + `--reuse-cache` | **Mutually exclusive.** Error: "Use --delta for auto-discovery or --reuse-cache for explicit reuse, not both." |
| `--diff` + `--reuse-cache` | **Mutually exclusive.** Error: "--diff creates a minimal cache from changed files; --reuse-cache expects a complete cache." |
| `--delta` + `--keep-cache` | Composable. Reuses previous cache if confirmed, preserves after completion. |
| `--reuse-cache` + `--keep-cache` | Composable. Reuses specified cache and preserves after completion. |
| `--diff` + `--delta` | Composable. Delta discovers previous cache; diff limits scope to changed files. |

### Flag Interaction: Converge Flags

| Combination | Behavior |
|------------|----------|
| `--converge` without `--fix` | Error: "--converge requires --fix" |
| `--converge` + `--dry-run` | `--dry-run` already prevents all writes (no fixes applied, no PRs created). Adding `--converge` has no additional effect since there are no fixes to delta-review. An informational message is emitted: "Converge flag ignored in dry-run mode (no fixes to iterate on)." |
| `--converge` + `--delta` | Composable. Initial review is delta, each convergence cycle uses previous cycle's commit as delta base. |
| `--converge` + `--keep-cache` | Keep final cycle's cache. |
| `--converge` + `--strict-scope` | Two distinct scopes: (1) convergence loop review scope is always "files modified by fixes" (the delta set), (2) `--strict-scope` controls whether fix patches that touch files outside the original review scope are rejected (vs. warned). These are independent: convergence reviews the delta, strict-scope gates what the fix agent can touch. |
| `--converge` + `--profile strat` | Error: "--converge requires --fix, which is code profile only" |

### Flag Interaction: Principles & Arch-Context Flags

| Combination | Behavior |
|------------|----------|
| `--principles` + `--profile code` | Error: "--principles is only available for the strat profile" |
| `--principles` + `--review-only` | Composable. Principles are injected into review specialists as hard constraints. |
| `--principles` + pipeline mode | Composable. Principles are injected into both refine agents and review specialists. |
| `--arch-context` + `--profile code` | Error: "--arch-context is only available for the strat profile" |
| `--arch-context` + `--context architecture=<source>` | Error: "Use --arch-context OR --context architecture=<source>, not both" |
| `--arch-context` + `--review-only` | Composable. Architecture context loaded for review specialists. |

### Flag Interaction: Pipeline Flags

| Combination | Behavior |
|------------|----------|
| `--review-only` + `--confirm` | Error: "confirm gate only applies to pipeline mode" |
| `--review-only` + Jira key input | Error: "review-only requires a file path, not a Jira key" |
| `--review-only` + `--quick` | Quick review-only (2 specialists, 2 iterations). No pipeline. |

### Preset Profiles

Presets are decoupled from profiles. Which specialists are selected for `--quick` depends on the profile's `quick_specialists` config.

| Flag | Code Profile | Strat Profile (pipeline) | Strat Profile (`--review-only`) | Iterations | Budget |
|------|-------------|--------------------------|--------------------------------|------------|--------|
| `--quick` | SEC + CORR (2) | 1 refine + SEC+FEAS review | SEC + FEAS (2) | 2 | 200K / 150K |
| `--thorough` | All 5 | 3 refine + all 6 review | All 6 | 3 | 1M / 800K |
| *(default)* | All 5 | 2 refine + all 6 review | All 6 | 3 | 500K / 350K |

### Defaults

- **Profile:** `code` (if `--profile` not specified)
- **Specialists:** All for the active profile (5 for code, 6 for strat) if none specified
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

## Step 1b: Strat Pipeline (Strat Profile Only)

When `--profile strat` is active and `--review-only` is NOT specified, delegate to `phases/strat-pipeline.md`. This runs the full create, refine, review pipeline:

1. **Create:** Extract input from Jira key or normalize from file into strategy template
2. **Quick Review:** Lightweight 2-specialist review to surface gaps (skipped in `--quick` mode)
3. **Adversarial Refine:** 2-3 role-based agents each produce a complete refined strategy
4. **Mediator:** Section-by-section best-of merge (skipped when only 1 refine agent)
5. **Confirm Gate:** Optional (`--confirm`), shows refined strategy for user approval

After Step 1b completes, the pipeline sets the review scope to the refined strategy document and proceeds to Step 3 (cache initialization), skipping Step 2 (scope confirmation, since the pipeline already determined scope).

**Input detection:** If the positional argument matches regex `^[A-Z][A-Z0-9_]+-\d+$`, it's a Jira key. Otherwise, it's a file path.

**`--review-only`:** Skips this entire step. Proceeds directly to Step 2 (scope resolution) with the input file as the review target. This preserves the original strat profile behavior.

---

## Step 2: Scope Resolution

Delegate to `protocols/scope-resolution.md`. Covers priority chain, sensitive file blocklist, scope file generation, scope confirmation (MANDATORY), scope immutability, size limits, force mode, and pre-flight budget gate.

---

## Step 2b: Deterministic Pre-Analysis (Strat Profile Only)

Delegate to `protocols/pre-analysis.md`. Covers Layer 1 (threat surface extraction), Layer 2 (NFR checklist scan), finding normalization (`--normalize`), finding persistence (`--persist`), prompt version tracking, and structured JSON output.

---

## Step 3: Initialize Cache

Delegate to `protocols/cache-initialization.md`. Covers the full cache lifecycle: init, populate (code, templates, references, context, constraints), navigation generation, cleanup traps, `--reuse-cache` override, `--delta` auto-discovery, and `--keep-cache` post-review.

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

**Strat profile additional outputs (when `--save` is active):**
- **Requirements output:** `docs/reviews/YYYY-MM-DD-<topic>-requirements.md` using `profiles/strat/templates/requirements-template.md`. Splits findings by confidence tier (Required Amendments / Recommended / Human Review) and includes NFR checklist gaps. This is addressed to the STRAT author.
- **JSON output:** `docs/reviews/YYYY-MM-DD-<topic>-findings.json` via `scripts/findings-to-json.py`. Machine-readable findings with enrichment metadata for downstream tooling.

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

### Convergence Loop (`--converge`)

When `--fix --converge` is specified, after Phase 5 completes (all fixes applied with fresh-context validation, PRs proposed):

1. **Run `--delta --quick`** on the fixed code (2 specialists, 2 iterations, scoped to files modified by fixes)
2. **Present results to user** with:
   - New findings discovered in the delta review
   - Cumulative diff from original code to current state
   - Estimated cost for the next fix cycle
3. **User confirmation gate**: continue, stop, or revert to a previous cycle's state
4. If user approves and new Critical/Important findings exist:
   - Apply fixes (with fresh-context validation) for Critical/Important only. Minor findings are reported but not auto-fixed.
   - Go to step 1 (next cycle)
5. If clean (zero new findings) or converged (findings unchanged from previous cycle) → stop

**Hard cap:** Max 3 fix-review cycles.

**Oscillation detection:** After each cycle, compute finding fingerprints (hash of finding ID + file + line range + severity) and compare against ALL previous cycles' fingerprint sets. If the current cycle's fingerprint set intersects with any previous cycle's set (not just N-2), halt with an oscillation warning: "Fixes are interacting in ways the tool cannot resolve autonomously. Cycle N re-introduced findings from cycle M." This catches both direct (A→B→A) and indirect (A→B→C→A) oscillation patterns.

**Non-convergence exit:** If cycle 3 still has findings:
- Present a convergence failure report: all cycles, what was found, what was fixed, what remains
- User chooses: keep current state, revert to the cleanest cycle (fewest findings), or manually intervene

**Budget:** Two budget checks per cycle:
1. **Pre-cycle gate:** Before starting each cycle, check remaining budget. If remaining budget < estimated cycle cost (~150K for delta-quick + fixes), stop and report "budget insufficient for another convergence cycle." Add `CONVERGE_BUDGET_EXCEEDED` to the guardrail trip log.
2. **Per-cycle ceiling:** Each convergence cycle is hard-capped at 200K tokens. If a cycle exceeds this mid-execution (checked after each agent completes via `track-budget.sh status`), halt the cycle, present partial results, and ask the user whether to continue with a fresh budget allocation or stop. Add `CONVERGE_CYCLE_CAP_EXCEEDED` to the guardrail trip log.

Pre-flight estimate for `--converge`: multiply base estimate by 2 (assumes 1 convergence cycle on average).

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

## Operational Protocols

### Progress Display & Task Tracking

See `protocols/progress-display.md` for status block format, agent status values, when to output, and budget bar construction.

### Guardrail Trip Log

The orchestrator maintains an in-memory list of guardrail events throughout the review. Each entry contains:

```
{timestamp, guardrail_id, agent (optional), details}
```

Guardrail events are appended whenever a guardrail fires (e.g., `FORCED_CONVERGENCE`, `BUDGET_EXCEEDED`, `AGENT_BUDGET_EXCEEDED`, `SCOPE_VIOLATION`, `SEVERITY_INFLATION`, `WEAK_EVIDENCE`, `DESTRUCTIVE_PATTERN`, `MAX_FINDINGS_EXCEEDED`).

The trip log is rendered in the final report as a `## Guardrails Triggered` section. If no guardrails fired during the review, the section reads "None."

See `protocols/guardrails.md` for the full list of guardrail definitions, constants, thresholds, and enforcement behavior.

### Token Budget

Budget management uses `scripts/track-budget.sh`. See `protocols/token-budget.md` for full specification. If `status` returns `"exceeded": true`, do not start the next iteration. Proceed to resolution with findings collected so far.

### Convergence Detection

Between self-refinement iterations, check if agents have converged (finding set unchanged). See `protocols/convergence-detection.md`. If all agents have converged, proceed directly to Phase 2.

### Delta Mode

When `--delta` is specified, follow `protocols/delta-mode.md`.

### Change-Impact Analysis & Triage

When `--diff` or `--triage` is active, follow `protocols/diff-triage-mode.md`.

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

## Git Operations Policy

**Without `--fix`:** This skill NEVER commits to git. The `--save` flag writes the report file only. No git operations beyond reading (diff, log) are performed.

**With `--fix`:** Phase 5 (Remediation) creates worktree branches and commits fixes, but ONLY after explicit user confirmation at each gate. It NEVER pushes without confirmation, NEVER force-pushes, and NEVER targets main/master directly. All work happens in isolated worktrees on dedicated branches.
