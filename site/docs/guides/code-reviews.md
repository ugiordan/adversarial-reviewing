# Code Reviews

The code profile is the default review mode. It analyzes source code from 5 specialist perspectives with `file:line` evidence.

## Specialists

| Tag | Specialist | Focus Area |
|-----|-----------|------------|
| SEC | Security Auditor | Vulnerabilities, injection, auth, crypto, OWASP Top 10 |
| PERF | Performance Analyst | Complexity, memory, I/O, caching, scalability |
| QUAL | Code Quality Reviewer | Maintainability, SOLID, patterns, readability |
| CORR | Correctness Verifier | Logic errors, edge cases, race conditions, invariants |
| ARCH | Architecture Reviewer | Coupling, cohesion, boundaries, extensibility |

## Selecting specialists

Run all 5 (default):

```bash
/adversarial-review src/
```

Run specific specialists:

```bash
# Security only
/adversarial-review src/ --security

# Security + correctness
/adversarial-review src/ --security --correctness

# Architecture + quality
/adversarial-review src/ --architecture --quality
```

## Presets

### Quick mode

2 specialists (SEC + CORR), 2 iterations, 150K token budget:

```bash
/adversarial-review src/ --quick
```

### Thorough mode

All 5 specialists, 3 iterations, 800K token budget:

```bash
/adversarial-review src/ --thorough
```

### Custom budget

```bash
/adversarial-review src/ --budget 500000
```

## Reviewing specific files

```bash
# Single file
/adversarial-review src/auth/handler.go

# Directory
/adversarial-review src/controllers/

# Multiple targets
/adversarial-review src/auth/ src/middleware/ pkg/db/
```

## Delta mode (re-review changes only)

After applying fixes, re-review only what changed:

```bash
/adversarial-review src/ --delta
```

Delta mode detects changes since the last review and focuses specialists on modified code.

## Saving reports

```bash
/adversarial-review src/ --save
```

Reports are written to `docs/reviews/YYYY-MM-DD-<topic>-review.md`.

## Strict scope

By default, findings on files outside the review target are demoted to Minor. Use `--strict-scope` to reject them entirely:

```bash
/adversarial-review src/auth/ --strict-scope
```

## Advanced modes

The code profile supports several additional modes. Each has its own guide:

| Mode | Flag | Description |
|------|------|-------------|
| [Triage](triage-mode.md) | `--triage pr:<N>` | Evaluate external review comments (CodeRabbit, human reviewers) |
| [Change-impact](change-impact.md) | `--diff` | Enrich review with git diff context and caller/callee graph |
| [Remediation](remediation.md) | `--fix` | Classify findings, draft Jira tickets, implement fixes in worktree branches |
| Dry run | `--fix --dry-run` | Preview remediation without writing anything |
| [Context injection](context-injection.md) | `--context <label>=<source>` | Inject architecture docs or other reference material |
| Finding persistence | `--persist` | Track findings across runs (new, recurring, resolved, regressed) |
| Output normalization | `--normalize` | Canonical ordering for cross-run stability metrics |

These modes are composable. For example, `--triage pr:42 --diff --thorough` gives specialists both external comments and the full change-impact graph.

## Finding severity levels

| Severity | Criteria |
|----------|----------|
| **Critical** | Exploitable vulnerability, data loss, system crash |
| **Important** | Security weakness, performance regression, correctness bug |
| **Minor** | Style issue, minor optimization, code smell |

Findings with less than 100 characters of evidence are auto-demoted to Minor by the guardrails system.

## Guardrails

The review enforces programmatic guardrails:

| Guardrail | Effect |
|-----------|--------|
| Scope confinement | Findings outside review target demoted or rejected |
| Iteration hard cap | Agents force-stopped after MAX_ITERATIONS |
| Budget enforcement | Review stops when token budget exhausted |
| Per-agent budget cap | No single agent can consume > 150% of its fair share |
| Evidence threshold | Findings with < 100 chars evidence auto-demoted to Minor |
| Destructive pattern check | Recommended fixes scanned for rm -rf, DROP TABLE, force-push |
| Severity inflation detection | Warning when > 50% of agent's findings are Critical |
