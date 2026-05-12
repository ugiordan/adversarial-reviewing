# Challenge Response Template

## Response Format

Each specialist responds to findings presented during the challenge round using this format:

```
Response to [FINDING-ID]:
Action: [Agree | Challenge | Abstain]
Severity assessment: [Critical | Important | Minor]
Evidence: [supporting or counter-evidence, max 2000 chars]
```

## Field Constraints

| Field               | Constraint                                                        |
|---------------------|-------------------------------------------------------------------|
| FINDING-ID          | Must reference an existing Finding ID (e.g., `SEC-001`)           |
| Action              | One of: `Agree`, `Challenge`, `Abstain`                           |
| Severity assessment | One of: `Critical`, `Important`, `Minor` — **required** if Action is `Agree`, optional otherwise |
| Evidence            | Max 2000 characters — supporting or counter-evidence              |

## Rules

1. **Agree** requires a severity assessment. The responding specialist confirms the finding and states their independent severity judgment.
2. **Challenge** provides counter-evidence disputing the finding's validity, severity, or applicability.
3. **Abstain** indicates the specialist lacks sufficient domain expertise to evaluate the finding.

## New Findings in Challenge Rounds

Specialists MAY raise new findings discovered during the challenge round, but only in **iterations 1 and 2**. New findings are **prohibited in the final iteration**.

New findings must use the standard finding template format with an additional source marker:

```
New Finding (if any, iterations 1-2 only):
Finding ID: [ROLE-NNN]
Specialist: [specialist name]
Severity: [Critical | Important | Minor]
Confidence: [High | Medium | Low]
File: [repo-relative path]
Lines: [start-end]
Title: [concise description, max 200 chars]
Evidence: [code reference + explanation, max 2000 chars]
Recommended fix: [concrete suggestion, max 1000 chars]
Source: Challenge Round
```

The `Source: Challenge Round` marker distinguishes these findings from those raised in the initial review phase.

## Example

```
Response to SEC-001:
Action: Agree
Severity assessment: Critical
Evidence: Confirmed. Math.random() is specified as implementation-dependent and not cryptographically secure in the ECMAScript specification (ECMA-262, sec 21.3.2.27). In V8, it uses xorshift128+ which is trivially predictable after observing ~64 outputs. This is exploitable in a session management context.

Response to PERF-003:
Action: Challenge
Evidence: The N+1 query pattern identified on lines 45-52 is mitigated by the DataLoader batching layer initialized in src/loaders/index.ts:18. The DataLoader collapses individual fetches into a single batched query per tick. Measured query count with DataLoader active: 2 queries vs. the claimed N+1. The finding is a false positive in this architecture.

Response to ARCH-002:
Action: Abstain
Evidence: This finding concerns database schema normalization which is outside my area of expertise as a performance specialist. Unable to provide a qualified assessment.
```

## Triage Mode

When reviewing triage verdicts (not standard findings), use this adapted format:

```
Response to TRIAGE-<ROLE>-NNN (re: EXT-NNN):
Action: [Agree | Challenge | Abstain]
Verdict assessment: [Fix | No-Fix | Investigate]
Evidence: [supporting or counter-evidence, max 2000 chars]
```

### Field Constraints (Triage Mode)

| Field               | Constraint                                                        |
|---------------------|-------------------------------------------------------------------|
| TRIAGE-ID           | Must reference an existing Triage ID (e.g., `TRIAGE-SEC-001`)    |
| EXT-ID              | Must reference the associated External Comment ID (e.g., `EXT-003`) |
| Action              | One of: `Agree`, `Challenge`, `Abstain`                           |
| Verdict assessment  | One of: `Fix`, `No-Fix`, `Investigate` — **required** if Action is `Agree` or `Challenge` |
| Evidence            | Max 2000 characters — supporting or counter-evidence              |

### Example (Triage Mode)

```
Response to TRIAGE-SEC-001 (re: EXT-003):
Action: Challenge
Verdict assessment: No-Fix
Evidence: The reviewer flagged unsanitized input on line 42, but the input passes through the sanitize() middleware at route registration (src/routes/api.ts:15). The middleware applies HTML encoding and SQL parameterization before any handler receives the request. The comment is a false positive in this architecture.
```
