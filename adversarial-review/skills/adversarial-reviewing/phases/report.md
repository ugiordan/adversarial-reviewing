# Phase 4: Report
## Contents

- [Purpose](#purpose)
- [Prerequisites](#prerequisites)
- [Procedure](#procedure)
- [Budget Truncation Note](#budget-truncation-note)
- [Single-Specialist Disclaimer](#single-specialist-disclaimer)
- [Topic Derivation](#topic-derivation)
- [Delta Mode Reports](#delta-mode-reports)
- [Cache Interaction](#cache-interaction)
- [References](#references)

## Purpose

Assemble and present the final review report. All findings are categorized by their resolution status and presented to the user. The report is displayed in conversation and optionally saved to disk.

## Prerequisites

- Phase 3 complete — all findings resolved, severity determined, co-locations flagged; OR Phases 2-3 skipped due to zero findings (generate "all clear" report with empty finding sections)
- Resolution results available for each finding (empty set if zero findings)

## Procedure

### Step 1: Assemble Report

Build the report using `profiles/<profile>/templates/report-template.md` with up to 14 sections for code profile, or 10 sections for strat/rfe profiles (some conditional). The core sections are:

**Profile-specific behavior:**
- **Code profile:** Finding details include File, Lines. Sections 10-14 (remediation, change impact, metrics, guardrails, audit log) are present. Phase 5 is available.
- **Strat profile:** Finding details include Document, Citation. Per-strategy verdict sections replace the flat finding sections. Sections 11-14 are omitted (no diff, no fix mode). The report uses verdict agreement level as the primary indicator (see `phases/resolution.md` Verdict Resolution).
- **RFE profile:** Finding details include Document, Citation. Per-RFE verdict sections replace the flat finding sections. Sections 11-14 are omitted (no diff, no fix mode). The report uses verdict agreement level as the primary indicator (see `phases/resolution.md` Verdict Resolution).

#### Section 1: Executive Summary

Generate the finding summary table from the resolution output:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/summarize-findings.py <resolution_output.json>
```

Include the script output verbatim, then add:
- List of specialists involved
- Scope of reviewed files (count and paths)
- **Agreement level** from Phase 3 resolution (Full Consensus / Strong Agreement / Partial Agreement / Split Decision / No Agreement) with breakdown from the summary output
- If budget was exceeded, include: **"Review truncated due to token budget"**
- If agreement level is **Split Decision** or **No Agreement**, include a prominent disclaimer: **"Specialists significantly disagreed. Majority findings should be treated with reduced confidence."**

#### Section 2: Review Configuration (conditional)

Generate using the metadata formatting script:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/format-report-meta.py \
  --topic "<topic>" --profile <profile> \
  --specialists "<list>" --iterations <n> \
  --budget-json '<track-budget.sh status output>' \
  --budget-limit <budget> \
  [--commit <sha>] [--preset <preset>] \
  [--flags "<flags>"] [--guardrails '<json_array>']
```

Include the script output verbatim.

#### Section 3: Consensus Findings (code profile) / Per-Document Review (strat/rfe profile)

**Code profile:** Findings where all specialists unanimously agreed on validity and severity. Include:
- Finding details (ID, severity, confidence, file, lines, title, evidence, fix)
- Agreement count: Unanimous (N/N specialists)

**Strat/RFE profile:** This section is replaced by per-document review sections (see `profiles/<profile>/templates/report-template.md` Section 3). Each document gets a dedicated section with verdict, per-agent verdict table, and categorized findings (consensus, majority, escalated).

#### Section 4: Majority Findings

Findings that achieved strict majority agreement. Include:
- Finding details
- Majority severity (and disputes if any specialist assessed differently)
- Agreement count: M/N specialists
- Dissenting positions with specialist name, action (Challenge/Abstain), and reasoning summary

#### Section 5: Escalated Disagreements

Findings with unresolved disagreements requiring user decision. Include:
- Finding details (file, lines)
- All specialist positions with reasoning
- Combined evidence summary from all positions

#### Section 6: Escalated (Quorum Not Met)

Findings that could not reach quorum due to excessive abstentions. Include:
- Finding details (file, lines)
- Vote breakdown: agree/challenge/abstain counts
- Quorum threshold: `ceil((N+1)/2) = <value>`

#### Section 7: Dismissed Findings

Findings rejected during the challenge round. Include:
- Original severity
- File and line information
- Rejection reasoning summary
- List of challengers

#### Section 8: Challenge Round Findings

New findings raised during Phase 2. Include:
- Source iteration (which challenge round iteration)
- Finding details
- Mini self-refinement result (passed unchanged, or refined with summary of changes)

#### Section 9: Co-located Findings

Cross-specialist findings targeting overlapping regions. Present as grouped tables showing:
- Finding IDs, specialists, severities, and titles for each co-location group
- Interaction notes describing how the findings relate

**Code profile:** Co-location is based on overlapping file/line ranges.
**Strat/RFE profile:** Co-location is based on same document and overlapping section/citation references.

#### Section 10: Remediation Summary

A flat, severity-sorted table of ALL validated findings (from Sections 3, 4, 5, 6, and 8) organized by area, not consensus mechanism. This is the actionable reference. Include:

- **All Findings table:** Every validated finding sorted by severity (Critical first), then by area. Columns: ID, Severity, Area, File, Title. For findings from Sections 5 and 6 (escalated/unresolved), add a `(unresolved)` marker in the Title column to distinguish them from fully validated findings.
- **Remediation Roadmap:** Categorize each finding's actionability status:
  - `Actionable (Jira)` — needs a tracked work item with design decisions, backward compat, or cross-team review
  - `Actionable (Chore)` — self-contained fix, direct PR without Jira
  - `Blocked/Deferred` — needs external approval, architect review, or cross-team decision before any work can start. Include the blocker reason.
  - `Already Fixed` — fix branch already exists (reference the branch name)
- **Top Priorities:** Numbered list of the 3-5 most urgent findings with a 1-line rationale for urgency.

This section is always generated, even without `--fix`. It provides the bridge between "what we found" (Sections 3-9) and "what to do about it" (Phase 5).

#### Sections 11-14 (conditional)

These sections are defined in `templates/report-template.md` and rendered when applicable:
- **Section 11: Change Impact** — when `--diff` is active
- **Section 12: Review Metrics** — challenge round statistics (findings raised/surviving/dismissed)
- **Section 13: Guardrails Triggered** — populated from the guardrail trip log
- **Section 14: Audit Log** — external actions taken during `--fix` and `--triage`
- **Section 15: Finding Persistence** — when `--persist` is active. Generated by `${CLAUDE_SKILL_DIR}/scripts/fingerprint_findings.py compare`. Shows:
  - **New findings:** First seen in this run
  - **Recurring findings:** Present in previous runs (with first-seen date and run count)
  - **Resolved findings:** Present in previous runs but not in this one
  - **Regressed findings:** Previously resolved, now reappearing
  - **Stability score:** When `--normalize` is also active, includes cross-run stability metrics from `${CLAUDE_SKILL_DIR}/scripts/normalize_findings.py diff`

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
prompt_versions: <map of agent file → version + content_hash from frontmatter>
-->
```

**Prompt versions:** For each active specialist, read the agent prompt file's YAML frontmatter and include `version` and `content_hash` fields. This enables tracking which prompt version produced which findings, supporting reproducibility analysis. Generate via `${CLAUDE_SKILL_DIR}/scripts/prompt_version.py manifest <agents_dir>`.

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
2. **Construct path:** `docs/reviews/YYYY-MM-DD-<topic>-review.md`
3. **Idempotency check:** Before writing, follow the Report File check in `protocols/idempotency.md`. If the file already exists, present options to the user before proceeding.
4. **Create directories** if they do not exist: `mkdir -p docs/reviews/`
5. **Write the file** — the metadata block MUST be the last element in the file

### Step 4b: Generate Requirements Output (Strat/RFE Profile, when `--save`)

When the active profile is `strat` or `rfe` and `--save` is specified, generate the requirements output alongside the report:

1. **Split findings by confidence tier** using the confidence labels from Phase 3:
   - **HIGH confidence** → "Required Amendments" (document must address before approval)
   - **MEDIUM confidence** → "Recommended Amendments" (document should address)
   - **LOW confidence** → "Findings Requiring Human Review" (team should evaluate)

2. **Include NFR checklist gaps** from the Layer 2 scan (items scored NO or PARTIAL) in a separate section. These are deterministic assessments, not specialist opinions.

3. **Include all 4 confidence signals** for each finding (self_assessment, corroboration, challenge_survival, evidence_specificity) for transparency.

4. **Write to** `docs/reviews/YYYY-MM-DD-<topic>-requirements.md` using `profiles/strat/templates/requirements-template.md` (shared between strat and rfe profiles).

5. **Generate JSON output** via `${CLAUDE_SKILL_DIR}/scripts/findings-to-json.py`:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/findings-to-json.py <findings-file> --profile <profile> --metadata '{"doc_id": "...", "review_date": "..."}'
   ```
   Write to `docs/reviews/YYYY-MM-DD-<topic>-findings.json`.

The requirements output is addressed to the document author. Use "the strategy/RFE" not "we found."

### Step 5: Generate Visualizations (Optional)

After assembling the report, generate a visual dashboard summarizing review metrics. Collect the following data from the review session:

- **Budget:** limit, consumed, per-phase breakdown, per-agent consumption (from `track-budget.sh status`)
- **Funnel:** raw finding count, post-self-refinement count, post-challenge count, validated count, dismissed count
- **Severity:** validated findings by severity level
- **Convergence:** findings-per-iteration per agent (from self-refinement iterations)

Pass this data as JSON to:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/generate-visuals.py --output <report_dir>/visuals --individual --inline '<json>'
```

The script generates:
- `summary.png`: 4-panel dashboard (budget gauge, finding funnel, severity donut, convergence curves)
- Individual charts: `budget.png`, `funnel.png`, `severity.png`, `convergence.png`

If `--save` is active, the visuals directory is created alongside the report file. Always display the summary chart to the user in conversation using the Read tool on the generated PNG.

If matplotlib is unavailable, skip visualization with a note in the report.

### Step 6: Never Auto-Commit

The report is **NEVER** automatically committed to git. The user must explicitly commit it themselves. This is a hard rule — do not offer to commit, do not stage the file, do not run `git add`.

### Step 7: Remediation Gate (when `--fix` is active)

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

## Cache Interaction

The final report reads consensus findings from `{CACHE_DIR}/findings/`. If `--keep-cache` is specified, write `.adversarial-review/last-cache.json` with session hex and commit SHA after report generation (before the cleanup trap fires). Format:

```json
{"session_hex": "<hex>", "commit_sha": "<HEAD>"}
```

## References

- `profiles/<profile>/templates/report-template.md` — profile-specific report template (code: up to 14 sections, strat/rfe: up to 10 sections)
- `templates/delta-report-template.md` — delta mode report template (code profile only)
- `protocols/token-budget.md` — budget truncation behavior
- `protocols/delta-mode.md` — delta mode execution and report rules
- `${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh` — cache management (findings read from `{CACHE_DIR}/findings/`)
- `phases/remediation.md` — Phase 5 classification that Section 10 feeds into
- `profiles/strat/templates/requirements-template.md` — confidence-tiered requirements output for document authors (shared between strat and rfe profiles)
- `${CLAUDE_SKILL_DIR}/scripts/findings-to-json.py` — structured JSON output with enrichment metadata
- `${CLAUDE_SKILL_DIR}/scripts/nfr-scan.py` — NFR checklist scanner (Layer 2 results for requirements output)
- `${CLAUDE_SKILL_DIR}/scripts/extract-threat-surface.py` — threat surface extraction (Layer 1 context)
