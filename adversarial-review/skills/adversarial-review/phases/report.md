# Phase 4: Report

## Purpose

Assemble and present the final review report. All findings are categorized by their resolution status and presented to the user. The report is displayed in conversation and optionally saved to disk.

## Prerequisites

- Phase 3 complete — all findings resolved, severity determined, co-locations flagged; OR Phases 2-3 skipped due to zero findings (generate "all clear" report with empty finding sections)
- Resolution results available for each finding (empty set if zero findings)

## Procedure

### Step 1: Assemble Report

Build the report using `templates/report-template.md` with the following 9 sections:

#### Section 1: Executive Summary

- Finding count by severity (Critical / Important / Minor)
- List of specialists involved
- Scope of reviewed files (count and paths)
- Configuration parameters: iterations completed, convergence status (achieved/not achieved per phase), token budget (used/total)
- If budget was exceeded, include: **"Review truncated due to token budget"**

#### Section 2: Consensus Findings

Findings where all specialists unanimously agreed on validity and severity. Include:
- Finding details (ID, severity, confidence, file, lines, title, evidence, fix)
- Agreement count: Unanimous (N/N specialists)

#### Section 3: Majority Findings

Findings that achieved strict majority agreement. Include:
- Finding details
- Majority severity (and disputes if any specialist assessed differently)
- Agreement count: M/N specialists
- Dissenting positions with specialist name, action (Challenge/Abstain), and reasoning summary

#### Section 4: Escalated Disagreements

Findings with unresolved disagreements requiring user decision. Include:
- Finding details (file, lines)
- All specialist positions with reasoning
- Combined evidence summary from all positions

#### Section 5: Escalated (Quorum Not Met)

Findings that could not reach quorum due to excessive abstentions. Include:
- Finding details (file, lines)
- Vote breakdown: agree/challenge/abstain counts
- Quorum threshold: `ceil((N+1)/2) = <value>`

#### Section 6: Dismissed Findings

Findings rejected during the challenge round. Include:
- Original severity
- File and line information
- Rejection reasoning summary
- List of challengers

#### Section 7: Challenge Round Findings

New findings raised during Phase 2. Include:
- Source iteration (which challenge round iteration)
- Finding details
- Mini self-refinement result (passed unchanged, or refined with summary of changes)

#### Section 8: Co-located Findings

Cross-specialist findings targeting overlapping file/line ranges. Present as grouped tables showing:
- Finding IDs, specialists, severities, and titles for each co-location group
- Interaction notes describing how the findings relate

#### Section 9: Remediation Summary

A flat, severity-sorted table of ALL validated findings (from Sections 2, 3, 4, 5, and 7) organized by area, not consensus mechanism. This is the actionable reference. Include:

- **All Findings table:** Every validated finding sorted by severity (Critical first), then by area. Columns: ID, Severity, Area, File, Title. For findings from Sections 4 and 5 (escalated/unresolved), add a `(unresolved)` marker in the Title column to distinguish them from fully validated findings.
- **Remediation Roadmap:** Categorize each finding's actionability status:
  - `Actionable (Jira)` — needs a tracked work item with design decisions, backward compat, or cross-team review
  - `Actionable (Chore)` — self-contained fix, direct PR without Jira
  - `Blocked/Deferred` — needs external approval, architect review, or cross-team decision before any work can start. Include the blocker reason.
  - `Already Fixed` — fix branch already exists (reference the branch name)
- **Top Priorities:** Numbered list of the 3-5 most urgent findings with a 1-line rationale for urgency.

This section is always generated, even without `--fix`. It provides the bridge between "what we found" (Sections 2-8) and "what to do about it" (Phase 5).

### Step 2: Generate Metadata Block

Compute and append the metadata block at the end of the report:

```
<!-- REVIEW METADATA
timestamp: <ISO 8601 UTC>
commit_sha: <git HEAD at time of review>
reviewed_files: <list of file paths with SHA-256 content hashes>
content_hash: <SHA-256 of report body excluding this metadata block>
metadata_hash: <SHA-256 of metadata fields excluding content_hash and metadata_hash>
specialists: <list of active specialist names>
configuration: <iterations, convergence points, CLI flags>
-->
```

**Computation order:**
1. Assemble all metadata fields except `content_hash` and `metadata_hash`
2. Compute `metadata_hash` = SHA-256 of all metadata fields (excluding `content_hash` and `metadata_hash` themselves)
3. Compute `content_hash` = SHA-256 of the full report body (everything above the metadata block)
4. Insert both hashes into the metadata block

**File hashes:** For each reviewed file, compute `sha256sum <file>` and include the hash alongside the path.

**Commit SHA:** Obtain via `git rev-parse HEAD`.

### Step 3: Display Report

Present the complete report to the user in the conversation. The report is always displayed regardless of whether `--save` is used.

### Step 4: Save Report (Optional)

If the `--save` flag is specified:

1. **Determine topic:**
   - Default: derive from the shallowest common ancestor directory of all reviewed files, converted to kebab-case
   - Override: use `--topic <name>` if provided
2. **Construct path:** `docs/superpowers/reviews/YYYY-MM-DD-<topic>-review.md`
3. **Create directories** if they do not exist: `mkdir -p docs/superpowers/reviews/`
4. **Write the file** — the metadata block MUST be the last element in the file

### Step 5: Never Auto-Commit

The report is **NEVER** automatically committed to git. The user must explicitly commit it themselves. This is a hard rule — do not offer to commit, do not stage the file, do not run `git add`.

### Step 6: Remediation Gate (when `--fix` is active)

If the `--fix` flag was specified, present the user with a confirmation prompt before proceeding to Phase 5:

> "The review is complete. Would you like to proceed with remediation (Phase 5)? This will classify findings, draft Jira tickets, and prepare fix PRs."

This is **Gate 1** of the remediation confirmation gates (see `phases/remediation.md`). Do NOT proceed to Phase 5 without explicit user approval.

## Budget Truncation Note

If the token budget was exceeded at any point during the review (Phase 1 or Phase 2), the executive summary must include:

> **Note:** Review truncated due to token budget. Some iterations were skipped and findings may be incomplete.

This informs the user that the review did not run to full completion.

## Single-Specialist Disclaimer

If the review ran in single-specialist mode (N = 1), the executive summary must include:

> **Note:** This review was conducted by a single specialist. Findings have not been cross-validated by independent reviewers and should be treated with reduced confidence.

## Topic Derivation

The topic for the saved report filename is derived as follows:

1. Collect all reviewed file paths
2. Find the shallowest common ancestor directory
3. Convert to kebab-case (e.g., `src/auth` becomes `src-auth`)
4. If `--topic` is provided, use that value instead (must be valid kebab-case)

## Delta Mode Reports

When `--delta` is active, use `templates/delta-report-template.md` instead of the standard report template. The delta report includes finding classification (resolved/persists/regressed/new) and references to the prior report.

## References

- `templates/report-template.md` — standard report template with 9 sections
- `templates/delta-report-template.md` — delta mode report template (also includes Remediation Summary)
- `protocols/token-budget.md` — budget truncation behavior
- `protocols/delta-mode.md` — delta mode execution and report rules
- `phases/remediation.md` — Phase 5 classification that Section 9 feeds into
