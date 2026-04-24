# Challenge Response Template (Strategy Profile)

## Response Format

Each specialist responds to findings presented during the challenge round using this format:

```
Response to [FINDING-ID]:
Action: [Agree | Challenge | Abstain]
Severity assessment: [Critical | Important | Minor]
Verdict assessment: [Approve | Revise | Reject]
Evidence: [supporting or counter-evidence, max 2000 chars]
```

## Field Constraints

| Field               | Constraint                                                        |
|---------------------|-------------------------------------------------------------------|
| FINDING-ID          | Must reference an existing Finding ID (e.g., `ARCH-001`)         |
| Action              | One of: `Agree`, `Challenge`, `Abstain`                           |
| Severity assessment | One of: `Critical`, `Important`, `Minor`. Required if Action is `Agree`, optional otherwise. |
| Verdict assessment  | One of: `Approve`, `Revise`, `Reject`. Required if Action is `Agree` or `Challenge`. |
| Evidence            | Max 2000 characters. Must cite specific strategy text or architecture docs. |

## Rules

1. **Agree** requires both a severity assessment and a verdict assessment. The responding specialist confirms the finding and states their independent severity and verdict judgment.
2. **Challenge** provides counter-evidence disputing the finding's validity, severity, or applicability. Must include a verdict assessment explaining how this affects the overall strategy verdict.
3. **Abstain** indicates the specialist lacks sufficient domain expertise to evaluate the finding. No severity or verdict assessment required.

## Verdict Challenges

Specialists may also challenge another agent's overall verdict independently of individual findings:

```
Verdict Challenge:
Target: [ROLE prefix of agent whose verdict is challenged]
Current verdict: [their verdict]
Proposed verdict: [your proposed change]
Evidence: [why the verdict should change, max 2000 chars]
```

This is used when a specialist agrees with all findings but disagrees with the overall verdict (e.g., "Your findings are all Minor, but you said Reject. That should be Approve.").

## New Findings in Challenge Rounds

Specialists MAY raise new findings discovered during the challenge round, but only in **iterations 1 and 2**. New findings are **prohibited in the final iteration**.

New findings must use the standard finding template format with an additional source marker:

```
New Finding (if any, iterations 1-2 only):
Finding ID: [ROLE-NNN]
Specialist: [specialist name]
Severity: [Critical | Important | Minor]
Confidence: [High | Medium | Low]
Document: [strategy document name]
Citation: [section, paragraph, or AC reference]
Title: [concise description, max 200 chars]
Evidence: [strategy text reference + explanation, max 2000 chars]
Recommended fix: [concrete suggestion, max 1000 chars]
Source: Challenge Round
```

## Example

```
Response to ARCH-001:
Action: Agree
Severity assessment: Important
Verdict assessment: Revise
Evidence: Confirmed. The platform architecture docs (rhods-operator.md, section "Ingress") describe Istio VirtualService as the current ingress mechanism. Gateway API migration is tracked in STRAT-042 but not yet implemented. The strategy's technical approach is built on infrastructure that doesn't exist yet.

Response to SEC-002:
Action: Challenge
Verdict assessment: Approve
Evidence: SEC flags a missing auth boundary on the new endpoint (Technical Approach, paragraph 5). However, the strategy states "all new endpoints will be fronted by the data-science-gateway" (Non-functional Requirements, item 3), which provides kube-auth-proxy via ext_authz. The auth gap SEC identified is already covered by the platform ingress pattern. This is a false positive.

Response to SCOP-001:
Action: Abstain
Evidence: This finding concerns acceptance criteria testability, which is outside my area of expertise as a security analyst.
```
