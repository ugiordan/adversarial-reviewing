# Finding Template

## Structured Finding Format

Each finding MUST conform to the following structure. All fields are required unless otherwise noted.

```
Finding ID: [ROLE-NNN]
Specialist: [specialist name]
Severity: [Critical | Important | Minor]
Confidence: [High | Medium | Low]
Source Trust: [External | Authenticated | Privileged | Internal | N/A]
File: [repo-relative path]
Lines: [start-end, e.g., 42-58]
Title: [concise description, max 200 chars]
Evidence: [code reference + explanation, max 2000 chars]
Impact chain: [source → intermediate steps → final impact, max 500 chars]
Recommended fix: [concrete suggestion, max 1000 chars]
```

## Field Constraints

| Field            | Constraint                                                    |
|------------------|---------------------------------------------------------------|
| Finding ID       | Format `ROLE-NNN` where ROLE is a role prefix, NNN is zero-padded three-digit sequence |
| Specialist       | Must match the assigned specialist name exactly               |
| Severity         | One of: `Critical`, `Important`, `Minor`                      |
| Confidence       | One of: `High`, `Medium`, `Low` — qualitative label for reporting only, does not affect resolution |
| Source Trust      | One of: `External`, `Authenticated`, `Privileged`, `Internal`, `N/A`. Required for SEC findings involving injection, SSRF, path traversal, impersonation, or any data flow from source to sink. Use `N/A` for findings not involving data flow (e.g., hardcoded secrets, missing encryption, config issues). See severity constraints below. |
| File             | Repo-relative path (e.g., `src/auth/login.ts`)               |
| Lines            | Numeric range `start-end` (e.g., `42-58`) or single line `N` (e.g., `42`) |
| Title            | Max 200 characters                                            |
| Evidence         | Max 2000 characters — must include code reference and explanation |
| Impact chain     | Max 500 characters — traces causal path from root cause through intermediate steps to final impact. Use `→` to separate steps. |
| Recommended fix  | Max 1000 characters — must be a concrete, actionable suggestion |

## Source Trust Definitions

| Value          | Meaning                                                        | Severity ceiling |
|----------------|----------------------------------------------------------------|------------------|
| External       | Attacker-controlled: HTTP params, request body, fork PR content, untrusted headers | Critical |
| Authenticated  | Requires valid login but any authenticated user can supply it   | Critical |
| Privileged     | Requires write/admin/triage access (e.g., labels, repo settings) | Important |
| Internal       | Hardcoded, infrastructure-set, or system-generated values       | Minor |
| N/A            | Finding does not involve a source-to-sink data flow             | Critical |

**Severity ceiling rule:** A finding's severity CANNOT exceed its Source Trust ceiling. A sink-only finding (dangerous operation identified but source not traced) is structurally invalid and must be rejected. The agent must trace the source before assigning severity.

## Role Prefixes

| Prefix | Specialist Domain |
|--------|-------------------|
| SEC    | Security          |
| PERF   | Performance       |
| QUAL   | Quality           |
| CORR   | Correctness       |
| ARCH   | Architecture      |

## Zero Findings

When a specialist finds no issues, the output MUST contain the explicit marker:

```
NO_FINDINGS_REPORTED
```

This marker is required for validation. An empty or missing findings section without this marker is considered a malformed response.

## Example

```
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
Source Trust: External
File: src/auth/session.ts
Lines: 112-128
Title: Session token generated with Math.random(), insufficient entropy for security-sensitive token
Evidence: The session token on line 115 uses `Math.random().toString(36)` which is not cryptographically secure. Math.random() uses a PRNG that is predictable and not suitable for generating session identifiers. An attacker could predict future tokens by observing a sequence of generated values. Source: any unauthenticated client triggers token generation via POST /login. Trust boundary: External.
Impact chain: Unauthenticated client triggers POST /login → Math.random() generates predictable token → attacker observes token sequence → predicts future tokens → session hijacking
Recommended fix: Replace `Math.random()` with `crypto.randomBytes(32).toString('hex')` (Node.js) or `crypto.getRandomValues()` (browser) to ensure cryptographically secure token generation.
```
