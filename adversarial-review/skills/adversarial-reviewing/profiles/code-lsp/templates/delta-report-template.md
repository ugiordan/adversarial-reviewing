# Delta Report Template
## Contents

- [Purpose](#purpose)
- [Classification Categories](#classification-categories)
- [Report Structure](#report-structure)
- [Metadata Block](#metadata-block)

## Purpose

The delta report is generated when running the adversarial review in delta mode against a prior review. It classifies each prior finding into one of four categories and surfaces any new issues introduced by fixes.

---

## Classification Categories

| Category     | Description                                      |
|--------------|--------------------------------------------------|
| **Resolved** | Finding is no longer present in the current code |
| **Persists** | Finding is still present, unchanged              |
| **Regressed**| Finding has gotten worse (e.g., expanded scope, increased severity) |
| **New**      | Issue introduced by fixes applied since the prior review |

---

## Report Structure

```
# Delta Review Report

**Base review:** [path or identifier of prior review]
**Base commit:** [commit SHA of prior review]
**Current commit:** [HEAD at time of delta review]
**Review date:** YYYY-MM-DD

## Summary

| Category   | Count |
|------------|-------|
| Resolved   | N     |
| Persists   | N     |
| Regressed  | N     |
| New        | N     |
```

### Resolved Findings

```
## Resolved Findings

The following findings from the prior review are no longer present.

### [FINDING-ID]: [Title] — RESOLVED
- **Prior severity:** [severity]
- **File:** [path] (lines [start-end])
- **Resolution:** [description of how/why the finding was resolved]
```

### Persisting Findings

```
## Persisting Findings

The following findings from the prior review are still present.

### [FINDING-ID]: [Title] — PERSISTS
- **Severity:** [severity] (unchanged | changed from [prior severity])
- **File:** [path] (lines [start-end])
- **Current state:** [description of the finding's current status]
- **Notes:** [any relevant changes in context, even if the core issue persists]
```

### Regressed Findings

```
## Regressed Findings

The following findings from the prior review have gotten worse.

### [FINDING-ID]: [Title] — REGRESSED
- **Prior severity:** [prior severity]
- **Current severity:** [current severity]
- **File:** [path] (lines [start-end])
- **Regression details:** [description of how the finding worsened]
```

### New Findings

```
## New Findings

The following issues were introduced by changes made since the prior review.

### [FINDING-ID]: [Title] — NEW
- **Severity:** [Critical | Important | Minor]
- **Confidence:** [High | Medium | Low]
- **File:** [path] (lines [start-end])
- **Evidence:** [code reference + explanation]
- **Recommended fix:** [concrete suggestion]
- **Likely cause:** [reference to fix or change that introduced this issue]
```

### Remediation Summary

```
## Remediation Summary

### All Active Findings by Severity

| ID | Severity | Category | Area | File | Title |
|----|----------|----------|------|------|-------|
| [ID] | [severity] | [Persists/Regressed/New] | [area] | [file:lines] | [title] |

### Remediation Roadmap

| Category | Count | Description |
|----------|-------|-------------|
| Actionable (Jira) | N | Findings requiring tracked work items with design decisions |
| Actionable (Chore) | N | Self-contained fixes for direct PR |
| Blocked/Deferred | N | Awaiting external approval or decisions |
| Already Fixed | N | Fix branches already exist |
| Resolved | N | No longer present (from prior review) |

### Top Priorities

1. **[ID]** — [1-line summary of why this is urgent]
2. **[ID]** — [1-line summary]
```

Only Persists, Regressed, and New findings appear in the "All Active Findings" table. Resolved findings are excluded (they need no action) but counted in the roadmap.

**Note:** The delta report uses a `Category` column (Persists/Regressed/New) in place of the base report's `(unresolved)` Title marker, since delta classification replaces resolution status as the primary grouping dimension.

---

## Metadata Block

```
<!-- DELTA REVIEW METADATA
timestamp: YYYY-MM-DDTHH:MM:SSZ
base_review: [path or identifier of prior review]
base_commit: [commit SHA of prior review]
current_commit: [HEAD at time of delta review]
reviewed_files: [list of file paths with SHA-256 hashes]
content_hash: [SHA-256 of report body excluding this metadata block]
metadata_hash: [SHA-256 of all metadata fields excluding both hash fields]
specialists: [list of active specialists]
configuration: [iterations, convergence points, flags used]
-->
```
