# Requirements Output Template (Strategy Profile)

## Purpose

Companion output to the full review report, addressed directly to the STRAT author. Separates findings into three tiers based on confidence scoring (see `phases/resolution.md` Confidence Scoring section). This is what the STRAT author reads and acts on.

Generated alongside the review report when profile is `strat` or `rfe`. Written to `docs/reviews/YYYY-MM-DD-<topic>-requirements.md` when `--save` is specified.

---

## Structure

```
# Strategy Review: Requirements for [STRAT-NNN]

**Review Date:** YYYY-MM-DD
**Verdict:** [Approve | Revise | Reject] ([Agreement type])
**Total Findings:** [N] ([N] required, [N] recommended, [N] for human review)

---

## Required Amendments

> These findings have HIGH confidence (corroborated by multiple specialists, survived challenge, or aligned with critical NFR gaps). The strategy should not be approved until these are addressed.

### [FINDING-ID]: [Title]
- **Severity:** [Critical | Important]
- **Category:** [category]
- **Document:** [STRAT reference]
- **What's missing:** [evidence text, citing specific section/AC or noting omission]
- **What to add:** [concrete recommended fix with platform-specific guidance where applicable]
- **Confidence signals:** self=[High|Medium|Low], corroboration=[yes: IDs | no], challenge=[survived|unchallenged], evidence=[specific|omission|vague]

---

## Recommended Amendments

> These findings have MEDIUM confidence (single specialist with strong evidence, or partial corroboration). The strategy should address these but they are less certain than required amendments.

### [FINDING-ID]: [Title]
- **Severity:** [Critical | Important | Minor]
- **Category:** [category]
- **Document:** [STRAT reference]
- **What's missing:** [evidence text]
- **What to add:** [recommended fix]
- **Confidence signals:** self=[value], corroboration=[value], challenge=[value], evidence=[value]

---

## Findings Requiring Human Review

> These findings have LOW confidence (single specialist, no corroboration, omission-based, or did not go through challenge round). The team should evaluate whether these are real gaps or false positives.

### [FINDING-ID]: [Title]
- **Severity:** [severity]
- **Category:** [category]
- **Document:** [STRAT reference]
- **What's missing:** [evidence text]
- **What to add:** [recommended fix]
- **Why low confidence:** [brief explanation: e.g., "single specialist, omission-based finding with no corroboration"]

---

## NFR Checklist Gaps

> Items from the recurring NFR checklist (Layer 2 scan) that this strategy scored NO or PARTIAL on. These are deterministic assessments, not specialist opinions.

| NFR ID | Category | Question | Answer | Severity | Citation |
|--------|----------|----------|--------|----------|----------|
| NFR-AUTH-01 | Auth & Authz | [question text] | NO | Critical | [section or "not mentioned"] |
| NFR-TEST-03 | Testability | [question text] | PARTIAL | Minor | [section] |

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total findings | N |
| Required amendments (HIGH confidence) | N |
| Recommended amendments (MEDIUM confidence) | N |
| Human review needed (LOW confidence) | N |
| NFR checklist gaps (NO) | N |
| NFR checklist gaps (PARTIAL) | N |
| Cross-specialist convergence | N findings flagged by 2+ specialists |
```

## Output Rules

- This file is addressed to the STRAT author, not the reviewer. Use "the strategy" not "we found".
- Every finding must include all 4 confidence signals for transparency.
- Required amendments (HIGH) always come first.
- NFR checklist gaps are listed separately because they come from the deterministic Layer 2 scan, not specialist opinion.
- If `--save` is specified, write to `docs/reviews/YYYY-MM-DD-<topic>-requirements.md` alongside the report.
- Never auto-committed.
