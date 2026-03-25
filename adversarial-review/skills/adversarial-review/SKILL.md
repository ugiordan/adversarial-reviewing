---
name: adversarial-review
description: Multi-agent adversarial review with isolated specialists, programmatic validation, and consensus-based findings. Use for reviewing code, designs, or documentation from multiple perspectives.
---

# Adversarial Review

## Overview

This skill spawns multiple specialist sub-agents in fully isolated environments to review code, documentation, or designs from different perspectives. Agents self-refine their findings through internal iteration. The orchestrator mediates all cross-agent communication with programmatic validation via shell scripts — agents never see each other's raw output. All findings require consensus before reaching the user.

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
- [ ] **Step 3:** Phase 1 — Self-refinement (delegate to `phases/self-refinement.md`)
- [ ] **Step 4:** Phase 2 — Challenge round (delegate to `phases/challenge-round.md`; devil's advocate mode if single-specialist)
- [ ] **Step 5:** Phase 3 — Resolution (delegate to `phases/resolution.md`; simplified if single-specialist)
- [ ] **Step 6:** Phase 4 — Report (delegate to `phases/report.md`)
- [ ] **Step 7:** Phase 5 — Remediation (delegate to `phases/remediation.md`; only when `--fix`)

---

## Step 1: Invocation Parsing

Parse the user's invocation to determine specialist selection, mode, and budget.

### Specialist Flags

| Flag | Specialist | Agent File |
|------|-----------|------------|
| `--security` | Security Auditor | `agents/security-auditor.md` |
| `--performance` | Performance Analyst | `agents/performance-analyst.md` |
| `--quality` | Code Quality Reviewer | `agents/code-quality-reviewer.md` |
| `--correctness` | Correctness Verifier | `agents/correctness-verifier.md` |
| `--architecture` | Architecture Reviewer | `agents/architecture-reviewer.md` |

If no specialist flags are provided, activate **all 5 specialists**.

### Mode Flags

| Flag | Effect |
|------|--------|
| `--delta` | Delta mode — re-review only changes since last review. Also overrides max iterations to 2 (matching minimum, so exactly 2 iterations always run). See `protocols/delta-mode.md`. |
| `--save` | Write report to file. Does NOT commit to git. |
| `--topic <name>` | Override the auto-derived topic name for the review. |
| `--budget <tokens>` | Override the default 500K token budget. |
| `--force` | Override the 200-file hard ceiling. Requires explicit budget confirmation. |
| `--fix` | Enable Phase 5 (Remediation). Classifies findings, drafts Jiras, creates worktree branches, implements fixes, and proposes PRs. |
| `--diff` | Enable diff-augmented input with change-impact graph. Auto-enabled by `--delta`. |
| `--diff --range <range>` | Specify git commit range for diff (e.g., `main..HEAD`, `HEAD~3..HEAD`) |
| `--triage <source>` | Evaluate external review comments. Source: `pr:<N>`, `file:<path>`, or `-` (stdin) |
| `--gap-analysis` | Include coverage gap analysis in triage report (auto-enabled by `--thorough --triage`) |

### Preset Profiles

| Flag | Specialists | Iterations | Budget |
|------|------------|------------|--------|
| `--quick` | 2 (Security + Correctness) | 2 (min=max, convergence check runs but early exit cannot trigger) | 200K |
| `--thorough` | 5 (all) | 3 | 800K |
| *(default)* | All specified or all 5 | 3 (convergence exit) | 500K |

### Defaults

- **Specialists:** All 5 (if none specified)
- **Iterations:** 3 self-refinement rounds (with convergence-based early exit, minimum 2)
- **Budget:** 500K tokens
- **Topic:** Auto-derived from scope (primary directory or file name)

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

## Step 3: Phase 1 — Self-Refinement

Delegate to `phases/self-refinement.md`.

### Agent Dispatch Procedure

For each active specialist:

1. **Generate delimiters** — Run `scripts/generate-delimiters.sh` on the input files to produce unique random delimiters for wrapping code. Each agent receives its own delimiter pair. See `protocols/input-isolation.md`.

   ```bash
   scripts/generate-delimiters.sh <code_file>
   ```

2. **Compose agent prompt** — Assemble the full prompt containing:
   - The specialist's role prompt from `agents/<specialist>.md` (includes inoculation instructions)
   - The code under review wrapped in the generated delimiters
   - Reference to `templates/finding-template.md` for output format
   - Self-refinement instructions from the phase file

3. **Spawn agent** — Dispatch via the host platform's subagent mechanism (e.g., Agent tool in Claude Code, agent spawn in other platforms). Each agent runs in isolation — agents never see each other's output during this phase.

4. **Validate output** — Run `scripts/validate-output.sh` on each agent's response to ensure structural compliance with the finding template.

   ```bash
   scripts/validate-output.sh <agent_output_file> <role_prefix>
   ```

5. **Track budget** — After each agent completes, update the budget tracker.

   ```bash
   scripts/track-budget.sh add <iteration_char_count>
   scripts/track-budget.sh status
   ```

### Budget Check

After each iteration, check remaining budget. If budget is exceeded, complete the current iteration but do not start another. Proceed to resolution.

---

## Step 4: Phase 2 — Challenge Round

Delegate to `phases/challenge-round.md`.

In this phase, specialists challenge each other's findings through structured debate. The orchestrator mediates all communication — agents never see each other's raw output. See `protocols/mediated-communication.md` for the mediation protocol. Challenge prompts use `templates/challenge-response-template.md`.

**Single-specialist mode:** When only 1 specialist is active, Phase 2 runs a devil's advocate pass instead of cross-agent debate (see `agents/devils-advocate.md` and the Single-Specialist Mode section in `phases/challenge-round.md`). Phase 2 is NOT skipped — it runs in devil's advocate mode.

---

## Step 5: Phase 3 — Resolution

Delegate to `phases/resolution.md`.

The orchestrator synthesizes challenges and defenses, applies consensus rules, and produces the final validated finding set. Convergence detection uses `scripts/detect-convergence.sh`. Deduplication uses `scripts/deduplicate.sh`.

---

## Step 6: Phase 4 — Report

Delegate to `phases/report.md`.

Generate the final report using `templates/report-template.md` (or `templates/delta-report-template.md` for delta mode). The report includes 9 sections:

- Executive summary
- Validated findings with consensus status (Sections 2-5)
- Dismissed findings (Section 6)
- Challenge round findings (Section 7)
- Co-located findings (Section 8)
- **Remediation summary** (Section 9) — severity-sorted action list with remediation roadmap, blocked items, and top priorities. Always present, even without `--fix`.

If `--save` was specified, write the report to `docs/reviews/YYYY-MM-DD-<topic>-review.md`.

**NEVER auto-commit.** The `--save` flag writes the file only.

---

## Single-Specialist Mode

When only one specialist is active (e.g., `--security` alone), the full multi-agent protocol is unnecessary. Instead:

1. **Phase 1: Self-refinement** — The specialist reviews and self-refines as normal
2. **Phase 2: Devil's advocate pass** — Instead of cross-agent debate, Phase 2 runs using `agents/devils-advocate.md` to challenge the specialist's findings. The originator responds once. See `phases/challenge-round.md` Single-Specialist Mode section.
3. **Phase 3: Simplified resolution** — Findings the specialist maintained are included with reduced-confidence flag. Findings withdrawn or conceded are dismissed. See `phases/resolution.md` Single-Specialist Mode section.
4. **Phase 4: Report** — Generate report with a disclaimer noting that findings were not cross-validated by other specialists
5. **Phase 5: Remediation** — Runs normally when `--fix` is specified (independent of specialist count)

---

## Step 7: Phase 5 — Remediation

**Only when `--fix` is specified.** Delegate to `phases/remediation.md`.

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

---

## Task Tracking

Create tasks dynamically based on specialist count and phase progression. Example for a 5-specialist, 2-iteration review:

```
Task: Parse invocation and resolve scope          [Step 1-2]
Task: SEC self-refinement (iteration 1)            [Step 3]
Task: PERF self-refinement (iteration 1)           [Step 3]
Task: QUAL self-refinement (iteration 1)           [Step 3]
Task: CORR self-refinement (iteration 1)           [Step 3]
Task: ARCH self-refinement (iteration 1)           [Step 3]
Task: SEC self-refinement (iteration 2)            [Step 3]
Task: PERF self-refinement (iteration 2)           [Step 3]
Task: QUAL self-refinement (iteration 2)           [Step 3]
Task: CORR self-refinement (iteration 2)           [Step 3]
Task: ARCH self-refinement (iteration 2)           [Step 3]
Task: Challenge round                              [Step 4]
Task: Resolution                                   [Step 5]
Task: Final report                                 [Step 6]
Task: Classify findings (jira/chore/blocked)       [Step 7, --fix only]
Task: Draft Jira tickets                           [Step 7, --fix only]
Task: Implement fixes (per work item)              [Step 7, --fix only]
Task: Propose PRs                                  [Step 7, --fix only]
```

Update task status as each completes. For single-specialist mode, Phase 2 runs in devil's advocate mode (not skipped). Phase 5 tasks are only created when `--fix` is specified.

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
  agents/
    security-auditor.md                 # SEC specialist prompt
    performance-analyst.md              # PERF specialist prompt
    code-quality-reviewer.md            # QUAL specialist prompt
    correctness-verifier.md             # CORR specialist prompt
    architecture-reviewer.md            # ARCH specialist prompt
    devils-advocate.md                  # Single-specialist challenge agent
  phases/
    self-refinement.md                  # Phase 1 procedure
    challenge-round.md                  # Phase 2 procedure
    resolution.md                       # Phase 3 procedure
    report.md                           # Phase 4 procedure
    remediation.md                      # Phase 5 procedure (--fix)
  protocols/
    input-isolation.md                  # Delimiter-based code isolation
    mediated-communication.md           # Cross-agent message mediation
    convergence-detection.md            # Finding set stability detection
    delta-mode.md                       # Re-review protocol
    token-budget.md                     # Budget tracking protocol
    injection-resistance.md             # Two-tier injection detection
  scripts/
    generate-delimiters.sh              # Produces unique code delimiters
    validate-output.sh                  # Validates agent output structure
    detect-convergence.sh               # Checks finding set stability
    deduplicate.sh                      # Removes duplicate findings
    track-budget.sh                     # Token budget tracking
  templates/
    finding-template.md                 # Required output format for findings
    challenge-response-template.md      # Challenge/defense exchange format
    report-template.md                  # Final report format
    delta-report-template.md            # Delta review report format
    sanitized-document-template.md      # Sanitized cross-agent message format
    jira-template.md                    # Jira ticket template (--fix)
  tests/
    run-all-tests.sh                    # Test runner
    test-validation-script.sh           # Validation script tests
    test-single-agent.sh                # Single-agent pipeline integration tests
    test-injection-resistance.sh        # Injection resistance tests
    test-coverage-gaps.sh               # Coverage gap and edge case tests
    fixtures/
      sample-code.py                    # Sample code for testing
      sample-code-with-injection.py     # Code with embedded injection attempts
      valid-finding.txt                 # Valid finding for test input
      valid-finding-2.txt               # Second valid finding (different specialist)
      valid-finding-perf.txt            # Valid PERF finding
      malformed-finding.txt             # Malformed finding for test input
      injection-finding.txt             # Finding containing injection patterns
      provenance-injection-finding.txt  # Finding with provenance marker injection
      no-findings.txt                   # Zero-finding output (NO_FINDINGS_REPORTED)
      changed-finding.txt              # Modified finding for convergence tests
      two-findings-overlap.txt          # Overlapping findings for dedup tests
      two-findings-nonoverlap.txt       # Non-overlapping findings for dedup tests
      expected-findings.md              # Expected findings reference
      sample-prior-report.md            # Prior report for delta mode tests
```

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

| Fix votes | No-Fix votes | Investigate votes | Result |
|-----------|-------------|-------------------|--------|
| All | 0 | 0 | **Fix** (consensus) |
| 0 | All | 0 | **No-Fix** (consensus) |
| >= majority | < majority | any | **Fix** (majority, note dissent) |
| < majority | >= majority | any | **No-Fix** (majority, note dissent) |
| < majority | < majority | >= 1 | **Investigate** (no majority) |

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
