# RFE Profile Details

Loaded by the orchestrator when `--profile rfe` is active.

## Specialist Flags

| Flag | Specialist | Agent File |
|------|-----------|------------|
| `--requirements` | Requirements Analyst | `profiles/rfe/agents/requirements-analyst.md` |
| `--feasibility` | Feasibility Analyst | `profiles/rfe/agents/feasibility-analyst.md` |
| `--architecture` | Architecture Reviewer | `profiles/rfe/agents/architecture-reviewer.md` |
| `--security` | Security Analyst | `profiles/rfe/agents/security-analyst.md` |
| `--compatibility` | Compatibility Analyst | `profiles/rfe/agents/compatibility-analyst.md` |

## Preset Profiles

| Flag | Pipeline mode | `--review-only` | Iterations | Budget |
|------|--------------|-----------------|------------|--------|
| `--quick` | 1 refine + REQ+SEC review | REQ + SEC (2) | 2 | 150K |
| `--thorough` | 3 refine + all 5 review | All 5 | 3 | 800K |
| *(default)* | 2 refine + all 5 review | All 5 | 3 | 350K |

## Document Pipeline (Step 1b)

The pipeline is shared with the strat profile. When `--review-only` is NOT specified, delegate to `phases/strat-pipeline.md`. The profile config determines which agents, templates, and section structure are used.

See `profiles/strat/PROFILE.md` for the full pipeline description. The flow is identical; only the agents and templates differ.

**`--review-only`:** Skips the pipeline. Proceeds directly to Step 2 (scope resolution) with the input file as the review target.

## Deterministic Pre-Analysis (Step 2b)

Delegate to `protocols/pre-analysis.md`. Same as strat profile.

## Report Sections (Phase 4)

The report includes up to 10 sections (see `profiles/rfe/templates/report-template.md`):

- Executive summary with verdict agreement level (Section 1)
- Review configuration (Section 2)
- Per-RFE review with verdict tables and categorized findings (Section 3)
- Cross-RFE patterns (Section 4, when reviewing 2+ RFEs)
- Architecture context citations (Section 5, when architecture context loaded)
- Dismissed findings (Section 6)
- Challenge round highlights (Section 7)
- Remediation roadmap (Section 8)
- Methodology notes (Section 9)
- Metadata (Section 10)

## Additional Outputs (when `--save` is active)

- **Requirements output:** `docs/reviews/YYYY-MM-DD-<topic>-requirements.md` using `profiles/rfe/templates/requirements-template.md`. Splits findings by confidence tier (Required Amendments / Recommended / Human Review) and includes NFR checklist gaps. Addressed to the document author.
- **JSON output:** `docs/reviews/YYYY-MM-DD-<topic>-findings.json` via `scripts/findings-to-json.py`. Machine-readable findings with enrichment metadata for downstream tooling.

## RFE-Only Flags

| Flag | Effect |
|------|--------|
| `--review-only` | Skip pipeline, review input document directly |
| `--confirm` | Show refined document for user approval before full review (pipeline only) |
| `--principles <path>` | Load design principles YAML, injected into refine agents and review specialists |
| `--arch-context <repo@ref>` | Fetch architecture context from a specific git ref |
