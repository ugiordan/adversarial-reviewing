# Audit Log Protocol

## Purpose

Records all external actions taken during `--fix` and `--triage` modes for accountability and reproducibility.

## Format

Each entry is a single line:

```
[<ISO-8601-timestamp>] ACTION: <service>.<operation> <key=value pairs>
```

### Services and Operations

| Service | Operations |
|---------|-----------|
| `github` | `create_branch`, `create_pr`, `push`, `add_comment`, `close_pr` |
| `jira` | `create_issue`, `update_issue`, `add_comment`, `transition` |
| `git` | `checkout`, `commit`, `worktree_add`, `worktree_remove` |

### Example

```
[2026-03-26T14:32:00Z] ACTION: github.create_branch branch=fix/SEC-001 base=main
[2026-03-26T14:32:15Z] ACTION: github.create_pr title="Fix SEC-001" branch=fix/SEC-001
[2026-03-26T14:33:00Z] ACTION: jira.create_issue project=MYPROJ type=Bug summary="SQL injection"
```

## Dry-Run Mode

When `--fix --dry-run` is active, entries are prefixed with `[DRY-RUN]`:

```
[DRY-RUN] [2026-03-26T14:32:00Z] ACTION: github.create_branch branch=fix/SEC-001 base=main
```

Dry-run entries appear in the `## Remediation Preview` section, not `## Audit Log`.

## Persistence

- Always included in the final report under `## Audit Log`.
- When `--save` is used, also appended to `docs/reviews/.audit-log`.
