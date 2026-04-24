# Report Template (RFE Profile)


## Contents

- [Final Review Report Structure](#final-review-report-structure)
- [Section 1: Executive Summary](#section-1-executive-summary)
- [Section 2: Review Configuration](#section-2-review-configuration)
- [Section 3: Per-RFE Review](#section-3-per-rfe-review)
- [Section 4: Cross-RFE Patterns](#section-4-cross-rfe-patterns)
- [Section 5: Architecture Context Citations](#section-5-architecture-context-citations)
- [Section 6: Dismissed Findings](#section-6-dismissed-findings)
- [Section 7: Challenge Round Highlights](#section-7-challenge-round-highlights)
- [Section 8: Remediation Roadmap](#section-8-remediation-roadmap)
- [Section 9: Methodology Notes](#section-9-methodology-notes)
- [Section 10: Metadata](#section-10-metadata)
- [Verdict Resolution Rules](#verdict-resolution-rules)

## Final Review Report Structure

The final report contains up to 10 sections followed by a metadata block. The report is never auto-committed. Use `--save` to write to `docs/reviews/YYYY-MM-DD-<topic>-review.md`.

---

## Section 1: Executive Summary

```
# RFE Review Report

**Review Date:** YYYY-MM-DD
**Specialists:** [list of active specialists]
**RFEs Reviewed:** [count]
**Agreement Level:** [Full Consensus | Strong Agreement | Partial Agreement | Split Decision | No Agreement] ([N]/[N] verdicts unanimous, [N] majority, [N] conservative tiebreak)
**Configuration:** [iterations] iterations, convergence [achieved/not achieved], budget [used/total]

| RFE | Verdict | Agreement | Critical | Important | Minor |
|-----|---------|-----------|----------|-----------|-------|
| RFE-NNN | [Approve/Revise/Reject] | [Unanimous/Majority/Tiebreak] (N/N) | N | N | N |

> **RFE TL;DR:** [Quote the TL;DR section from the reviewed RFE document. If the RFE has no TL;DR section, omit this block.]
```

**Agreement Level values:**
- **Full Consensus**: All RFEs received unanimous verdicts from all specialists
- **Strong Agreement**: >75% of verdicts are unanimous or majority, no tiebreaks
- **Partial Agreement**: Mix of unanimous, majority, and tiebreak verdicts
- **Split Decision**: >25% of verdicts required conservative tiebreak
- **No Agreement**: Majority of verdicts required tiebreak

When the agreement level is **Split Decision** or **No Agreement**, add a prominent note:

```
> **Note:** Specialists significantly disagreed on this review. [N] verdicts were decided by conservative tiebreak (most conservative verdict wins). See per-RFE sections for full positions.
```

## Section 2: Review Configuration

```
## Review Configuration
- **Date:** YYYY-MM-DDTHH:MM:SSZ
- **Scope:** [RFE documents] ([N] RFEs)
- **Specialists:** [list of active specialist tags]
- **Mode flags:** [flags used]
- **Iterations:** [TAG: N, TAG: N, ...]
- **Budget:** [used]K / [total]K consumed ([N]%) (~$[cost_usd])
- **Architecture context:** [loaded from <source> | not available]
- **Reference modules:** [N] loaded ([list])
- **Constraints:** [pack name] ([N] active) | none
```

When `--constraints` is active, add a subsection listing the loaded constraints:

```
### Active Constraints

| ID | Title | Severity Floor |
|----|-------|---------------|
| ORG-001 | Example constraint title | High |
| ... | ... | ... |

Constraint severity is a floor: findings matching constraint violations use the constraint severity or higher.
```

## Section 3: Per-RFE Review

For each RFE reviewed, include a dedicated section:

```
## RFE-NNN: [Title]

### Verdict: [Approve | Revise | Reject] ([Agreement type], [N]/[N]) [escalated from X, if applicable]

| Agent | Verdict | Rationale |
|-------|---------|-----------|
| REQ   | [verdict] | [one-line rationale] |
| FEAS  | [verdict] | [one-line rationale] |
| ARCH  | [verdict] | [one-line rationale] |
| SEC   | [verdict] | [one-line rationale] |
| COMPAT| [verdict] | [one-line rationale] |

### Findings

#### Consensus Findings
[Findings where all specialists agree]

#### Majority Findings
[Findings where majority agrees, with dissenting positions]

#### Escalated Findings
[Findings with unresolved disagreement, showing all positions]

### Dissenting Positions
[Full text of dissenting verdicts and their reasoning. Only present if verdict was not unanimous.]
```

## Section 4: Cross-RFE Patterns

```
## Cross-RFE Patterns

[Patterns observed across multiple RFEs. Common themes, recurring gaps, systemic issues.]
```

Only include this section when reviewing 2+ RFEs.

## Section 5: Architecture Context Citations

```
## Architecture Context

[Key architecture docs referenced during the review, with citations.]
```

Only include when architecture context was loaded.

## Section 6: Dismissed Findings

```
## Dismissed Findings

[Findings that were dismissed during resolution, with rationale.]
```

## Section 7: Challenge Round Highlights

```
## Challenge Round Highlights

[Notable challenges, reversals, and evidence-based rebuttals from the debate.]
```

## Section 8: Remediation Roadmap

```
## Remediation Roadmap

| Priority | RFE | Finding | Action Required |
|----------|-----|---------|-----------------|
| 1 | RFE-NNN | [ID] | [concrete revision needed] |
```

Ordered by severity (Critical first), then by RFE.

## Section 9: Methodology Notes

```
## Methodology

This review was conducted using adversarial multi-agent analysis with [N] specialists.
Each specialist independently reviewed the RFE documents, then challenged each
other's findings through [N] iterations of structured debate with evidence-based rebuttal.
Verdicts were resolved by [unanimous agreement | majority vote | conservative tiebreak].
```

## Section 10: Metadata

```yaml
---
review_type: rfe_review
profile: rfe
rfes_reviewed: [list]
verdicts: {RFE-NNN: approve, RFE-NNN: revise}
agreement_level: [full_consensus | strong_agreement | partial_agreement | split_decision | no_agreement]
specialists: [REQ, FEAS, ARCH, SEC, COMPAT]
budget_used: N
budget_limit: N
iterations_phase1: N
iterations_phase2: N
architecture_context: [source | null]
reference_modules: [list]
---
```

## Verdict Resolution Rules

Per-RFE verdict is resolved after Phase 3 in two passes:

### Pass 1: Agent Vote Resolution

| Condition | Result |
|-----------|--------|
| All agents agree | Unanimous verdict |
| Strict majority agrees | Majority verdict |
| No majority (e.g., 2-2-1) | Most conservative verdict wins (reject > revise > approve) |

The conservative tiebreaker ensures RFEs with split opinions are not approved.

### Pass 2: Severity-Based Escalation

After agent votes, finding severity can escalate (never downgrade) the verdict:

| Rule | Condition | Escalation |
|------|-----------|------------|
| Critical consensus | Any Critical finding with Consensus/Majority agreement | -> REJECT |
| Critical low-confidence | Any Critical finding with LOW confidence | -> REVISE (minimum) |
| Accumulation | 5+ findings at Important or higher | -> REJECT |
| Important cluster | 3-4 findings at Important or higher | -> REVISE (minimum) |
| Constraint violation | Finding matching a constraint with High+ severity floor | -> REVISE (minimum) |

When a verdict is escalated, the report shows:

```
### Verdict: Reject (escalated from Approve)

**Escalation reason:** Critical consensus, finding SEC-003 (Critical, Consensus) triggers automatic REJECT.
**Agent votes:** 3 Approve, 2 Revise
```
