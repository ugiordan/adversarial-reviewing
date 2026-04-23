# Strat Profile Details

Loaded by the orchestrator when `--profile strat` is active.

## Specialist Flags

| Flag | Specialist | Agent File |
|------|-----------|------------|
| `--security` | Security Analyst | `profiles/strat/agents/security-analyst.md` |
| `--feasibility` | Feasibility Analyst | `profiles/strat/agents/feasibility-analyst.md` |
| `--architecture` | Architecture Reviewer | `profiles/strat/agents/architecture-reviewer.md` |
| `--user-impact` | User Impact Analyst | `profiles/strat/agents/user-impact-analyst.md` |
| `--scope` | Scope & Completeness Analyst | `profiles/strat/agents/scope-completeness-analyst.md` |
| `--testability` | Testability Analyst | `profiles/strat/agents/testability-analyst.md` |

## Preset Profiles

| Flag | Pipeline mode | `--review-only` | Iterations | Budget |
|------|--------------|-----------------|------------|--------|
| `--quick` | 1 refine + SEC+FEAS review | SEC + FEAS (2) | 2 | 200K |
| `--thorough` | 3 refine + all 6 review | All 6 | 3 | 1M |
| *(default)* | 2 refine + all 6 review | All 6 | 3 | 500K |

## Document Pipeline (Step 1b)

When `--review-only` is NOT specified, delegate to `phases/strat-pipeline.md`. This runs the full create, refine, review pipeline:

1. **Create:** Extract input from Jira key or normalize from file into strategy template
2. **Quick Review:** Lightweight 2-specialist review to surface gaps (skipped in `--quick` mode)
3. **Adversarial Refine:** 2-3 role-based agents each produce a complete refined strategy
4. **Mediator:** Section-by-section best-of merge (skipped when only 1 refine agent)
5. **Confirm Gate:** Optional (`--confirm`), shows refined strategy for user approval

After the pipeline completes, the review scope is set to the refined strategy document. Proceed to Step 3 (cache initialization), skipping Step 2 (scope confirmation).

**Input detection:** If the positional argument matches regex `^[A-Z][A-Z0-9_]+-\d+$`, it's a Jira key. Otherwise, it's a file path.

**`--review-only`:** Skips the pipeline. Proceeds directly to Step 2 (scope resolution) with the input file as the review target.

## Deterministic Pre-Analysis (Step 2b)

Delegate to `protocols/pre-analysis.md`. Covers Layer 1 (threat surface extraction), Layer 2 (NFR checklist scan), finding normalization (`--normalize`), finding persistence (`--persist`), prompt version tracking, and structured JSON output.

## Report Sections (Phase 4)

The report includes up to 10 sections (see `profiles/strat/templates/report-template.md`):

- Executive summary with verdict agreement level (Section 1)
- Review configuration (Section 2)
- Per-strategy review with verdict tables and categorized findings (Section 3)
- Cross-strategy patterns (Section 4, when reviewing 2+ strategies)
- Architecture context citations (Section 5, when architecture context loaded)
- Dismissed findings (Section 6)
- Challenge round highlights (Section 7)
- Remediation roadmap (Section 8)
- Methodology notes (Section 9)
- Metadata (Section 10)

## Additional Outputs (when `--save` is active)

- **Requirements output:** `docs/reviews/YYYY-MM-DD-<topic>-requirements.md` using `profiles/strat/templates/requirements-template.md`. Splits findings by confidence tier (Required Amendments / Recommended / Human Review) and includes NFR checklist gaps. Addressed to the document author.
- **JSON output:** `docs/reviews/YYYY-MM-DD-<topic>-findings.json` via `scripts/findings-to-json.py`. Machine-readable findings with enrichment metadata for downstream tooling.

## Strat-Only Flags

| Flag | Effect |
|------|--------|
| `--review-only` | Skip pipeline, review input document directly |
| `--confirm` | Show refined document for user approval before full review (pipeline only) |
| `--principles <path>` | Load design principles YAML, injected into refine agents and review specialists |
| `--arch-context <repo@ref>` | Fetch architecture context from a specific git ref |
