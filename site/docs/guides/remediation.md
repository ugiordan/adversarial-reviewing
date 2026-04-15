# Remediation

Phase 5 generates and applies fixes for confirmed findings. It requires explicit user confirmation at every step.

## Activation

```bash
# Full review with remediation
/adversarial-review src/ --fix

# Preview without writing anything
/adversarial-review src/ --fix --dry-run
```

## Pipeline

```mermaid
flowchart LR
    CLASSIFY["Classify findings"] --> |"jira / chore / blocked"| GATE1{{"User confirms\nclassification"}}
    GATE1 --> DRAFT["Draft Jira tickets"]
    DRAFT --> GATE2{{"User confirms\ntickets"}}
    GATE2 --> WORKTREE["Create worktree\nbranches"]
    WORKTREE --> IMPLEMENT["Implement fixes"]
    IMPLEMENT --> GATE3{{"User confirms\nPRs"}}

    style GATE1 fill:#ffe6e6,stroke:#cc4444
    style GATE2 fill:#ffe6e6,stroke:#cc4444
    style GATE3 fill:#ffe6e6,stroke:#cc4444
```

Every red gate requires explicit user confirmation before proceeding.

## Step 1: Classification

Each finding is classified into one of:

| Category | Description |
|----------|-------------|
| **jira** | Needs a tracked ticket (security fixes, breaking changes) |
| **chore** | Simple fix that can be done inline (typos, minor refactors) |
| **blocked** | Cannot be fixed without more context or upstream changes |

The user reviews and confirms the classification before any action.

## Step 2: Jira ticket drafts

For findings classified as `jira`, the system drafts tickets using the Jira template:

- Title, description, acceptance criteria
- Priority mapped from finding severity
- Labels derived from specialist domain

Tickets are presented for review. The user decides which to actually create.

## Step 3: Worktree branches

For findings that will be fixed:

- Each fix gets its own git worktree branch
- Branch names follow the pattern `fix/<finding-id>-<short-description>`
- The orchestrator never pushes, force-pushes, or targets main/master

## Step 4: Implementation

Fixes are implemented in the worktree branches. Each fix is scoped to its finding. The destructive pattern check scans all recommended fixes for dangerous operations (rm -rf, DROP TABLE, force-push, etc.) before applying.

## Step 5: Fix verification

After each fix is committed, the original specialist agent is re-invoked on the modified files to verify the finding is resolved:

1. The specialist role is extracted from the finding ID prefix (e.g., `SEC-003` uses the Security Auditor)
2. The specialist reviews the fixed code with the original finding as context
3. If the finding is no longer reproduced, the fix is verified
4. If the finding persists, the fix is marked as "incomplete" and the user can: accept the partial fix, request one more attempt, or revert

This prevents shipping fixes that don't actually address the issue. It adds one specialist invocation per fix but catches incomplete remediations before they reach PR review.

## Dry run mode

Preview what the remediation would do without writing anything:

```bash
/adversarial-review src/ --fix --dry-run
```

This runs the full classification and shows the proposed Jira drafts, branch names, and fix descriptions, but writes no files and creates no branches.

## Strict scope

When `--strict-scope` is active, remediation patches that touch files outside the review target are rejected entirely (not just flagged):

```bash
/adversarial-review src/auth/ --fix --strict-scope
```
