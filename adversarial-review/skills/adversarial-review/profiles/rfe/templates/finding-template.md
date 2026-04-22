# Finding Template (RFE Profile)

## Structured Finding Format

Each finding MUST conform to the following structure. All fields are required unless otherwise noted.

```
Finding ID: [ROLE-NNN]
Specialist: [specialist name]
Severity: [Critical | Important | Minor]
Confidence: [High | Medium | Low]
Category: [required for SEC only: Security Risk | NFR Gap]
Document: [RFE document name]
Citation: [section, paragraph, requirement, or acceptance criterion reference]
Title: [concise description, max 200 chars]
Evidence: [RFE text reference + explanation, max 2000 chars]
Recommended fix: [concrete suggestion for RFE revision, max 1000 chars]
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
| Document         | RFE document name (e.g., `RFE-model-upload-api`)              |
| Citation         | Section, requirement, or AC reference (e.g., `Proposed Solution, paragraph 2` or `FR-3` or `AC-4`) |
| Title            | Max 200 characters                                            |
| Evidence         | Max 2000 characters. Must cite specific RFE text that creates the issue. |
| Recommended fix  | Max 1000 characters. Must be a concrete suggestion for revising the RFE. |
| Verdict          | One of: `Approve`, `Revise`, `Reject`. Per-RFE verdict reflecting all findings. |

## Role Prefixes

| Prefix | Specialist Domain        |
|--------|--------------------------|
| REQ    | Requirements             |
| FEAS   | Feasibility              |
| ARCH   | Architecture             |
| SEC    | Security                 |
| COMPAT | Backward Compatibility   |

## Verdict Rules

- **Approve**: No findings, or only Minor findings that don't block the RFE.
- **Revise**: One or more Important/Critical findings that require RFE changes before approval.
- **Reject**: Fundamental issues that require rethinking the approach, not just revisions.

The verdict appears ONCE at the end of the agent's output, after all findings. It reflects the agent's overall assessment across all findings for that RFE.

## Zero Findings

When a specialist finds no issues, the output MUST contain the explicit marker:

```
NO_FINDINGS_REPORTED
Verdict: Approve
```

Both the marker and a verdict are required.

## Example

```
Finding ID: COMPAT-001
Specialist: Compatibility Analyst
Severity: Important
Confidence: High
Document: RFE-model-upload-api
Citation: Proposed Solution, paragraph 4
Title: New upload endpoint changes response format without deprecation period
Evidence: The Proposed Solution states "the /v1/models/upload endpoint will return a structured JSON response with upload_id and status fields" (paragraph 4), replacing the current plain-text response. Existing clients that parse the plain-text response will break. No deprecation period or versioned endpoint is specified.
Recommended fix: Add a versioned endpoint (/v2/models/upload) with the new response format. Keep /v1 unchanged for at least 2 minor releases. Add Accept header negotiation or a deprecation notice in /v1 response headers.

Verdict: Revise
```
