# Delta Mode Protocol

## Purpose

Enable incremental reviews that build on a previous full review, analyzing only what changed. This reduces cost and time when re-reviewing code that has been partially modified since the last review.

## Activation

Delta mode is activated **only** with the explicit `--delta` flag. It is never auto-detected or implicitly enabled. If `--delta` is passed but no prior report is found, the review falls back to a full review with a warning.

## Prior Report Detection

When `--delta` is specified, the orchestrator searches `docs/reviews/` for existing review reports that match the current review topic.

## Report Integrity Verification

### Dual Hash Verification

Each prior report contains two hashes:

1. **content_hash** — SHA-256 of the report body (findings, analysis, recommendations)
2. **metadata_hash** — SHA-256 of metadata fields, excluding the hash fields themselves

Both hashes are recomputed and compared against stored values. Both must match for the report to be considered trustworthy.

### Git Verification

If the prior report is tracked by git, an additional check verifies that the file has not been amended since its original commit. This guards against post-commit tampering.

### Verification Failure

If hash verification fails:

1. Warn the user with a clear explanation of which hash failed
2. Offer the option to proceed with a full review instead
3. **Never silently proceed** with a delta review using an unverified report

## Change Scope

The diff scope for delta mode is determined by:

```bash
git diff <commit_sha>
```

This includes both staged and unstaged changes (the full working tree diff since the prior review's commit). The `<commit_sha>` is extracted from the prior report's metadata.

## Specialist Selection

Specialists are selected based on the prior report's findings:

- If a specialist had findings in files that have changed, that specialist is included
- Specialists with no prior findings in changed files may be excluded to reduce cost
- At minimum, two specialists are always selected regardless of prior findings

## Cost Guard

Before proceeding, the orchestrator estimates the cost of:

1. The delta review (fewer files, reduced iterations)
2. A fresh full review

If the delta review estimate exceeds the fresh review estimate (e.g., because most files changed), the user is offered the choice between delta and full review. This prevents delta mode from being more expensive than starting fresh.

## Execution

### Pre-Seeded Context

Specialists receive context only from changed files, not the full codebase. Prior findings for those files are included as baseline context.

### Reduced Iterations

Delta mode uses reduced iteration counts:

- Phase 1 (self-refinement): 2 iterations (instead of up to 3)
- Phase 2 (cross-agent debate): 2 iterations (instead of up to 3)

### Finding Classification

Each finding in a delta review is classified relative to the prior report:

| Classification | Meaning |
|---------------|---------|
| **resolved** | Finding from prior report no longer applies (code was fixed) |
| **persists** | Finding from prior report still applies despite changes |
| **regressed** | Finding from prior report worsened due to changes |
| **new** | Finding not present in prior report, introduced by changes |

### Delta Report

The output uses the delta report template (`templates/delta-report-template.md`) which includes the classification column and references to the prior report.

## Interaction with `--fix` (Phase 5)

When both `--delta` and `--fix` are specified:

1. Only **Persists**, **Regressed**, and **New** findings are eligible for remediation. **Resolved** findings are excluded.
2. Classification follows the same `jira`/`chore`/`blocked` criteria as a full review.
3. Regressed findings are prioritized — they indicate a fix attempt that made things worse.
4. The Remediation Summary in the delta report provides the bridge to Phase 5.

## Incremental Triage (`--triage --delta`)

When `--triage` and `--delta` are combined, the orchestrator loads the prior triage report and classifies each comment's verdict relative to the prior triage:

| Classification | Meaning |
|---------------|---------|
| **resolved** | Prior Fix verdict no longer applies (code was fixed) |
| **persists** | Prior Fix verdict still applies despite changes |
| **verdict-changed** | Verdict changed (e.g., Fix → No-Fix after code fix) |
| **new** | Comment not present in prior triage report |
| **dropped** | Comment from prior triage no longer exists in source |

## References

- `templates/delta-report-template.md` — output format for delta reviews (includes Remediation Summary)
- `protocols/token-budget.md` — budget tracking applies to delta reviews
- `protocols/convergence-detection.md` — convergence rules (with reduced iteration caps)
- `phases/remediation.md` — Phase 5 remediation workflow (when `--fix` is also specified)
