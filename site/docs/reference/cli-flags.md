# CLI Flags

Complete reference for all flags accepted by `/adversarial-reviewing`.

## Invocation

```
/adversarial-reviewing [files/dirs] [flags]
```

When no files are specified, the review targets staged changes or the current directory.

## Profile flag

| Flag | Default | Description |
|------|---------|-------------|
| `--profile strat` | `code` | Switch to strategy document review |

## Specialist flags (code profile)

| Flag | Tag | Description |
|------|-----|-------------|
| `--security` | SEC | Security Auditor only |
| `--performance` | PERF | Performance Analyst only |
| `--quality` | QUAL | Code Quality Reviewer only |
| `--correctness` | CORR | Correctness Verifier only |
| `--architecture` | ARCH | Architecture Reviewer only |

## Specialist flags (strategy profile)

| Flag | Tag | Description |
|------|-----|-------------|
| `--security` | SEC | Security Analyst only |
| `--feasibility` | FEAS | Feasibility Analyst only |
| `--architecture` | ARCH | Architecture Reviewer only |
| `--user-impact` | USER | User Impact Analyst only |
| `--scope` | SCOP | Scope & Completeness Analyst only |
| `--testability` | TEST | Testability Analyst only |

Multiple specialist flags can be combined: `--security --correctness`.

Default (no specialist flags): all specialists for the active profile.

## Mode flags

| Flag | Profiles | Description |
|------|----------|-------------|
| `--quick` | Both | 2 specialists, 2 iterations, 150K budget |
| `--thorough` | Both | All specialists, 3 iterations, 800K budget |
| `--delta` | Code only | Re-review only changes since last review |
| `--save` | Both | Write report to `docs/reviews/YYYY-MM-DD-<topic>-review.md` |
| `--fix` | Code only | Enable Phase 5 remediation (Jira drafts, worktree branches, PRs) |
| `--fix --dry-run` | Code only | Preview remediation without writing anything |
| `--budget <N>` | Both | Override default 350K token budget. Cost estimates (USD) are shown in the pre-flight check and final report. |
| `--force` | Both | Override 200-file hard ceiling |
| `--strict-scope` | Both | Reject (not demote) out-of-scope findings and patches |
| `--persist` | Both | Enable cross-run finding persistence via fingerprinting |
| `--normalize` | Both | Enable output normalization for stability metrics |

!!! warning "Code-only flags with strat profile"
    Using `--delta`, `--diff`, `--triage`, or `--fix` with `--profile strat` produces an error. Strategy findings require manual revision of the strategy documents; automated remediation and diff-based analysis are not applicable.

## Diff and triage flags

These flags are **code profile only**.

| Flag | Description |
|------|-------------|
| `--diff` | Enable change-impact analysis with caller/callee graph |
| `--diff --range <range>` | Specify git commit range (e.g., `main..HEAD`) |
| `--triage <source>` | Evaluate external review comments |
| `--triage pr:<N>` | Triage PR comments (requires GitHub MCP tools) |
| `--triage file:<path>` | Triage comments from a JSON file |
| `--triage -` | Triage comments from stdin |
| `--gap-analysis` | Include coverage gap analysis in triage report |

## Context flag

| Flag | Profiles | Description |
|------|----------|-------------|
| `--context <label>=<source>` | Both | Inject labeled context (repeatable) |

Sources: git URL, local directory, or local file. Labels must be alphanumeric with optional hyphens.

## Cross-run analysis flags

| Flag | Profiles | Description |
|------|----------|-------------|
| `--persist` | Both | Track findings across runs via content-based fingerprinting. Classifies findings as new, recurring, resolved, or regressed. History stored in `.adversarial-review/findings-history.jsonl`. |
| `--normalize` | Both | Canonicalize output ordering and formatting. When combined with `--persist`, computes cross-run stability metrics (Jaccard similarity). |

## Reference module flags

| Flag | Description |
|------|-------------|
| `--list-references` | List all discovered reference modules with metadata |
| `--update-references` | Update modules from remote `source_url` (interactive) |
| `--update-references --check-only` | Check for updates without applying |

## Presets

### `--quick`

| Setting | Value |
|---------|-------|
| Specialists | 2 (SEC + CORR for code, SEC + FEAS for strat) |
| Iterations | 2 |
| Budget | 150K tokens |

### `--thorough`

| Setting | Value |
|---------|-------|
| Specialists | All (5 for code, 6 for strat) |
| Iterations | 3 |
| Budget | 800K tokens |

### Default (no preset)

| Setting | Value |
|---------|-------|
| Specialists | All |
| Iterations | 2 |
| Budget | 350K tokens |

## Flag compatibility matrix

Use this table to understand which flag combinations are valid:

| Combination | Behavior |
|------------|----------|
| `--delta` + `--reuse-cache` | **Mutually exclusive**. Use `--delta` for auto-discovery or `--reuse-cache` for explicit reuse, not both. |
| `--diff` + `--reuse-cache` | **Mutually exclusive**. `--diff` creates a minimal cache from changed files; `--reuse-cache` expects a complete cache. |
| `--delta` + `--keep-cache` | Composable. Reuses previous cache if confirmed, preserves after completion. |
| `--reuse-cache` + `--keep-cache` | Composable. Reuses specified cache and preserves after completion. |
| `--diff` + `--delta` | Composable. Delta discovers previous cache; diff limits scope to changed files. |
| `--persist` + `--normalize` | Composable. Adds stability metrics to the finding persistence report. |
| `--fix` + `--profile strat` | **Error**. Strategy findings require manual revision. |
| `--triage` + `--profile strat` | **Error**. Triage evaluates code review comments. |
| `--diff` + `--profile strat` | **Error**. Change-impact analysis requires source code. |
| `--delta` + `--profile strat` | **Error**. Delta re-review requires previous code review cache. |
