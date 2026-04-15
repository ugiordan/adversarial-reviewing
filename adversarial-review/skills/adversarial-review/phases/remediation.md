# Phase 5: Remediation

## Purpose

Classify validated findings into actionable work items, draft Jira tickets where needed, implement fixes using isolated worktrees, and prepare PRs for user approval. This phase is activated by the `--fix` flag.

## Prerequisites

- Phase 4 complete — final report generated with all validated findings
- Git repository is clean (no uncommitted changes)
- User has confirmed they want to proceed with remediation

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

After user approval, create Jira tickets using the MCP Atlassian tools (if available) or present the final descriptions for manual creation.

Record the Jira ticket IDs for use in branch names and PR descriptions.

> **Audit:** Log this action to the audit trail. See `protocols/audit-log.md`.

### Step 5: Implement Fixes

Process work items in this order:
1. Jira groups (larger, more impactful)
2. Chore batches (smaller, straightforward)

**Skip blocked findings** — no worktrees, branches, or implementation. For **Already Fixed** findings with status "Needs PR", skip implementation but include them in Step 6 (Propose PRs).

For each work item (Jira group or chore batch):

#### 5a. Create Worktree

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

Spawn a fix agent in the worktree with:
- The finding details (evidence, file, lines, recommended fix)
- The Jira ticket ID (for commit message reference)
- Instructions to make minimal, focused changes
- Instructions to run existing tests if available

The fix agent should:
1. Read the target files
2. Implement the fix as described in the finding
3. Run any relevant tests
4. Commit with an appropriate message

#### 5b-verify. Verify Fix (post-fix specialist re-check)

After the fix agent commits, re-run the original specialist agent on the modified files to verify the finding is resolved:

1. Extract the specialist role from the finding ID prefix (e.g., `SEC-003` → security-auditor)
2. Re-invoke that specialist on the fixed file(s) only, with the original finding as context
3. Check the specialist's output:
   - **Finding not reproduced**: Fix is verified. Proceed to next work item.
   - **Finding still present**: Mark fix as `incomplete`. Present the specialist's updated assessment to the user with the option to:
     (a) Accept the partial fix as-is
     (b) Request a second fix attempt (max 1 retry)
     (c) Skip the fix and revert the commit

This step prevents shipping fixes that don't actually resolve the issue. It adds one specialist invocation per fix but catches incomplete remediations before they reach PR review.

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
1. List all worktrees created during remediation
2. Ask user if they should be cleaned up
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

## Cache Interaction

Unless `--keep-cache` is specified, the cleanup trap (set during cache initialization) removes the cache directory after Phase 5 completes. If `--keep-cache` is active, the trap is skipped and the cache is preserved for future `--reuse-cache` use.

Note: in agent-tool execution models (e.g., Claude Code), the trap may not persist across Bash tool invocations. The `cleanup_stale` function in `manage-cache.sh` provides a reliability backstop, removing caches older than 24 hours with dead orchestrator PIDs.

## References

- `templates/jira-template.md` — Jira ticket description template
- `templates/report-template.md` — finding format for reference
- `scripts/manage-cache.sh` — cache management and cleanup
- `protocols/guardrails.md` — guardrail definitions, constants, enforcement behavior
- `protocols/audit-log.md` — external action audit log format
- `protocols/destructive-patterns.txt` — regex patterns for destructive command detection
