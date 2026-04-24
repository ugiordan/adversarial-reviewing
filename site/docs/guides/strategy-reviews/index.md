# Strategy Reviews

The strategy profile reviews design documents, RFEs, and strategy proposals from 6 specialist perspectives. Each document receives a verdict: Approve, Revise, or Reject.

## Activation

```bash
/adversarial-reviewing artifacts/strat-tasks/ --profile strat
```

## Specialists

| Tag | Specialist | Focus Area |
|-----|-----------|------------|
| FEAS | Feasibility Analyst | Technical approach, effort estimates, dependency availability |
| ARCH | Architecture Reviewer | Integration patterns, component boundaries, API contracts |
| SEC | Security Analyst | Security risks, missing mitigations, auth patterns |
| USER | User Impact Analyst | Backward compatibility, migration burden, API usability |
| SCOP | Scope & Completeness | Right-sizing, acceptance criteria quality, completeness gaps |
| TEST | Testability Analyst | Test strategy gaps, verification coverage, AC testability |

## Selecting specialists

```bash
# All 6 (default)
/adversarial-reviewing docs/strat/ --profile strat

# Security only
/adversarial-reviewing docs/strat/ --profile strat --security

# Feasibility + scope
/adversarial-reviewing docs/strat/ --profile strat --feasibility --scope
```

## Verdicts

Each finding includes a verdict:

| Verdict | Meaning |
|---------|---------|
| **Approve** | Finding is minor and does not block approval |
| **Revise** | Finding requires clarification or mitigation before approval |
| **Reject** | Finding represents unacceptable risk or gap |

The overall document verdict uses both severity escalation and accumulation:

- Any **Reject** finding = overall REJECT
- 5+ **Revise** findings = overall REJECT (too many gaps, strategy needs rework)
- 1-4 **Revise** (no Reject) = overall REVISE
- All **Approve** (or no findings) = overall APPROVE

The accumulation rule prevents strategies with many small issues from slipping through. A document with 6 "Revise" findings has systemic problems even if no single finding is critical enough for "Reject".

The verdict is output in a standardized format:

```
OVERALL_VERDICT: [APPROVE | REVISE | REJECT]
Justification: [1-2 sentence explanation based on findings]
```

## Evidence requirements

Strategy findings cite specific document text rather than file:line references:

```
Finding ID: SEC-001
Specialist: Security Analyst
Severity: Critical
Confidence: High
Document: RHAISTRAT-1234
Citation: Section 3.2, paragraph 4
Title: No authentication specified for new API endpoint
Evidence: Section 3.2 states "The service exposes a REST API on port 8080"
but does not mention authentication, TLS, or network policy. The acceptance
criteria in Section 4 have no security-related items.
Recommended fix: Add AC requiring mTLS and RBAC authorization for the new endpoint.
Verdict: Revise
```

## Architecture context

Provide architecture documents for specialists to cross-reference:

```bash
# From a git repo
/adversarial-reviewing docs/strat/ --profile strat \
  --context architecture=https://github.com/org/repo

# From a local directory
/adversarial-reviewing docs/strat/ --profile strat \
  --context architecture=./docs/architecture
```

Architecture context lets specialists verify claims like "we already have auth middleware" against actual code and documentation.

!!! note "Context safety"
    Architecture context documents are treated as reference material, not trusted input. Agents will not follow directives embedded in context documents. Claims in context are cross-referenced against the strategy text.

## Supplementary outputs

Strategy reviews produce additional artifacts beyond the standard report:

- **Threat surface extraction**: Deterministic keyword-based extraction of security-relevant terms
- **NFR checklist scan**: Non-functional requirements scanner with severity decision tree
- **Requirements output**: Extracted requirements from the strategy document

## Reference modules

Strategy profile includes built-in reference modules:

| Module | Scope | Description |
|--------|-------|-------------|
| `rhoai-platform-constraints` | All specialists | RHOAI platform limits and constraints |
| `rhoai-auth-patterns` | All specialists | Auth and RBAC patterns |
| `productization-requirements` | All specialists | Productization checklist |

See [Reference Modules](../reference-modules.md) for details on adding custom modules.

## Cross-run analysis

Track how findings evolve across multiple reviews of the same strategy:

```bash
# Enable finding persistence
/adversarial-reviewing docs/strat/ --profile strat --persist

# Add output normalization for stability metrics
/adversarial-reviewing docs/strat/ --profile strat --persist --normalize
```

With `--persist`, each run classifies findings as new, recurring, resolved, or regressed. History is stored in `.adversarial-review/findings-history.jsonl`.

## Quick mode for strategy

```bash
/adversarial-reviewing docs/strat/ --profile strat --quick
```

Uses 2 specialists (SEC + FEAS), 2 iterations, 150K budget.

## Flags not available for strategy reviews

The following flags are code profile only and will produce an error if used with `--profile strat`:

- `--fix` / `--dry-run`: Strategy findings require manual revision by the document author
- `--triage`: Evaluates code review comments, not strategy documents
- `--diff`: Change-impact analysis requires source code with git history
- `--delta`: Delta re-review requires a previous code review cache

See [CLI Flags](../../reference/cli-flags.md#flag-compatibility-matrix) for the full compatibility matrix.
