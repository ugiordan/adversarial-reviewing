# Usage Examples

Real-world usage patterns for adversarial-review beyond the basics in the README.

## Reviewing a PR Before Merge

Review only the files changed in a PR with diff-augmented input:

```
/adversarial-review --diff --range origin/main..HEAD
```

Add `--save` to keep a record:

```
/adversarial-review --diff --range origin/main..HEAD --save
```

## Security Audit of Auth Code

Targeted security review with thorough mode for critical paths:

```
/adversarial-review src/auth/ src/middleware/ --security --thorough --save
```

## Triaging CodeRabbit Comments

Evaluate whether automated review comments are worth fixing:

```
/adversarial-review --triage pr:42 --diff
```

With gap analysis to find what the automated reviewer missed:

```
/adversarial-review --triage pr:42 --diff --gap-analysis
```

## Quick Smoke Check

Fast review with 2 specialists before pushing:

```
/adversarial-review --quick --diff
```

## Full Review with Auto-Remediation

Review, then generate Jira tickets and fix branches:

```
/adversarial-review src/ --thorough --fix --save
```

Preview what remediation would do without writing anything:

```
/adversarial-review src/ --thorough --fix --dry-run
```

## Reviewing a Large Codebase

For repos with > 200 files, use `--force` with targeted scope:

```
/adversarial-review src/api/ src/services/ --force --thorough
```

Or break into focused reviews:

```
/adversarial-review src/api/ --security --save
/adversarial-review src/services/ --quality --correctness --save
```

## Custom Reference Modules

Add project-specific security patterns at `.adversarial-review/references/security/`:

```markdown
---
title: Internal Auth Patterns
specialist: security
version: "1.0"
---

## Custom OAuth Flow
- Verify token rotation happens on every refresh
- Check that PKCE is enforced for public clients
```

Then review — the module is automatically discovered:

```
/adversarial-review src/auth/ --security --list-references
```

## Delta Reviews

After fixing issues from a previous review, re-review only what changed:

```
/adversarial-review --delta --save
```
