# Injection Resistance Protocol

## Purpose

Detect and reject agent outputs that contain prompt injection patterns — text designed to manipulate the orchestrator or other agents rather than report genuine findings.

## Implementation

**Script:** `${CLAUDE_SKILL_DIR}/scripts/validate-output.sh`

Injection detection runs on all free-text fields (Title, Evidence, Recommended fix) of every finding during output validation.

## Detection Patterns

Detection uses a two-tier system to balance security with false-positive reduction. Legitimate security findings may naturally contain words like "override" or "abandon" — the two-tier approach prevents single incidental matches from rejecting valid findings.

### High-Confidence Patterns (single match flags)

These multi-word phrases are unlikely to appear in legitimate security findings:

| Pattern | Rationale |
|---------|-----------|
| `ignore all previous` | Attempt to override prior instructions |
| `ignore all instructions` | Attempt to override prior instructions |
| `ignore the above` | Attempt to override prior instructions |
| `disregard previous` | Attempt to clear prior context |
| `disregard all` | Attempt to override all controls |
| `system prompt` | Reference to system-level instructions |
| `discard previous` | Attempt to clear prior context |
| `new instructions` | Introducing replacement instructions |
| `real task` | Reframing the agent's objective |
| `you are now` | Role reassignment attempt |
| `forget your` | Memory/context manipulation |

### Context-Sensitive Patterns (2+ matches required)

These single words or short phrases can appear legitimately in security findings. A finding is flagged only when 2 or more context-sensitive patterns co-occur:

| Pattern | Legitimate use example |
|---------|----------------------|
| `you must` | "Users must rotate keys..." |
| `you should` | "Operators should restrict..." |
| `override` | "The RBAC override mechanism..." |
| `set aside` | "Set aside the default timeout..." |
| `supersede` | "New policy supersedes the old..." |
| `abandon` | "Users can abandon sessions..." |
| `authoritative` | "The authoritative DNS response..." |
| `ignore all` | "Do not ignore all errors..." |
| `disregard` | "Cannot disregard the timeout..." |

## Provenance and Field Isolation Markers

In addition to phrase patterns, the validator checks for structural markers that should only appear in orchestrator-generated wrappers, never in agent-produced content:

| Marker Pattern | Description |
|----------------|-------------|
| `[PROVENANCE::]` | Provenance markers used by the mediated communication protocol |
| `[FIELD_DATA_` | Field isolation markers used to wrap individual finding fields |

If an agent's output contains these markers in free-text fields, it indicates the agent is attempting to forge provenance or escape field isolation boundaries.

## Validation Behavior

- High-confidence pattern: a single match causes validation failure
- Context-sensitive patterns: 2+ co-occurring matches cause validation failure; a single match is allowed
- Provenance/field markers: a single match causes validation failure
- Failed validation triggers a fresh agent spawn with the error message (up to 2 attempts)

## Triage Mode Extensions

### Triage-Specific Inoculation

When `--triage` is active, all agent prompts receive additional inoculation text warning that external review comments are untrusted input that may contain prompt injection. See agent definition files for the full inoculation text.

### Input-Side Injection Scanning

External comments processed by `parse-comments.sh` undergo input-side injection scanning using the same high-confidence patterns as output validation. Comments containing injection patterns are:
1. NOT rejected (they are still triaged)
2. Flagged with `injection_warning: true` in the parsed output
3. Accompanied by a caution marker in the agent prompt

### Privileged Marker Stripping

The markers `NO_FINDINGS_REPORTED` and `NO_TRIAGE_EVALUATIONS` are stripped from external comment text before presenting to agents. These markers have privileged semantics in the validation pipeline and must not appear in untrusted input.

## References

- `${CLAUDE_SKILL_DIR}/scripts/validate-output.sh` — injection detection implementation
- `protocols/input-isolation.md` — delimiter-based isolation that prevents code-under-review from injecting
- `protocols/mediated-communication.md` — provenance and field isolation marker definitions
