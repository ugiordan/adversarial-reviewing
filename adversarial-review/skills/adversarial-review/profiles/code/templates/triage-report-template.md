# Triage Report Template

## Report Structure

```markdown
# Triage Report

## Metadata
- Date: [ISO-8601 timestamp]
- Source: [pr:NNN | file:path | stdin]
- Comments evaluated: [N]
- Specialists: [comma-separated list]
- Configuration: [--quick | --thorough | default]
- Budget: [consumed/limit tokens]

## Summary
- Fix: N (XX%)
- No-Fix: N (XX%)
- Investigate: N (XX%)
- New issues discovered: N

## Triage Table

| # | Verdict | Confidence | Severity | File | Comment Summary | Action |
|---|---------|-----------|----------|------|----------------|--------|
| EXT-001 | Fix | High | Important | component.go:155 | Early return skips baseline reset | Move reset before check |
| EXT-002 | Fix | Medium | Critical | controller.go:198 | IsEnabled drops ConditionFalse | Handle disabled path |
| EXT-003 | No-Fix | High | N/A | utils.go:44 | Unnecessary nil check | Acceptable defensive coding |

## Detailed Analysis

### EXT-001: [Comment summary]
**Consensus verdict:** Fix (4/5 agree)
**Analysis:** [full consensus reasoning with code evidence]
**Dissenting positions:** [if any]

## Discovered Issues

[New findings raised during triage, in standard finding format]

## Coverage Gap Analysis (optional, --gap-analysis or --thorough)

| Gap Type | Count | Example |
|----------|-------|---------|
| Change-impact tracing | 2 | EXT-001: Side effects not visible without caller context |
| Cross-file data flow | 1 | EXT-002: Guard clause in caller not analyzed |
```

## Notes

- Report is never auto-committed. Use `--save` for `docs/reviews/YYYY-MM-DD-<topic>-triage.md`.
- Triage-Discovery findings appear in the Discovered Issues section using the standard finding format.
- Coverage Gap Analysis only appears when `--gap-analysis` or `--thorough` is specified.
