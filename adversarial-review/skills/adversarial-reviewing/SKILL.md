---
name: adversarial-reviewing
description: Performs multi-agent adversarial review of code, strategy documents, or RFE designs. Spawns isolated specialist sub-agents for security audit, architecture review, correctness verification, and more. Use for pre-merge code review, security-sensitive changes, design document review, architecture decisions, or when the user asks for a thorough or multi-perspective review.
user-invocable: true
license: Apache-2.0
compatibility: Requires agent platform with shell execution and subagent spawning capabilities, git, python3, openssl
metadata:
  author: ugiordan
  version: "1.0.0"
---

# Adversarial Review

## Contents

- [Overview](#overview)
- [When to Use](#when-to-use)
- [Checklist](#checklist)
- [Step 1: Invocation Parsing](#step-1-invocation-parsing)
- [Step 1b: Document Pipeline](#step-1b-document-pipeline-stratrfe-profile)
- [Step 2: Scope Resolution](#step-2-scope-resolution)
- [Step 3: Initialize Cache](#step-3-initialize-cache)
- [Step 4: Phase 1 — Self-Refinement](#step-4-phase-1--self-refinement)
- [Step 5: Phase 2 — Challenge Round](#step-5-phase-2--challenge-round)
- [Step 6: Phase 3 — Resolution](#step-6-phase-3--resolution)
- [Step 7: Phase 4 — Report](#step-7-phase-4--report)
- [Single-Specialist Mode](#single-specialist-mode)
- [Step 8: Phase 5 — Remediation](#step-8-phase-5--remediation)
- [Error Handling](#error-handling)
- [Operational Protocols](#operational-protocols)
- [Platform Notes](#platform-notes)
- [Git Operations Policy](#git-operations-policy)

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
- [ ] **Step 1b:** Pipeline: Create + Quick Review + Adversarial Refine (delegate to `phases/strat-pipeline.md` for strat/rfe; only when `--profile strat` or `--profile rfe` without `--review-only`)
- [ ] **Step 2:** Confirm scope with user (MANDATORY — never skip; skipped in pipeline mode, scope is the refined strategy)
- [ ] **Step 3:** Initialize cache (delegate to `protocols/cache-initialization.md`)
- [ ] **Step 3b:** Detect external references and offer auto-fetch (delegate to `protocols/external-reference-detection.md`)
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
| `--profile rfe` | `rfe` | RFE (Request for Enhancement) document review |

The profile determines the agent set, templates, reference modules, and validation mode. Read the profile config:

```bash
${CLAUDE_SKILL_DIR}/scripts/profile-config.sh profiles/<profile> <key>
```

### Specialist Flags

Read the specialist flag table from `profiles/<profile>/PROFILE.md` for the active profile.

If no specialist flags are provided, activate **all specialists** for the active profile.

### Mode Flags

| Flag | Effect |
|------|--------|
| `--delta` | Delta mode — re-review only changes since last review. Also overrides max iterations to 2 (matching minimum, so exactly 2 iterations always run). See `protocols/delta-mode.md`. When `.adversarial-review/last-cache.json` exists, prompts user to reuse previous cache. |
| `--save` | Write report to file. Does NOT commit to git. |
| `--topic <name>` | Override the auto-derived topic name for the review. |
| `--budget <tokens>` | Override the default 350K token budget. |
| `--no-budget` | Disable the token budget entirely. No budget tracking, no per-agent caps, no pre-flight gate. The review runs to completion regardless of token consumption. |
| `--force` | Override the 200-file hard ceiling. Requires explicit budget confirmation. |
| `--fix` | Enable Phase 5 (Remediation). Classifies findings, drafts Jiras, creates worktree branches, implements fixes, and proposes PRs. |
| `--diff` | Enable diff-augmented input with change-impact graph. Auto-enabled by `--delta`. |
| `--diff --range <range>` | Specify git commit range for diff (e.g., `main..HEAD`, `HEAD~3..HEAD`) |
| `--triage <source>` | Evaluate external review comments. Source: `pr:<N>`, `file:<path>`, or `-` (stdin) |
| `--gap-analysis` | Include coverage gap analysis in triage report (auto-enabled by `--thorough --triage`) |
| `--update-references` | Run `${CLAUDE_SKILL_DIR}/scripts/update-references.sh` before starting review. If used alone (without files/dirs), runs update and exits. If combined with review flags, runs update then proceeds with review. |
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
| `--review-only` | Skip pipeline create/refine steps. Review the input document directly. Strat/RFE profile only. Default behavior when `--profile strat` was invoked before pipeline was added. |
| `--confirm` | Show refined document for user approval before full review. Strat/RFE pipeline only. |
| `--principles <path>` | Load project-level design principles from a YAML file. Principles are injected into all refine agents and review specialists as hard constraints. Violations are flagged as Critical findings. Works with strat and rfe profiles. See `protocols/principles.md` for YAML format. |
| `--arch-context <repo@ref>` | Fetch architecture context from a specific git ref (tag, branch, or commit SHA). Syntax: `org/repo@ref`. The `@ref` suffix is optional; without it, uses default branch. Strat/RFE profile only. |

### Flag Compatibility

| Flag | Code profile | Strat profile | RFE profile |
|------|-------------|---------------|-------------|
| `--delta`, `--diff`, `--triage`, `--fix` | Yes | No (error) | No (error) |
| `--context` | Yes | Yes | Yes |
| `--constraints` | Yes | Yes | Yes |
| `--save`, `--budget`, `--no-budget`, `--quick`, `--thorough` | Yes | Yes | Yes |
| `--keep-cache`, `--reuse-cache` | Yes | Yes | Yes |
| `--strict-scope` | Yes | Yes | Yes |
| `--persist`, `--normalize` | Yes | Yes | Yes |
| `--principles` | No (error) | Yes | Yes |
| `--arch-context` | No (error) | Yes | Yes |
| `--review-only` | No (error) | Yes | Yes |

> **Note:** `--strict-scope` is an orchestrator-level flag. `${CLAUDE_SKILL_DIR}/scripts/validate-output.sh` always emits scope violations as warnings; the orchestrator decides whether to demote or reject based on `--strict-scope`.

### Flag Interaction: Cache Flags

| Combination | Behavior |
|------------|----------|
| `--delta` + `--reuse-cache` | **Mutually exclusive.** Error: "Use --delta for auto-discovery or --reuse-cache for explicit reuse, not both." |
| `--diff` + `--reuse-cache` | **Mutually exclusive.** Error: "--diff creates a minimal cache from changed files; --reuse-cache expects a complete cache." |
| `--delta` + `--keep-cache` | Composable. Reuses previous cache if confirmed, preserves after completion. |
| `--reuse-cache` + `--keep-cache` | Composable. Reuses specified cache and preserves after completion. |
| `--diff` + `--delta` | Composable. Delta discovers previous cache; diff limits scope to changed files. |

### Flag Interaction: Budget Flags

| Combination | Behavior |
|------------|----------|
| `--no-budget` + `--budget <N>` | **Mutually exclusive.** Error: "Use --budget to set a limit or --no-budget to remove it, not both." |
| `--no-budget` + `--quick` | Composable. Quick specialist/iteration selection applies, but no token cap. |
| `--no-budget` + `--thorough` | Composable. Thorough specialist/iteration selection applies, but no token cap. |
| `--no-budget` + `--converge` | Composable. Convergence cycles run without budget checks. Per-cycle ceiling (200K) is also disabled. Hard cap (3 cycles) and oscillation detection still apply. |
| `--no-budget` + `--force` | Composable. Both ceiling overrides active. |

### Flag Interaction: Converge Flags

| Combination | Behavior |
|------------|----------|
| `--converge` without `--fix` | Error: "--converge requires --fix" |
| `--converge` + `--dry-run` | `--dry-run` already prevents all writes (no fixes applied, no PRs created). Adding `--converge` has no additional effect since there are no fixes to delta-review. An informational message is emitted: "Converge flag ignored in dry-run mode (no fixes to iterate on)." |
| `--converge` + `--delta` | Composable. Initial review is delta, each convergence cycle uses previous cycle's commit as delta base. |
| `--converge` + `--keep-cache` | Keep final cycle's cache. |
| `--converge` + `--strict-scope` | Two distinct scopes: (1) convergence loop review scope is always "files modified by fixes" (the delta set), (2) `--strict-scope` controls whether fix patches that touch files outside the original review scope are rejected (vs. warned). These are independent: convergence reviews the delta, strict-scope gates what the fix agent can touch. |
| `--converge` + `--profile strat` | Error: "--converge requires --fix, which is code profile only" |
| `--converge` + `--profile rfe` | Error: "--converge requires --fix, which is code profile only" |

### Flag Interaction: Principles & Arch-Context Flags

| Combination | Behavior |
|------------|----------|
| `--principles` + `--profile code` | Error: "--principles is only available for the strat and rfe profiles" |
| `--principles` + `--review-only` | Composable. Principles are injected into review specialists as hard constraints. |
| `--principles` + pipeline mode | Composable. Principles are injected into both refine agents and review specialists. |
| `--arch-context` + `--profile code` | Error: "--arch-context is only available for the strat and rfe profiles" |
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

Read the preset profile table from `profiles/<profile>/PROFILE.md` for the active profile.

### Defaults

- **Profile:** `code` (if `--profile` not specified)
- **Specialists:** All for the active profile (5 for code, 6 for strat, 5 for rfe) if none specified
- **Iterations:** 3 self-refinement rounds (with convergence-based early exit, minimum 2)
- **Budget:** 350K tokens (disable with `--no-budget`)
- **Topic:** Auto-derived from scope (primary directory or file name)

---

### Reference Staleness Check

Before proceeding to scope resolution, run staleness check for each active specialist:

```bash
${CLAUDE_SKILL_DIR}/scripts/discover-references.sh <specialist> --check-staleness
```

Staleness warnings are informational only — they never block the review.

---

## Step 1b: Document Pipeline (Strat/RFE Profile)

When `--profile strat` or `--profile rfe` is active and `--review-only` is NOT specified, delegate to `phases/strat-pipeline.md`. See `profiles/<profile>/PROFILE.md` for the full pipeline description, input detection, and `--review-only` behavior.

After the pipeline completes, proceed to Step 3 (cache initialization), skipping Step 2.

---

## Step 2: Scope Resolution

Delegate to `protocols/scope-resolution.md`. Covers priority chain, sensitive file blocklist, scope file generation, scope confirmation (MANDATORY), scope immutability, size limits, force mode, and pre-flight budget gate.

---

## Step 2b: Deterministic Pre-Analysis (Strat/RFE Profile Only)

Delegate to `protocols/pre-analysis.md`. See `profiles/<profile>/PROFILE.md` for profile-specific details.

---

## Step 3: Initialize Cache

Delegate to `protocols/cache-initialization.md`. Covers the full cache lifecycle: init, populate (code, templates, references, context, constraints), navigation generation, cleanup traps, `--reuse-cache` override, `--delta` auto-discovery, and `--keep-cache` post-review.

---

## Step 3b: External Reference Detection

After cache initialization, scan the cached code for references to resources defined outside the reviewed scope. Delegate to `protocols/external-reference-detection.md`.

This step detects patterns like Go imports from other repos, file paths pointing outside the cache, RBAC `resourceNames:` referencing external objects, and Kustomize overlays referencing external directories. For each detected reference, the orchestrator attempts to resolve it to a fetchable source (git repo, local directory).

**User interaction**: Present detected references to the user. For resolvable references, offer to auto-fetch them as context using the existing `--context` mechanism. For unresolvable references, list them as warnings so agents know their scope has gaps.

**Skipped when**: `--reuse-cache` is active (cache already populated), or `--context` already covers the detected references, or no external references are detected.

---

## Step 4: Phase 1 — Self-Refinement

Delegate to `phases/self-refinement.md`.

### Agent Dispatch Procedure

Agent dispatch uses the local context cache (initialized in Step 3). For the detailed cache-based prompt composition and iteration flow, see `phases/self-refinement.md`.

Summary:

1. **Compose minimal prompt (~2,825 tokens)** — role definition, delimiter values, finding template, and cache navigation block pointing agents to `{CACHE_DIR}`. Agents read code from the cache via the Read tool.

2. **Spawn agents in parallel** — dispatch via the host platform's subagent mechanism. Each agent reads `navigation.md` first, then code files from the cache.

3. **Validate and cache findings** — run `${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-findings` on each agent's output (replaces separate `validate-output.sh` invocation). This validates, sanitizes, splits findings, and generates the summary table.

4. **Track budget** — after each agent completes, update the budget tracker with per-agent tracking.

   ```bash
   ${CLAUDE_SKILL_DIR}/scripts/track-budget.sh add <iteration_char_count> --agent <role_prefix> --per-agent-cap <cap>
   ${CLAUDE_SKILL_DIR}/scripts/track-budget.sh status
   ```

### Iteration Hard Cap and Budget Enforcement

Before dispatching each iteration, the orchestrator checks the applicable conditions. If any fails, stop iterating for that agent and use the last iteration's output.

1. **Iteration hard cap:** `iteration_count < MAX_ITERATIONS` (see `protocols/guardrails.md` for values by profile: default 4, quick 2, thorough 4). If exceeded, emit `FORCED_CONVERGENCE` to the guardrail trip log.
2. **Global budget** (skipped when `--no-budget`)**:** `${CLAUDE_SKILL_DIR}/scripts/track-budget.sh status` must not return `exceeded: true`. If exceeded, emit `BUDGET_EXCEEDED` to the guardrail trip log.
3. **Agent-level budget** (skipped when `--no-budget`)**:** The response from `${CLAUDE_SKILL_DIR}/scripts/track-budget.sh add --agent` must not return `agent_exceeded: true`. If exceeded, emit `AGENT_BUDGET_EXCEEDED` to the guardrail trip log.

After each iteration, check remaining budget (unless `--no-budget`). If budget is exceeded, complete the current iteration but do not start another. Proceed to resolution.

### Severity Inflation Check

After all specialists complete self-refinement, run the severity inflation check:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/severity-check.py {CACHE_DIR}/findings/
```

If `any_inflation` is `true` in the output, emit a `SEVERITY_INFLATION` warning to the guardrail trip log for each flagged specialist. Include the warning in the specialist's challenge round context so challengers can scrutinize severity assignments.

---

## Step 5: Phase 2 — Challenge Round

Delegate to `phases/challenge-round.md`.

In this phase, specialists challenge each other's findings through structured debate. The orchestrator mediates all communication — agents never see each other's raw output. See `protocols/mediated-communication.md` for the mediation protocol. Challenge prompts use `profiles/<profile>/templates/challenge-response-template.md`.

**Single-specialist mode:** When only 1 specialist is active, Phase 2 runs a devil's advocate pass instead of cross-agent debate (see `profiles/<profile>/agents/devils-advocate.md` and the Single-Specialist Mode section in `phases/challenge-round.md`). Phase 2 is NOT skipped — it runs in devil's advocate mode.

---

## Step 6: Phase 3 — Resolution

Delegate to `phases/resolution.md`.

The orchestrator synthesizes challenges and defenses, applies consensus rules, and produces the final validated finding set. Convergence detection uses `${CLAUDE_SKILL_DIR}/scripts/detect-convergence.sh`. Deduplication uses `${CLAUDE_SKILL_DIR}/scripts/deduplicate.sh`.

**Cache interaction:** Phase 3 reads deduplicated findings from `{CACHE_DIR}/findings/`. No cache writes — deduplication and ranking operate on the finding files already in the cache.

---

## Step 7: Phase 4 — Report

Delegate to `phases/report.md`.

Generate the final report using the profile's report template: `profiles/<profile>/templates/report-template.md` (or `profiles/code/templates/delta-report-template.md` for delta mode, code profile only). See `profiles/<profile>/PROFILE.md` for the report section list and any additional outputs.

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

**Only when `--fix` is specified. Code profile only.** Delegate to `phases/remediation.md`. If `--fix` is used with `--profile strat` or `--profile rfe`, emit an error: "Phase 5 (Remediation) is not available for the strat/rfe profile. Document findings require manual revision."

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
| Budget exceeded mid-iteration | Complete current iteration, stop further iterations. If in Phase 1: skip Phase 2 and proceed to Phase 3 (No-Debate Resolution). If in Phase 2: proceed to Phase 3 with positions collected so far. Not applicable when `--no-budget` is active. |
| No shell execution available | Fall back to LLM-based validation with disclaimer in report |
| All findings dismissed in challenge | Report with "all clear" executive summary |

### Cache Errors

| Scenario | Response |
|----------|----------|
| `${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh init` fails | Abort review with error |
| `populate-code` fails (collision, missing file) | Abort review — cache integrity cannot be guaranteed |
| `populate-templates` or `populate-references` fails | Abort review — agents need templates and references |
| `populate-findings` fails | Spawn fresh agent with error, max 2 retries. Exclude agent if retries exhausted. |
| `validate-cache` fails on `--reuse-cache` | Abort with mismatch details |
| `generate-navigation` fails | Non-fatal warning — agents use mandatory reads list from prompt |
| Cache directory disappears mid-review | Abort review — unrecoverable |
| `last-cache.json` missing on `--delta` | Treat as not found — create new cache, inform user |

---

## Operational Protocols

The orchestrator maintains a guardrail trip log (in-memory list of `{timestamp, guardrail_id, agent, details}` entries). Events are appended when guardrails fire and rendered in the report's "Guardrails Triggered" section.

Budget management uses `${CLAUDE_SKILL_DIR}/scripts/track-budget.sh`. When `--no-budget` is active, initialize with limit `0` (unlimited mode). If `status` returns `"exceeded": true`, do not start the next iteration.

### Protocol & Phase Index

All files the orchestrator reads during a review. Each is one hop from SKILL.md:

| File | Purpose |
|------|---------|
| [phases/self-refinement.md](phases/self-refinement.md) | Phase 1: agent dispatch, iteration, convergence |
| [phases/challenge-round.md](phases/challenge-round.md) | Phase 2: cross-agent debate, devil's advocate |
| [phases/resolution.md](phases/resolution.md) | Phase 3: consensus rules, deduplication, ranking |
| [phases/report.md](phases/report.md) | Phase 4: report generation, additional outputs |
| [phases/remediation.md](phases/remediation.md) | Phase 5: classification, fixes, worktrees, PRs, convergence loop |
| [phases/strat-pipeline.md](phases/strat-pipeline.md) | Step 1b: create, refine, mediate pipeline |
| [protocols/scope-resolution.md](protocols/scope-resolution.md) | Priority chain, blocklist, scope confirmation, pre-flight gate |
| [protocols/cache-initialization.md](protocols/cache-initialization.md) | Cache lifecycle: init, populate, navigate, cleanup |
| [protocols/external-reference-detection.md](protocols/external-reference-detection.md) | Step 3b: detect external refs, auto-fetch, scope warnings |
| [protocols/token-budget.md](protocols/token-budget.md) | Budget init, tracking, rebalance, unlimited mode |
| [protocols/guardrails.md](protocols/guardrails.md) | Guardrail definitions, constants, enforcement |
| [protocols/convergence-detection.md](protocols/convergence-detection.md) | Finding-set diff between iterations |
| [protocols/mediated-communication.md](protocols/mediated-communication.md) | Cross-agent message sanitization |
| [protocols/input-isolation.md](protocols/input-isolation.md) | Delimiter generation, NFKC normalization |
| [protocols/injection-resistance.md](protocols/injection-resistance.md) | Injection heuristics, defense patterns |
| [protocols/delta-mode.md](protocols/delta-mode.md) | Re-review changed files only |
| [protocols/diff-triage-mode.md](protocols/diff-triage-mode.md) | Change-impact graph, external comment triage |
| [protocols/pre-analysis.md](protocols/pre-analysis.md) | Threat surface, NFR scan, persistence, normalization |
| [protocols/principles.md](protocols/principles.md) | Design principles YAML injection |
| [protocols/idempotency.md](protocols/idempotency.md) | Duplicate detection for Jira/PR creation |
| [protocols/progress-display.md](protocols/progress-display.md) | Status block format, budget bar |
| [protocols/audit-log.md](protocols/audit-log.md) | External action logging for --fix and --triage modes |

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
