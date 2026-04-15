# Finding Template (Strategy Profile)

## Structured Finding Format

Each finding MUST conform to the following structure. All fields are required unless otherwise noted.

```
Finding ID: [ROLE-NNN]
Specialist: [specialist name]
Severity: [Critical | Important | Minor]
Confidence: [High | Medium | Low]
Category: [required for SEC only: Security Risk | NFR Gap]
Document: [strategy document name]
Citation: [section, paragraph, or acceptance criterion reference]
Title: [concise description, max 200 chars]
Evidence: [strategy text reference + explanation, max 2000 chars]
Recommended fix: [concrete suggestion for strategy revision, max 1000 chars]
Verdict: [Approve | Revise | Reject]
```

## Field Constraints

| Field            | Constraint                                                    |
|------------------|---------------------------------------------------------------|
| Finding ID       | Format `ROLE-NNN` where ROLE is a role prefix, NNN is zero-padded three-digit sequence |
| Specialist       | Must match the assigned specialist name exactly               |
| Severity         | One of: `Critical`, `Important`, `Minor`                      |
| Confidence       | One of: `High`, `Medium`, `Low`                               |
| Category         | One of: `Security Risk`, `NFR Gap` (SEC agent only, omit for other agents) |
| Document         | Strategy document name (e.g., `STRAT-001-gateway-api-sharding`) |
| Citation         | Section, paragraph, or AC reference (e.g., `Technical Approach, paragraph 3` or `AC-2`) |
| Title            | Max 200 characters                                            |
| Evidence         | Max 2000 characters. Must cite specific strategy text that creates the issue. |
| Recommended fix  | Max 1000 characters. Must be a concrete suggestion for revising the strategy. |
| Verdict          | One of: `Approve`, `Revise`, `Reject`. Per-strategy verdict reflecting all findings. |

## Role Prefixes

| Prefix | Specialist Domain   |
|--------|---------------------|
| FEAS   | Feasibility         |
| ARCH   | Architecture        |
| SEC    | Security            |
| USER   | User Impact         |
| SCOP   | Scope & Completeness|

## Verdict Rules

- **Approve**: No findings, or only Minor findings that don't block the strategy.
- **Revise**: One or more Important/Critical findings that require strategy changes before approval.
- **Reject**: Fundamental issues that require rethinking the approach, not just revisions.

The verdict appears ONCE at the end of the agent's output, after all findings. It reflects the agent's overall assessment across all findings for that strategy.

## Zero Findings

When a specialist finds no issues, the output MUST contain the explicit marker:

```
NO_FINDINGS_REPORTED
Verdict: Approve
```

Both the marker and a verdict are required.

## Example

```
Finding ID: ARCH-001
Specialist: Architecture Reviewer
Severity: Important
Confidence: High
Document: STRAT-001-gateway-api-sharding
Citation: Technical Approach, paragraph 3
Title: Strategy assumes Gateway API controller exists but platform uses Istio ingress
Evidence: The strategy states "route traffic through the existing Gateway API controller" (Technical Approach, paragraph 3), but per rhods-operator.md, the platform currently uses Istio VirtualService for ingress routing. Gateway API support is planned but not yet implemented. The strategy's approach depends on infrastructure that does not exist.
Recommended fix: Either (a) rewrite the technical approach to use Istio VirtualService, or (b) add a dependency on the Gateway API migration strategy and adjust the timeline accordingly.

Verdict: Revise
```
