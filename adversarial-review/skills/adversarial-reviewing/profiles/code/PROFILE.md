# Code Profile Details

Loaded by the orchestrator when `--profile code` is active (default).

## Specialist Flags

| Flag | Specialist | Agent File |
|------|-----------|------------|
| `--security` | Security Auditor | `profiles/code/agents/security-auditor.md` |
| `--performance` | Performance Analyst | `profiles/code/agents/performance-analyst.md` |
| `--quality` | Code Quality Reviewer | `profiles/code/agents/code-quality-reviewer.md` |
| `--correctness` | Correctness Verifier | `profiles/code/agents/correctness-verifier.md` |
| `--architecture` | Architecture Reviewer | `profiles/code/agents/architecture-reviewer.md` |

## Preset Profiles

| Flag | Specialists | Iterations | Budget |
|------|-------------|------------|--------|
| `--quick` | SEC + CORR (2) | 2 | 150K |
| `--thorough` | All 5 | 3 | 800K |
| *(default)* | All 5 | 3 | 350K |

## Report Sections (Phase 4)

The report includes up to 14 sections (see `profiles/code/templates/report-template.md`, or `profiles/code/templates/delta-report-template.md` for delta mode):

- Executive summary (Section 1)
- Review configuration (Section 2) — conditional, review parameters summary
- Validated findings with consensus status (Sections 3-6)
- Dismissed findings (Section 7)
- Challenge round findings (Section 8)
- Co-located findings (Section 9)
- **Remediation summary** (Section 10) — severity-sorted action list with remediation roadmap, blocked items, and top priorities. Always present, even without `--fix`.
- **Change Impact** (Section 11) — conditional, when `--diff` is active
- **Review Metrics** (Section 12) — challenge round statistics
- **Guardrails Triggered** (Section 13) — populated from the guardrail trip log
- **Audit Log** (Section 14) — external actions taken during `--fix` and `--triage`

## Code-Only Flags

| Flag | Effect |
|------|--------|
| `--delta` | Re-review only changes since last review |
| `--diff` | Enable diff-augmented input with change-impact graph |
| `--triage <source>` | Evaluate external review comments |
| `--fix` | Enable Phase 5 (Remediation) |
| `--fix --dry-run` | Preview remediation without writing anything |
| `--fix --converge` | Fix-review cycles to catch cross-fix interactions |
