# Idempotency Protocol

## Purpose

Prevents duplicate side effects when the skill is re-run on the same codebase or when Phase 5 remediation is retried. The orchestrator performs these checks before every write operation.

## Report File (`--save`)

Before writing any report file (`docs/reviews/YYYY-MM-DD-<topic>-review.md`, `-requirements.md`, `-findings.json`):

1. Check if the target file already exists
2. If it exists, read its metadata block and compare:
   - Commit SHA (same commit = same code reviewed)
   - Specialist set (same agents = comparable results)
   - Review date
3. Present to user:
   ```
   Report already exists: docs/reviews/2026-04-20-auth-review.md
   Previous: commit abc123, specialists: SEC+CORR, date: 2026-04-20
   Current:  commit def456, specialists: SEC+CORR+ARCH, date: 2026-04-20
   Options: [overwrite] [rename existing to .bak] [abort save]
   ```
4. Proceed only after user chooses

## Finding History (`--persist`)

Before appending to `.adversarial-review/findings-history.jsonl`:

1. Read the last line of the history file (if it exists)
2. Parse its `commit_sha` field
3. If `commit_sha` matches current `git rev-parse HEAD`: skip the append (same commit produces same findings)
4. If different or file doesn't exist: append normally

## Cache State (`--keep-cache`)

Before writing `.adversarial-review/last-cache.json`:

1. Check if the file exists
2. If exists, read its `commit_sha` field
3. If `commit_sha` matches current HEAD: skip write (cache pointer is current)
4. If different: overwrite (new review supersedes old cache reference)

## Jira Tickets (Phase 5)

Before each `acli jira workitem create`:

1. Search for existing tickets with similar summary:
   ```bash
   acli jira workitem search --jql "summary ~ '<finding-title-keywords>' AND project = <PROJECT> AND status != Done" --json
   ```
2. If no matches: proceed with creation
3. If matches found, present to user:
   ```
   Possible existing ticket for finding SEC-001:
     PROJ-456: "SQL injection in auth handler" (status: Open, assignee: unassigned)
   Options: [link to existing] [create new anyway] [skip]
   ```
4. If user chooses "link to existing": use existing ticket ID for branch naming, skip creation
5. Log the decision via `write-audit-log.sh`:
   ```bash
   scripts/write-audit-log.sh jira dedup_match finding=SEC-001 existing=PROJ-456 decision=linked
   ```

## Branches (Phase 5)

Before each `git worktree add -b <branch>`:

1. Check if the branch already exists:
   ```bash
   git branch --list '<branch-name>'
   ```
2. If branch does not exist: proceed normally
3. If branch exists, check its state:
   ```bash
   git log --oneline -1 <branch-name>
   ```
4. Present to user:
   ```
   Branch fix/PROJ-123-rbac-hardening already exists
   Last commit: abc1234 fix(auth): harden RBAC permissions (2 days ago)
   Options: [reuse branch] [create with suffix -v2] [abort]
   ```
5. If reusing: `git worktree add /tmp/fix-<id> <existing-branch>` (no `-b` flag)
6. If creating with suffix: `git worktree add /tmp/fix-<id> -b <branch>-v2 <base>`

## PRs (Phase 5)

Before each `gh pr create`:

1. Check for existing open PR on the branch:
   ```bash
   gh pr list --head <branch-name> --state open --json number,title,url
   ```
2. If no open PR: proceed with creation
3. If open PR exists, present to user:
   ```
   Open PR already exists for branch fix/PROJ-123-rbac-hardening:
     #42: "fix: harden RBAC permissions" (https://github.com/org/repo/pull/42)
   Options: [skip PR creation] [update PR description]
   ```
4. If updating: use `gh pr edit <number> --body <updated-body>` instead of creating new

## Audit Log

No idempotency check required. Audit entries are append-only with timestamps. Duplicate entries from re-runs are acceptable since they accurately document what actions were attempted. The timestamp differentiates runs.
