# Templates

All agent outputs follow structured templates validated by bash scripts.

## Code profile templates

### Finding template

Every code review finding uses this format:

```
Finding ID: <TAG>-NNN
Specialist: <specialist name>
Severity: [Critical | Important | Minor]
Confidence: [High | Medium | Low]
File: <file path>
Line: <line number or range>
Title: <max 200 chars>
Evidence: <max 2000 chars - must cite specific code>
Recommended fix: <max 1000 chars>
Source Trust: [First-Party | Third-Party | Generated | Vendored | Test]
```

**Field rules**:

- Finding ID prefix must match specialist tag (SEC, PERF, QUAL, CORR, ARCH)
- Evidence must exceed 100 characters (auto-demoted to Minor otherwise)
- Source Trust is required for security findings, optional for others
- Recommended fixes are scanned for destructive patterns

### Challenge response template

Used during Phase 2 cross-agent debate:

```
Challenge: <finding-id>
Challenger: <tag>
Type: [False Positive | Severity Inflation | Missing Context | Duplicate]
Argument: <max 1000 chars>
Evidence: <file:line citations>
```

### Report template

The Phase 4 report includes up to 14 sections:

1. Executive summary with agreement level
2. Review metadata (target, specialists, iterations, budget)
3. Critical findings
4. Important findings
5. Minor findings
6. Escalated disagreements
7. Dismissed findings with rationale
8. Challenge round highlights
9. Co-located findings
10. Remediation roadmap
11. Budget summary
12. Reference modules used
13. Appendix: raw specialist outputs (optional)
14. Appendix: convergence data (optional)

### Triage templates

Triage mode uses specialized templates:

- **Triage finding**: Verdict (Fix/No-Fix/Investigate), confidence, analysis per comment
- **Triage report**: Summary of all verdicts with coverage gaps (when `--gap-analysis` is used)
- **Triage input schema**: Expected format for comment sources

### Other templates

- **Jira template**: For Phase 5 ticket drafts
- **Delta report template**: For `--delta` mode incremental reports
- **Sanitized document template**: Post-sanitization output format

## Strategy profile templates

### Finding template

Strategy findings include a verdict instead of file:line references:

```
Finding ID: <TAG>-NNN
Specialist: <specialist name>
Severity: [Critical | Important | Minor]
Confidence: [High | Medium | Low]
Document: <strategy document name>
Citation: <section, paragraph, or AC reference>
Title: <max 200 chars>
Evidence: <max 2000 chars - must cite specific strategy text>
Recommended fix: <max 1000 chars>
Verdict: [Approve | Revise | Reject]
```

### Challenge response template

Same structure as code profile but with document citations instead of file:line.

### Report template

Strategy reports include per-document verdicts and requirements extraction alongside the standard sections.

### Requirements template

Extracted requirements from strategy documents, structured for downstream consumption.
