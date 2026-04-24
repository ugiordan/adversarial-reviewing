# Phase 5: Remediation
## Contents

- [Purpose](#purpose)
- [Prerequisites](#prerequisites)
- [Dry-Run Mode (`--fix --dry-run`)](#dry-run-mode-fix-dry-run)
- [Procedure](#procedure)
- [Branch Naming Conventions](#branch-naming-conventions)
- [Error Handling](#error-handling)
- [Guardrails](#guardrails)
- [Convergence Loop (`--converge`)](#convergence-loop-converge)
- [Cache Interaction](#cache-interaction)
- [References](#references)

## Purpose

Classify validated findings into actionable work items, draft Jira tickets where needed, implement fixes using isolated worktrees, and prepare PRs for user approval. This phase is activated by the `--fix` flag.

## Prerequisites

- Phase 4 complete — final report generated with all validated findings
- Git repository is clean (no uncommitted changes)
- User has confirmed they want to proceed with remediation. This is **Gate 1** of the remediation confirmation gates.

## Dry-Run Mode (`--fix --dry-run`)

When `--dry-run` is specified alongside `--fix`, the full remediation pipeline runs but writes nothing:

- Classification: computed and displayed, not persisted.
- Jira tickets: drafted and displayed, not created.
- Code patches: generated and displayed as unified diffs, not applied.
- Branches/PRs: described but not created.
- No user confirmation gates fire (nothing to confirm).
- Audit log entries are prefixed with `[DRY-RUN]` (see `protocols/audit-log.md`).

Output appears in the `## Remediation Preview` report section.

## Procedure

### Step 1: Classify Findings

Classify each validated finding as `jira`, `chore`, or `blocked`.

#### Classification Criteria

A finding is **`jira`** when ANY of the following apply:
- Requires a design decision (multiple valid fix approaches exist)
- Has backward compatibility implications (changing defaults, removing fields, altering API behavior)
- Touches multiple components or teams (cross-team review needed)
- Needs investigation before fixing (e.g., "is this RBAC permission actually used?")
- Security vulnerability with user-facing impact that needs release notes
- Fix involves architectural changes (e.g., replacing a pattern across many files)
- Severity is Important+ AND the fix is non-trivial (>20 lines changed or >2 files)

A finding is **`chore`** when ALL of the following apply:
- Fix is self-contained and obvious (no design decision)
- No backward compatibility concerns
- Confined to a single component/team
- Does not need investigation — the fix is clear from the finding
- Typically: one-line fixes, adding validation, fixing obvious bugs, hardening

A finding is **`blocked`** when ANY of the following apply:
- Requires external approval before any work can start (e.g., architect sign-off on a new library or pattern)
- Depends on a cross-team decision that hasn't been made yet
- Requires an upstream change or dependency that isn't available
- The fix approach itself needs RFC/proposal review before implementation
- Organizational process requires sign-off before a PR can be opened (e.g., new dependency approval)

For blocked findings, always specify:
1. **What** is blocked (the finding or group of findings)
2. **Why** it's blocked (the specific approval, decision, or dependency needed)
3. **Who** needs to unblock it (team, role, or person)
4. **What happens after** it's unblocked (will it become a Jira or chore?)

#### Output Format

Present the classification table to the user:

```
## Finding Classification

### Actionable (Jira)
| ID | Severity | Title | Jira Group | Reason |
|----|----------|-------|------------|--------|
| ... | ... | ... | JIRA-N | ... |

### Actionable (Chore)
| ID | Severity | Title | Chore Batch | Fix Summary |
|----|----------|-------|-------------|-------------|
| ... | ... | ... | CHORE-N | ... |

### Blocked/Deferred
| ID | Severity | Title | Blocker | Unblocked by | After unblock |
|----|----------|-------|---------|-------------|---------------|
| ... | ... | ... | <what's blocking> | <who/what unblocks> | Jira / Chore |

### Already Fixed
| ID | Severity | Title | Branch | Status |
|----|----------|-------|--------|--------|
| ... | ... | ... | fix/branch-name | Needs PR / PR open / Merged |
```

**Already Fixed** findings are identified by checking for existing fix branches (via `git branch --list 'fix/*'` or user-provided branch references). They are not classified as jira/chore/blocked — they have their own section showing branch name and PR status (Needs PR / PR open / Merged).

**Wait for user confirmation** of the classification before proceeding. This is **Gate 2** of the remediation confirmation gates.

**Edge case: no actionable findings.** If all findings are classified as blocked or already-fixed (zero jira + zero chore findings), skip Steps 2-5. If any already-fixed findings have status "Needs PR", proceed directly to Step 6 (Propose PRs) with those branches only. Otherwise, proceed to Step 7 (Cleanup) or exit if no worktrees exist.

### Step 2: Group Related Findings

Group findings into logical work units. **Only `jira` and `chore` findings are grouped.** Blocked findings are not grouped — they remain individually listed. Already-fixed findings skip grouping entirely.

**Jira groups:** Related findings that should be tracked by a single Jira ticket. Group by:
- Same root cause (e.g., all RBAC overprivilege findings)
- Same file/component area
- Same fix approach (e.g., all "add CEL validation" findings)

If a logical group contains both actionable and blocked findings, **split the group**. The actionable findings form the Jira ticket. The blocked findings are listed in the ticket's References section as deferred related work but are not included in Acceptance Criteria.

**Chore batches:** Related chore findings that can share a single branch and PR. Rules:
- Maximum 8-10 findings per chore batch (keeps PRs reviewable)
- Only batch findings that touch related code areas
- Unrelated chores get separate batches
- Each batch gets one branch and one PR

### Step 3: Draft Jira Tickets

For each Jira group, generate a ticket using `templates/jira-template.md`. Blocked findings do **not** receive Jira drafts, even if their "After unblock" classification is Jira — tickets for blocked items are created only after the blocker is resolved.

Present ALL Jira drafts to the user at once:

```
## Jira Ticket Drafts

### JIRA-1: [Title]
[Full Jira description from template]

---

### JIRA-2: [Title]
[Full Jira description from template]

...
```

**Wait for user confirmation.** This is **Gate 3** of the remediation confirmation gates. The user may:
- Approve all tickets as-is
- Request changes to specific tickets
- Merge or split tickets
- Remove tickets they don't want created

Do NOT create any Jira tickets until the user explicitly approves.

### Step 4: Create Jira Tickets

After user approval, create Jira tickets using the `acli` CLI (`acli jira workitem create --project <PROJECT> --type Bug --summary "<title>" --description "<wiki-markup>"`). If `acli` is not available, present the final descriptions for manual creation.

**Idempotency:** Before creating each ticket, follow the Jira Tickets check in `protocols/idempotency.md`. Search for existing tickets with matching summary to avoid duplicates.

Record the Jira ticket IDs for use in branch names and PR descriptions.

**Partial failure:** If ticket creation succeeds for some tickets but fails for others: (1) Record which tickets succeeded (with IDs) and which failed (with error messages). (2) Present failed ticket descriptions to the user for manual creation or retry. (3) Ask the user whether to wait for manual ticket IDs or proceed immediately with placeholder branch names (`fix/pending-jira-<N>-<description>`). (4) If placeholders are used, flag them for manual ticket association in Step 7 (Cleanup).

> **Audit:** Log this action to the audit trail. See `protocols/audit-log.md`.

### Step 5: Implement Fixes

Process work items in this order:
1. Jira groups (larger, more impactful)
2. Chore batches (smaller, straightforward)

**Skip blocked findings** — no worktrees, branches, or implementation. For **Already Fixed** findings with status "Needs PR", skip implementation but include them in Step 6 (Propose PRs).

For each work item (Jira group or chore batch):

#### 5a. Create Worktree

**Idempotency:** Before creating each branch, follow the Branches check in `protocols/idempotency.md`. Check for existing branches to avoid conflicts.

Use `isolation: "worktree"` when spawning fix agents, OR create worktrees manually:

```bash
# For Jira-tracked work
git worktree add /tmp/fix-<jira-id> -b fix/<jira-id>-<short-description> <base-branch>

# For chore batches
git worktree add /tmp/chore-<batch-id> -b chore/security-hardening-batch-<N> <base-branch>
```

Base branch should be `upstream/main` or the project's default branch.

> **Audit:** Log this action to the audit trail. See `protocols/audit-log.md`.

#### 5b. Implement Fix

**Before spawning the fix agent**, record the current commit SHA as the pre-fix rollback target: `PRE_FIX_SHA=$(git rev-parse HEAD)`. This SHA is used by Step 5b-verify to revert failed fixes.

Load the fix agent role from `profiles/code/agents/fix-agent.md` and spawn it in the worktree with:
- The fix agent role definition
- A populated Fix Context block containing: finding ID, severity, file, lines, title, evidence, recommended fix, work item type, Jira ID (if applicable), and commit message format
- For chore batches: all findings in the batch, processed sequentially

The fix agent reads target files, implements the minimal fix, runs tests if detectable, and commits with the appropriate message format. It emits a structured `FIX_RESULT` block that the orchestrator parses to determine next steps. See `fix-agent.md` for the complete agent protocol.

#### 5b-verify. Verify Fix (fresh-context validation)

After the fix agent commits, verify the fix using a **fresh-context** specialist invocation. The validator has no knowledge of the original finding, eliminating confirmation bias.

1. **Confirm rollback target:** Verify `PRE_FIX_SHA` (recorded in Step 5b before the fix agent ran) is still valid: `git rev-parse --verify $PRE_FIX_SHA`. This is the state to revert to if the fix fails validation.
2. Extract the specialist role from the finding ID prefix (e.g., `SEC-003` → security-auditor)
3. Spawn a **new** agent with the same specialist role but **without** the original finding context. Give it only:
   - The patched file(s)
   - The specialist's standard role definition and review instructions
   - For **Critical** findings only: a targeted hint restricted to file path and line range (e.g., `{"file": "api/proxy.go", "lines": "45-60"}`). No domain keywords, no semantic description. Validate the hint against this schema before passing to the agent.
4. Ask the agent: "Review this code for issues in your domain"
5. **Sanitize output:** Run the fresh agent's output through `validate-output.sh` (or `manage-cache.sh populate-findings`) before parsing. This applies the same format validation, sanitization, and delimiter checks used for Phase 1 agent outputs.
6. Check the sanitized output:
   - **Original issue not found (and no other issues)**: Fix is verified. Proceed to next work item. If the fix diff is non-trivial (>10 lines changed) and the original severity was Minor, log an informational note: "Fresh validator found no issues. Verify the original finding was not a false positive."
   - **Original issue found independently**: Fix failed. `git reset --hard <known-good-SHA>` to cleanly revert (safe in isolated worktree on unpushed branch). Retry once with the fresh agent's assessment as feedback to the fix agent.
   - **Different issue found**: Log as a new finding. Before assuming the original fix worked, verify the fix diff actually modifies the lines/pattern identified in the original finding (syntactic check against the finding's File/Lines fields). If the diff does not touch the relevant code, treat as "fix failed" instead. Otherwise proceed with the original fix and queue the new finding for the next remediation pass or `--converge` cycle.
7. If retry also fails (fresh agent still finds the issue):
   - `git reset --hard <known-good-SHA>` to cleanly revert
   - Present the finding + failed fix diff + fresh agent's assessment to the user
   - User decides: (a) accept the last attempt as-is, (b) skip the fix entirely (revert stands), (c) manually intervene

**Why fresh-context?** A biased validator (same agent, same finding context) will confirm its own recommendation was implemented correctly. A fresh agent evaluates the code on its own merits. If the original finding was a false positive, the fresh agent won't flag it. Without `--converge`, a false-positive fix ships with an informational note; with `--converge`, the delta review catches regressions from unnecessary fixes.

**Cost:** ~8-10K tokens per finding (single-file, single-specialist, 1 iteration). With retry: ~16-20K. For chore batches (up to 8-10 findings), validation runs per-finding, so budget is 8-10K * N_findings per batch.

**Batch early termination:** For chore batches, if any finding fails validation (including retry), halt further validations for that batch. Present the user with: (1) which findings in the batch succeeded validation, (2) which finding failed and why, (3) options: commit only the successful fixes (splitting the batch into a partial PR), revert the entire batch, or manually intervene. Update budget tracking to account for early termination (charge only for validations actually run).

**Budget tracking:** Update per-work-item estimate to account for validation: 15K fix + (8K * N_findings) validation. For single-finding work items, ~23K. For chore batches of 8, ~79K. Run:
```bash
${CLAUDE_SKILL_DIR}/scripts/track-budget.sh add <validation_char_count> --agent <role_prefix>-verify
```

**Scope Lock:** Before applying any patch, verify all files in the patch are in the review scope (same file list used for `validate-output.sh --scope`). If a patch touches out-of-scope files:
- Default: warn user per-patch. User can approve or skip.
- `--strict-scope`: auto-reject out-of-scope patches.

**Destructive Pattern Check:** Before applying any patch, scan the diff against `protocols/destructive-patterns.txt`. If matched, flag `DESTRUCTIVE_PATTERN` to user before applying.

> **Audit:** Log this action to the audit trail. See `protocols/audit-log.md`.

#### 5c. Commit Message Format

**For Jira-tracked work:**
```
fix(<component>): <short description>

<detailed description of what was fixed and why>

Relates-to: <JIRA-ID>
```

**For chore batches:**
```
chore(<component>): <short description>

<detailed description of hardening/cleanup changes>
```

### Step 6: Propose PRs

After all fixes are committed, present the PR plan to the user:

```
## PR Plan

### Jira PRs
| Branch | Jira | Files Changed | PR Title |
|--------|------|---------------|----------|
| fix/PROJ-123-rbac-hardening | PROJ-123 | 4 | fix: harden RBAC permissions across controllers |

### Chore PRs
| Branch | Findings | Files Changed | PR Title |
|--------|----------|---------------|----------|
| chore/security-hardening-batch-1 | B2-004,B2-008,B2-013 | 3 | chore: security hardening (hash, crypto, file perms) |
```

**Additional sections in the PR plan:**

```
### Already Fixed — Needs PR
| Branch | Findings | Files Changed | PR Title |
|--------|----------|---------------|----------|
| fix/security-audit-batch1 | B1-001,B1-002 | 3 | fix: address auth RBAC bug and ClusterVersion panic |

### Blocked — No Action
| Findings | Blocker | Unblocked by |
|----------|---------|-------------|
| B2-010,B2-011,... | Library needs architect approval | Architecture team |
```

**Wait for user confirmation** before creating any PRs. This is **Gate 4** of the remediation confirmation gates.

**Idempotency:** Before creating each PR, follow the PRs check in `protocols/idempotency.md`. Check for existing open PRs on each branch.

For each approved PR, create it using `gh pr create` with:
- Title from the plan
- Body containing:
  - Summary of findings addressed
  - Jira link (if applicable)
  - List of changes made
  - Test plan

> **Audit:** Log this action to the audit trail. See `protocols/audit-log.md`.

### Step 7: Cleanup

After all PRs are created:
1. List all worktrees created during remediation, categorized by status:
   - **Successful**: PR created, all fixes validated
   - **Partial**: some fixes succeeded, some failed/skipped
   - **Failed**: all fixes failed/skipped, no PR created
2. Ask user separately for each category whether to clean up. Default to keeping Failed/Partial worktrees for investigation.
3. Remove worktrees only with user approval

## Branch Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Jira fix | `fix/<jira-id>-<kebab-description>` | `fix/PROJ-123-rbac-hardening` |
| Chore batch | `chore/security-hardening-batch-<N>` | `chore/security-hardening-batch-1` |
| Single chore | `chore/<kebab-description>` | `chore/fix-file-permissions` |
| Blocked | No branch created | — |
| Already fixed | Pre-existing branch | `fix/security-audit-batch1` |

## Error Handling

| Scenario | Response |
|----------|----------|
| Worktree creation fails | Fall back to regular branch, warn user about isolation loss |
| Fix agent fails | Report failure, skip to next work item, note in PR plan |
| Tests fail after fix | Report test failure, ask user whether to proceed or adjust |
| Jira creation fails | Present ticket description for manual creation, continue with fixes |
| PR creation fails | Present branch name and description for manual PR creation |

## Guardrails

- **NEVER force-push** any branch
- **NEVER push to main/master** directly
- **NEVER create PRs without user confirmation**
- **NEVER create Jira tickets without user confirmation**
- Each worktree is independent — a failure in one does not affect others
- If a fix touches files outside the original finding scope, flag it to the user before committing

## Convergence Loop (`--converge`)

When `--fix --converge` is specified, after the remediation pipeline completes (all fixes applied with fresh-context validation, PRs proposed):

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

**Oscillation detection:** After each cycle, compute finding fingerprints (hash of finding ID + file + line range + severity) and compare against ALL previous cycles' fingerprint sets. If the current cycle's fingerprint set intersects with any previous cycle's set (not just N-2), halt with an oscillation warning: "Fixes are interacting in ways the tool cannot resolve autonomously. Cycle N re-introduced findings from cycle M." This catches both direct (A->B->A) and indirect (A->B->C->A) oscillation patterns.

**Non-convergence exit:** If cycle 3 still has findings:
- Present a convergence failure report: all cycles, what was found, what was fixed, what remains
- User chooses: keep current state, revert to the cleanest cycle (fewest findings), or manually intervene

**Budget** (skipped when `--no-budget`)**:** Two budget checks per cycle:
1. **Pre-cycle gate:** Before starting each cycle, check remaining budget. If remaining budget < estimated cycle cost (~150K for delta-quick + fixes), stop and report "budget insufficient for another convergence cycle." Add `CONVERGE_BUDGET_EXCEEDED` to the guardrail trip log.
2. **Per-cycle ceiling:** Each convergence cycle is hard-capped at 200K tokens. If a cycle exceeds this mid-execution (checked after each agent completes via `${CLAUDE_SKILL_DIR}/scripts/track-budget.sh status`), halt the cycle, present partial results, and ask the user whether to continue with a fresh budget allocation or stop. Add `CONVERGE_CYCLE_CAP_EXCEEDED` to the guardrail trip log.

When `--no-budget` is active, both checks are skipped. The hard cap (3 cycles) and oscillation detection still apply.

Pre-flight estimate for `--converge`: multiply base estimate by 2 (assumes 1 convergence cycle on average).

## Cache Interaction

Unless `--keep-cache` is specified, the cleanup trap (set during cache initialization) removes the cache directory after Phase 5 completes. If `--keep-cache` is active, the trap is skipped and the cache is preserved for future `--reuse-cache` use.

Note: in agent-tool execution models (e.g., Claude Code), the trap may not persist across Bash tool invocations. The `cleanup_stale` function in `manage-cache.sh` provides a reliability backstop, removing caches older than 24 hours with dead orchestrator PIDs.

## References

- `templates/jira-template.md` — Jira ticket description template
- `templates/report-template.md` — finding format for reference
- `${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh` — cache management and cleanup
- `protocols/guardrails.md` — guardrail definitions, constants, enforcement behavior
- `protocols/audit-log.md` — external action audit log format
- `protocols/destructive-patterns.txt` — regex patterns for destructive command detection
