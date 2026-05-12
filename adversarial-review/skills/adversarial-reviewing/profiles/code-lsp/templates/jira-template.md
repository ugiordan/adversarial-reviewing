# Jira Ticket Template
## Contents

- [Usage](#usage)
- [Template](#template)
- [Grouping Rules](#grouping-rules)
- [Output Rules](#output-rules)

## Usage

This template is used by Phase 5 (Remediation) to generate Jira ticket descriptions for findings classified as `jira`-needed. The orchestrator fills in the fields from the validated findings.

---

## Template

### Title

```
[<Category>] <concise problem statement>
```

Title must be under 80 characters. Use the pattern: `[<Category>] <verb> <what> in <where>`.

Category matches the review specialist domain:
- `[Security]` for security audit findings
- `[Performance]` for performance findings
- `[Quality]` for code quality findings
- `[Correctness]` for correctness findings
- `[Architecture]` for architecture findings

Examples:
- `[Security] Harden RBAC permissions across operator controllers`
- `[Security] Prevent cross-namespace secret access via GatewayConfig`
- `[Performance] Reduce N+1 query pattern in dashboard controller`
- `[Quality] Replace string-based YAML templating in monitoring setup`

### Description

Use Jira wiki markup (not Markdown).

```
h2. Overview

<1-2 sentence summary of the security issue and its impact>

h2. Findings

The following findings from the review are addressed by this ticket:

||Finding ID||Severity||File||Title||
|<ID>|<severity>|<file:lines>|<title>|
|<ID>|<severity>|<file:lines>|<title>|

h2. What We Have Now

<Explain the current code behavior and why it's a problem. Include the actual
code snippet showing the vulnerable/broken pattern.>

{code:<language>}
// Current code (<file>:<lines>)
<code snippet showing the problem as it exists today>
{code}

*Root cause:*
<What in the code causes this issue — be specific about the mechanism>

*Impact:*
<What could happen if this is exploited or left unfixed — concrete scenarios>

*Affected components:*
<List of files/packages/controllers affected>

h2. How We Fix It

<Explain the specific technical approach. This is actionable — we are proposing
the fix, not asking someone else to decide. State the approach, justify why this
approach over alternatives, and show the target code.>

{code:<language>}
// After (<file>:<lines>)
<code snippet showing the fixed version>
{code}

*Alternatives considered:*
<If multiple approaches exist, briefly explain why this one was chosen>

h2. Code Quality Observations

<Optional — include only when the review surfaced related improvements that
should be addressed in the same change. Examples: magic strings that should be
constants, missing error handling adjacent to the fix, test gaps.>

<If no observations, omit this section entirely.>

h2. Acceptance Criteria

* [ ] <specific testable criterion 1>
* [ ] <specific testable criterion 2>
* [ ] <specific testable criterion 3>
* [ ] All existing tests pass
* [ ] No new RBAC permissions introduced (or justified if needed)

h2. Risk Assessment

*Severity:* <Critical|Important|Minor>
*Backward compatibility:* <Yes — no behavior change | No — <describe breaking change>>
*Requires backport:* <Yes — affects versions X+ | No>

h2. References

* Security audit report: <link or date>
* Related findings: <list of finding IDs>
```

### Labels

```
security, audit, <component-label>
```

### Priority

Map from finding severity:
| Finding Severity | Jira Priority |
|-----------------|---------------|
| Critical | Blocker |
| Important | Major |
| Minor | Minor |

When a Jira groups multiple findings with different severities, use the highest severity.

### Story Points / Estimation

Do NOT include story points or time estimates. The team should estimate during refinement.

---

## Grouping Rules

When multiple findings map to a single Jira ticket:

1. **Title** should describe the common theme, not individual findings
2. **Findings table** lists all findings in the group
3. **What We Have Now** explains the shared root cause or pattern with current code
4. **How We Fix It** covers the holistic approach (not per-finding patches) with target code
5. **Code Quality Observations** surfaces any related improvements discovered during review (constants, test gaps, etc.) — omit if none
6. **Acceptance Criteria** should verify all findings in the group are resolved
7. **Severity** is the highest severity among grouped findings
8. **Mixed groups:** If a logical group contains both actionable and blocked findings, split the group. The actionable findings form the Jira ticket. The blocked findings are listed in the References section as deferred related work but are NOT included in Acceptance Criteria.

## Output Rules

- Use Jira wiki markup, NOT Markdown (Jira renders wiki markup natively)
- Keep descriptions concise — link to code rather than pasting entire files
- Include code snippets only for the specific vulnerable pattern and its fix
- Do not include tool attribution or AI-generated disclaimers in the ticket
