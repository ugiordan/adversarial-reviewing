# CLI Flags

Complete reference for all flags accepted by `/adversarial-review`.

## Invocation

```
/adversarial-review [files/dirs] [flags]
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

| Flag | Description |
|------|-------------|
| `--quick` | 2 specialists, 2 iterations, 150K budget |
| `--thorough` | All specialists, 3 iterations, 800K budget |
| `--delta` | Re-review only changes since last review |
| `--save` | Write report to `docs/reviews/YYYY-MM-DD-<topic>-review.md` |
| `--fix` | Enable Phase 5 remediation (Jira drafts, worktree branches, PRs) |
| `--fix --dry-run` | Preview remediation without writing anything |
| `--budget <N>` | Override default 350K token budget |
| `--force` | Override 200-file hard ceiling |
| `--strict-scope` | Reject (not demote) out-of-scope findings and patches |

## Diff and triage flags

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

| Flag | Description |
|------|-------------|
| `--context <label>=<source>` | Inject labeled context (repeatable) |

Sources: git URL, local directory, or local file. Labels must be alphanumeric with optional hyphens.

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
