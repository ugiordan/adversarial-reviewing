# Sanitized Document Template
## Contents

- [Purpose](#purpose)
- [Document Structure](#document-structure)
- [Markers](#markers)
- [Rules](#rules)
- [Example](#example)

## Purpose

This template defines the format the orchestrator uses when presenting findings to agents during the challenge round. It ensures provenance tracking and field-level data isolation to prevent prompt injection and cross-contamination between specialist outputs.

## Document Structure

```
[PROVENANCE::Specialist_Name::VERIFIED]

[FIELD_DATA_<hex>_START]
Finding ID: [ROLE-NNN]
[FIELD_DATA_<hex>_END]

[FIELD_DATA_<hex>_START]
Specialist: [specialist name]
[FIELD_DATA_<hex>_END]

[FIELD_DATA_<hex>_START]
Severity: [Critical | Important | Minor]
[FIELD_DATA_<hex>_END]

[FIELD_DATA_<hex>_START]
Confidence: [High | Medium | Low]
[FIELD_DATA_<hex>_END]

[FIELD_DATA_<hex>_START]
File: [repo-relative path]
[FIELD_DATA_<hex>_END]

[FIELD_DATA_<hex>_START]
Lines: [start-end]
[FIELD_DATA_<hex>_END]

[FIELD_DATA_<hex>_START]
Title: [concise description]
[FIELD_DATA_<hex>_END]

[FIELD_DATA_<hex>_START]
Evidence: [code reference + explanation]
[FIELD_DATA_<hex>_END]

[FIELD_DATA_<hex>_START]
Recommended fix: [concrete suggestion]
[FIELD_DATA_<hex>_END]
```

## Markers

### Provenance Marker

```
[PROVENANCE::Specialist_Name::VERIFIED]
```

- Placed at the top of each specialist's finding block.
- `Specialist_Name` is the exact name of the specialist who produced the finding.
- `VERIFIED` indicates the orchestrator has validated the finding against the output schema before presenting it.

### Field-Level Isolation Markers

```
[FIELD_DATA_<hex>_START]
...field content...
[FIELD_DATA_<hex>_END]
```

- `<hex>` is a unique random hexadecimal token generated per field per finding (e.g., `a3f8c1`, `7b2e9d`).
- Each field in a finding is wrapped in its own pair of dynamic markers with a unique hex value.
- Dynamic markers prevent adversarial content in one field from escaping its boundary and being interpreted as structure in another field.

## Rules

1. **Only validated findings** — The orchestrator MUST only include findings that have passed schema validation. Raw specialist output or self-refinement drafts are never forwarded.
2. **Unique hex tokens** — Each `<hex>` value MUST be unique within the document. Reuse of hex tokens across fields is prohibited.
3. **No raw output** — Self-refinement drafts, internal reasoning traces, or intermediate outputs from specialists are never included in the sanitized document.
4. **Provenance integrity** — The provenance marker MUST accurately reflect the specialist who produced the finding. Misattribution is a validation failure.

## Example

```
[PROVENANCE::Security_Auditor::VERIFIED]

[FIELD_DATA_a3f8c1_START]
Finding ID: SEC-001
[FIELD_DATA_a3f8c1_END]

[FIELD_DATA_7b2e9d_START]
Specialist: Security Auditor
[FIELD_DATA_7b2e9d_END]

[FIELD_DATA_e4d102_START]
Severity: Critical
[FIELD_DATA_e4d102_END]

[FIELD_DATA_9fc3a8_START]
Confidence: High
[FIELD_DATA_9fc3a8_END]

[FIELD_DATA_b1a47e_START]
File: src/auth/session.ts
[FIELD_DATA_b1a47e_END]

[FIELD_DATA_2d6f93_START]
Lines: 112-128
[FIELD_DATA_2d6f93_END]

[FIELD_DATA_c8e51a_START]
Title: Session token generated with Math.random(), insufficient entropy
[FIELD_DATA_c8e51a_END]

[FIELD_DATA_f03b72_START]
Evidence: Math.random() on line 115 is not cryptographically secure. Predictable PRNG output enables session hijacking.
[FIELD_DATA_f03b72_END]

[FIELD_DATA_5a9d0e_START]
Recommended fix: Use crypto.randomBytes(32).toString('hex') for token generation.
[FIELD_DATA_5a9d0e_END]
```
