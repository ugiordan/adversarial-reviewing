# Triage Finding Template

## Structured Triage Verdict Format

Each triage verdict MUST conform to the following structure. All fields are required unless otherwise noted.

```
Triage ID: [TRIAGE-ROLE-NNN]
External Comment ID: [EXT-NNN]
Specialist: [specialist name]
Verdict: [Fix | No-Fix | Investigate]
Confidence: [High | Medium | Low]
Severity-If-Fix: [Critical | Important | Minor | N/A]
File: [repo-relative path, or "N/A" for general comments]
Lines: [start-end, or "N/A"]
Comment Summary: [the external comment being evaluated, max 500 chars]
Analysis: [technical analysis with code evidence, max 2000 chars]
Recommended Action: [concrete next step, max 1000 chars]
```

## Field Constraints

| Field | Constraint |
|-------|-----------|
| Triage ID | Format `TRIAGE-ROLE-NNN` where ROLE is a role prefix (SEC, PERF, QUAL, CORR, ARCH), NNN is zero-padded three-digit sequence |
| External Comment ID | Must reference a valid `EXT-NNN` from the parsed input |
| Specialist | Must match the assigned specialist name exactly |
| Verdict | One of: `Fix`, `No-Fix`, `Investigate` |
| Confidence | One of: `High`, `Medium`, `Low` — qualitative label matching finding template convention |
| Severity-If-Fix | Required when Verdict=Fix. One of: `Critical`, `Important`, `Minor`. Must be `N/A` when Verdict=No-Fix or Investigate. |
| File | Repo-relative path or `N/A` for general comments |
| Lines | Numeric range `start-end`, single line `N`, or `N/A` |
| Comment Summary | Max 500 characters |
| Analysis | Max 2000 characters — must include code reference and technical reasoning |
| Recommended Action | Max 1000 characters |

## Confidence Calibration

- **High**: Clear technical evidence supports the verdict. Code analysis is unambiguous.
- **Medium**: Evidence supports the verdict but edge cases or context gaps exist.
- **Low**: Verdict is a best guess. Insufficient context or conflicting signals.

## Role Prefixes

Same as standard findings: SEC, PERF, QUAL, CORR, ARCH.

## Zero Evaluations

When a specialist has no evaluations (no comments relate to their domain):

```
NO_TRIAGE_EVALUATIONS
```

## Triage-Discovery Findings

New findings discovered during triage use the standard finding template with:

```
Source: Triage-Discovery
Related-Comment: EXT-NNN
```

These follow all standard finding template constraints. Scope rules apply — findings can only target files in the confirmed scope.

## Example

```
Triage ID: TRIAGE-CORR-001
External Comment ID: EXT-001
Specialist: Correctness Verifier
Verdict: Fix
Confidence: High
Severity-If-Fix: Important
File: pkg/reconciler/component.go
Lines: 155-158
Comment Summary: Early return before baseline reset leaves stale per-component conditions for disabled components.
Analysis: The early return at line 155 exits ReconcileComponent when comp.Status.Phase == "disabled". However, SetCondition (line 160) and ResetBaseline (line 164) are called after this point. When a component transitions from enabled to disabled, the early return prevents ResetBaseline from clearing the previous baseline state, leaving stale conditions.
Recommended Action: Move ResetBaseline call before the disabled check, or add explicit baseline cleanup in the disabled path.
```
