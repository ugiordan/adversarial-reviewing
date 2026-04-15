# First Review Walkthrough

This walkthrough runs a real review and explains what each phase produces.

## Setup

Make sure the plugin is [installed](installation.md). Open a Claude Code session in a project directory.

## Step 1: Run the review

```bash
/adversarial-review src/controllers/ --security --correctness --save
```

This runs two specialists against the controllers directory and saves the report.

## Step 2: Understand the output

### Phase 1 output (per specialist)

Each specialist produces findings in a structured format:

```
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Important
Confidence: High
File: src/controllers/auth.go
Line: 42-58
Title: SQL injection in user lookup query
Evidence: The `findUser` function at line 42 concatenates user input
directly into the SQL query string without parameterization...
Recommended fix: Use parameterized queries via db.Query("SELECT ... WHERE id = ?", userID)
Source Trust: First-Party
```

Every finding must have:

- A unique ID with specialist prefix
- Severity (Critical/Important/Minor) backed by evidence
- Confidence level (High/Medium/Low)
- Exact file and line references
- Evidence exceeding 100 characters (findings with less are auto-demoted)

### Phase 2 output (challenge round)

Specialists challenge each other's findings:

```
Challenge: SEC-001
Challenger: CORR
Type: False Positive
Argument: The SQL query at line 42 uses an ORM method that already
parameterizes inputs. The raw SQL string is a template, not a
concatenation vulnerability.
Evidence: See orm.go:15 where Query() wraps all inputs in prepared statements.
```

The originating specialist must defend with `file:line` evidence or retract.

### Phase 3 output (resolution)

Each finding gets an agreement classification:

- **Full Consensus**: All specialists agree
- **Strong Agreement**: 4/5 agree
- **Partial Agreement**: 3/5 agree
- **Split Decision**: 2-3 agree (triggers confidence disclaimer)
- **No Agreement**: Dismissed with rationale

### Phase 4 output (report)

The final report includes:

- Executive summary with overall agreement level
- Validated findings by severity (Critical > Important > Minor)
- Escalated disagreements with all specialist positions
- Dismissed findings with rationale
- Remediation roadmap prioritized by severity and confidence

## Step 3: Review the saved report

```bash
cat docs/reviews/$(date +%Y-%m-%d)-controllers-review.md
```

## Next steps

- [Code review guide](../guides/code-reviews/index.md) for advanced usage
- [Strategy review guide](../guides/strategy-reviews/index.md) for document review
- [CLI flags reference](../reference/cli-flags.md) for all available options
