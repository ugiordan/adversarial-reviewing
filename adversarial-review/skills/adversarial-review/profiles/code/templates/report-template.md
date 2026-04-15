# Report Template

## Final Review Report Structure

The final report contains up to 14 sections followed by a metadata block. Some sections (Section 2, Section 11, Sections 12-14) are conditional based on review mode and events. The report is never auto-committed. Use `--save` to write to `docs/reviews/YYYY-MM-DD-<topic>-review.md`.

---

## Section 1: Executive Summary

Summary of the review including:
- Finding count by severity (Critical / Important / Minor)
- Specialists involved in the review
- Scope of reviewed files
- Configuration parameters: iterations completed, convergence status, token budget

```
# Executive Summary

**Review Date:** YYYY-MM-DD
**Specialists:** [list of active specialists]
**Files Reviewed:** [count] files
**Agreement Level:** [Full Consensus | Strong Agreement | Partial Agreement | Split Decision | No Agreement] ([N]/[N] findings unanimous, [N] majority, [N] escalated, [N] dismissed)
**Configuration:** [iterations] iterations, convergence [achieved/not achieved], budget [used/total]

| Severity | Count |
|----------|-------|
| Critical | N     |
| Important| N     |
| Minor    | N     |
| **Total**| **N** |
```

**Agreement Level values:**
- **Full Consensus**: All findings unanimously agreed upon by all specialists
- **Strong Agreement**: >75% consensus/majority findings, no escalated disagreements
- **Partial Agreement**: Mix of consensus, majority, and escalated findings
- **Split Decision**: >25% of findings escalated or dismissed, significant specialist disagreement
- **No Agreement**: Majority of findings unresolved, specialists fundamentally disagree

When the agreement level is **Split Decision** or **No Agreement**, add a prominent note after the severity table:

```
> **Note:** Specialists significantly disagreed on this review. [N] findings were resolved by majority override and [N] remain escalated. See Sections 4-6 for the full positions. Treat majority findings with reduced confidence.
```

## Section 2: Review Configuration

Human-readable summary of review parameters. Distinct from the machine-readable metadata block at the end of the report.

```
## Review Configuration
- **Date:** YYYY-MM-DDTHH:MM:SSZ
- **Scope:** [directories/files] ([N] files, [N] lines)
- **Specialists:** [list of active specialist tags]
- **Mode flags:** [flags used]
- **Iterations:** [TAG: N, TAG: N, ...]
- **Budget:** [used]K / [total]K consumed ([N]%)
- **Reference modules:** [N] loaded ([list])
- **Constraints:** [pack name] ([N] active) | none
```

When `--constraints` is active, add a subsection listing the loaded constraints:

```
### Active Constraints

| ID | Title | Severity Floor |
|----|-------|---------------|
| RHOAI-FIPS | FIPS 140-3 compliance required | High |
| ... | ... | ... |

Constraint severity is a floor: findings matching constraint violations use the constraint severity or higher.
```

## Section 3: Consensus Findings

Findings where all specialists agree on both validity and severity.

```
## Consensus Findings

All specialists agree on the following findings.

### [FINDING-ID]: [Title]
- **Severity:** [Critical | Important | Minor]
- **Confidence:** [High | Medium | Low]
- **File:** [path] (lines [start-end])
- **Evidence:** [evidence text]
- **Recommended fix:** [fix text]
- **Agreement:** Unanimous ([N]/[N] specialists)
```

## Section 4: Majority Findings

Findings where at least `ceil((N+1)/2)` specialists agree. Includes dissenting positions and any severity disputes.

```
## Majority Findings

The following findings achieved majority agreement.

### [FINDING-ID]: [Title]
- **Severity:** [majority severity] (disputed by: [specialist] who assessed [their severity])
- **Confidence:** [confidence]
- **File:** [path] (lines [start-end])
- **Evidence:** [evidence text]
- **Recommended fix:** [fix text]
- **Agreement:** [M]/[N] specialists
- **Dissenting positions:**
  - [Specialist]: [Challenge/Abstain] — [reasoning summary]
```

## Section 5: Escalated Disagreements

Findings with unresolved disagreements that require user decision. All positions are presented.

```
## Escalated Disagreements

The following findings have unresolved disagreements and require your decision.

### [FINDING-ID]: [Title]
- **File:** [path] (lines [start-end])
- **Positions:**
  - [Specialist A]: [Agree, severity] — [reasoning]
  - [Specialist B]: [Challenge] — [reasoning]
  - [Specialist C]: [Agree, different severity] — [reasoning]
- **Evidence summary:** [combined evidence from all positions]
```

## Section 6: Escalated (Quorum Not Met)

Findings where too many abstentions prevented reaching quorum.

```
## Escalated — Quorum Not Met

The following findings could not reach quorum due to abstentions.

### [FINDING-ID]: [Title]
- **File:** [path] (lines [start-end])
- **Votes:** [agree count] agree, [challenge count] challenge, [abstain count] abstain
- **Quorum required:** ceil(([N]+1)/2) = [threshold]
- **Reason:** Insufficient qualified assessments
```

## Section 7: Dismissed Findings

Findings rejected during the challenge debate, with reasoning.

```
## Dismissed Findings

The following findings were rejected during the challenge round.

### [FINDING-ID]: [Title] (DISMISSED)
- **Original severity:** [severity]
- **File:** [path] (lines [start-end])
- **Rejection reasoning:** [summary of why the finding was dismissed]
- **Challengers:** [list of specialists who challenged]
```

## Section 8: Challenge Round Findings

New findings raised during Phase 2 (challenge rounds), including mini self-refinement results.

```
## Challenge Round Findings

The following findings were raised during the challenge round.

### [FINDING-ID]: [Title]
- **Source:** Challenge Round (iteration [N])
- **Severity:** [severity]
- **Confidence:** [confidence]
- **File:** [path] (lines [start-end])
- **Evidence:** [evidence text]
- **Recommended fix:** [fix text]
- **Self-refinement result:** [passed | refined — summary of changes]
```

## Section 9: Co-located Findings

Cross-specialist findings at overlapping file and line ranges.

```
## Co-located Findings

The following findings from different specialists target overlapping file/line ranges.

### Co-location Group: [file path], lines [range]
| Finding ID | Specialist | Severity | Title |
|------------|-----------|----------|-------|
| [ID-1]     | [spec-1]  | [sev-1]  | [title-1] |
| [ID-2]     | [spec-2]  | [sev-2]  | [title-2] |

**Interaction notes:** [description of how these findings relate or interact]
```

## Section 10: Remediation Summary

Flat, severity-sorted summary of all validated findings organized by area and actionability. This is the "what do I do next" reference — it strips away consensus mechanics and presents findings as a prioritized action list.

```
## Remediation Summary

### All Findings by Severity

| ID | Severity | Area | File | Title |
|----|----------|------|------|-------|
| [ID] | [Critical/Important/Minor] | [component area] | [file:lines] | [title (unresolved)] |
| ... | ... | ... | ... | ... |

### Remediation Roadmap

| Category | Count | Description |
|----------|-------|-------------|
| Actionable (Jira) | N | Findings requiring tracked work items with design decisions |
| Actionable (Chore) | N | Self-contained fixes for direct PR |
| Blocked/Deferred | N | Findings awaiting external approval or cross-team decisions |
| Already Fixed | N | Findings with existing fix branches |

### Top Priorities

1. **[ID]** — [1-line summary of why this is urgent]
2. **[ID]** — [1-line summary]
3. ...
```

This section is always present, even without `--fix`. It gives the user a clear picture of what needs attention regardless of whether remediation will run.

## Section 11: Change Impact Summary (only when `--diff` is active)

When `--diff` is used, this section shows the change-impact graph overview:

- Changed symbols and their files
- Callers affected by the changes
- Callees that may be skipped by new early returns or guard clauses
- Advisory note that the impact graph is grep-based and may be incomplete

## Section 12: Review Metrics

Challenge round statistics for calibrating trust in results.

```
## Review Metrics
- Findings raised: [N]
- Findings surviving challenge: [N] ([N]%)
- Findings dismissed: [N] ([N]%)
- Consensus rate: [N]% (findings where all challengers agreed)
- Forced convergence: [N] agents
```

## Section 13: Guardrails Triggered

Record of all guardrails that activated during the review. If none: "None."

```
## Guardrails Triggered
- `GUARDRAIL_ID` — [agent] [details]
```

## Section 14: Audit Log

External actions taken during --fix and --triage. If no external actions: "No external actions taken." See `protocols/audit-log.md` for format.

```
## Audit Log
[timestamp] ACTION: service.operation key=value
```

---

## Metadata Block

Appended at the end of every report. Contains integrity and reproducibility information.

```
<!-- REVIEW METADATA
timestamp: YYYY-MM-DDTHH:MM:SSZ
commit_sha: [HEAD at time of review]
reviewed_files: [list of file paths with SHA-256 hashes]
content_hash: [SHA-256 of report body excluding this metadata block]
metadata_hash: [SHA-256 of all metadata fields excluding both hash fields]
specialists: [list of active specialists]
configuration: [iterations, convergence points, flags used]
-->
```

### Metadata Field Definitions

| Field          | Description                                                              |
|----------------|--------------------------------------------------------------------------|
| timestamp      | ISO 8601 UTC timestamp of report generation                              |
| commit_sha     | Git HEAD SHA at time of review                                           |
| reviewed_files | List of reviewed file paths, each with its SHA-256 content hash          |
| content_hash   | SHA-256 of the full report body, excluding the metadata block itself     |
| metadata_hash  | SHA-256 of all metadata fields, excluding `content_hash` and `metadata_hash` |
| specialists    | List of specialist names that participated in the review                 |
| configuration  | Review configuration: iteration count, convergence points, CLI flags     |

### Output Rules

- The report is **never auto-committed** to the repository.
- When `--save` is specified, the report is written to `docs/reviews/YYYY-MM-DD-<topic>-review.md`.
- The metadata block MUST be the last element in the report file.
