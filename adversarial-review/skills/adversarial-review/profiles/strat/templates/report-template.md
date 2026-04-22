# Report Template (Strategy Profile)

## Final Review Report Structure

The final report contains up to 10 sections followed by a metadata block. The report is never auto-committed. Use `--save` to write to `docs/reviews/YYYY-MM-DD-<topic>-review.md`.

---

## Section 1: Executive Summary

```
# Strategy Review Report

**Review Date:** YYYY-MM-DD
**Specialists:** [list of active specialists]
**Strategies Reviewed:** [count]
**Agreement Level:** [Full Consensus | Strong Agreement | Partial Agreement | Split Decision | No Agreement] ([N]/[N] verdicts unanimous, [N] majority, [N] conservative tiebreak)
**Configuration:** [iterations] iterations, convergence [achieved/not achieved], budget [used/total]

| Strategy | Verdict | Agreement | Critical | Important | Minor |
|----------|---------|-----------|----------|-----------|-------|
| STRAT-NNN | [Approve/Revise/Reject] | [Unanimous/Majority/Tiebreak] (N/N) | N | N | N |

> **Strategy TL;DR:** [Quote the TL;DR section from the reviewed strategy document. If the strategy has no TL;DR section, omit this block.]
```

**Agreement Level values:**
- **Full Consensus**: All strategies received unanimous verdicts from all specialists
- **Strong Agreement**: >75% of verdicts are unanimous or majority, no tiebreaks
- **Partial Agreement**: Mix of unanimous, majority, and tiebreak verdicts
- **Split Decision**: >25% of verdicts required conservative tiebreak
- **No Agreement**: Majority of verdicts required tiebreak

When the agreement level is **Split Decision** or **No Agreement**, add a prominent note:

```
> **Note:** Specialists significantly disagreed on this review. [N] verdicts were decided by conservative tiebreak (most conservative verdict wins). See per-strategy sections for full positions.
```

## Section 2: Review Configuration

```
## Review Configuration
- **Date:** YYYY-MM-DDTHH:MM:SSZ
- **Scope:** [strategy documents] ([N] strategies)
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

## Section 3: Per-Strategy Review

For each strategy reviewed, include a dedicated section:

```
## STRAT-NNN: [Title]

### Verdict: [Approve | Revise | Reject] ([Agreement type], [N]/[N]) [escalated from X — if applicable]

| Agent | Verdict | Rationale |
|-------|---------|-----------|
| FEAS  | [verdict] | [one-line rationale] |
| ARCH  | [verdict] | [one-line rationale] |
| SEC   | [verdict] | [one-line rationale] |
| USER  | [verdict] | [one-line rationale] |
| SCOP  | [verdict] | [one-line rationale] |

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

## Section 4: Cross-Strategy Patterns

```
## Cross-Strategy Patterns

[Patterns observed across multiple strategies. Common themes, recurring gaps, systemic issues.]
```

Only include this section when reviewing 2+ strategies.

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

| Priority | Strategy | Finding | Action Required |
|----------|----------|---------|-----------------|
| 1 | STRAT-NNN | [ID] | [concrete revision needed] |
```

Ordered by severity (Critical first), then by strategy.

## Section 9: Methodology Notes

```
## Methodology

This review was conducted using adversarial multi-agent analysis with [N] specialists.
Each specialist independently reviewed the strategy documents, then challenged each
other's findings through [N] iterations of structured debate with evidence-based rebuttal.
Verdicts were resolved by [unanimous agreement | majority vote | conservative tiebreak].
```

## Section 10: Metadata

```yaml
---
review_type: strategy_review
profile: strat
strategies_reviewed: [list]
verdicts: {STRAT-NNN: approve, STRAT-NNN: revise}
agreement_level: [full_consensus | strong_agreement | partial_agreement | split_decision | no_agreement]
specialists: [FEAS, ARCH, SEC, USER, SCOP]
budget_used: N
budget_limit: N
iterations_phase1: N
iterations_phase2: N
architecture_context: [source | null]
reference_modules: [list]
---
```

## Verdict Resolution Rules

Per-strategy verdict is resolved after Phase 3 in two passes:

### Pass 1: Agent Vote Resolution

| Condition | Result |
|-----------|--------|
| All agents agree | Unanimous verdict |
| Strict majority agrees | Majority verdict |
| No majority (e.g., 2-2-1) | Most conservative verdict wins (reject > revise > approve) |

The conservative tiebreaker ensures strategies with split opinions are not approved.

### Pass 2: Severity-Based Escalation

After agent votes, finding severity can escalate (never downgrade) the verdict:

| Rule | Condition | Escalation |
|------|-----------|------------|
| Critical consensus | Any Critical finding with Consensus/Majority agreement | → REJECT |
| Critical low-confidence | Any Critical finding with LOW confidence | → REVISE (minimum) |
| Accumulation | 5+ findings at Important or higher | → REJECT |
| Important cluster | 3-4 findings at Important or higher | → REVISE (minimum) |
| Constraint violation | Finding matching a constraint with High+ severity floor | → REVISE (minimum) |

When a verdict is escalated, the report shows:

```
### Verdict: Reject (escalated from Approve)

**Escalation reason:** Critical consensus — finding SEC-003 (Critical, Consensus) triggers automatic REJECT.
**Agent votes:** 3 Approve, 2 Revise
```
