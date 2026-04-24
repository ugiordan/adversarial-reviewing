# Usage Examples

Real-world usage patterns for adversarial-reviewing beyond the basics in the README.

## Reviewing a PR Before Merge

Review only the files changed in a PR with diff-augmented input:

```
/adversarial-reviewing --diff --range origin/main..HEAD
```

Add `--save` to keep a record:

```
/adversarial-reviewing --diff --range origin/main..HEAD --save
```

## Security Audit of Auth Code

Targeted security review with thorough mode for critical paths:

```
/adversarial-reviewing src/auth/ src/middleware/ --security --thorough --save
```

## Triaging CodeRabbit Comments

Evaluate whether automated review comments are worth fixing:

```
/adversarial-reviewing --triage pr:42 --diff
```

With gap analysis to find what the automated reviewer missed:

```
/adversarial-reviewing --triage pr:42 --diff --gap-analysis
```

## Quick Smoke Check

Fast review with 2 specialists before pushing:

```
/adversarial-reviewing --quick --diff
```

## Full Review with Auto-Remediation

Review, then generate Jira tickets and fix branches:

```
/adversarial-reviewing src/ --thorough --fix --save
```

Preview what remediation would do without writing anything:

```
/adversarial-reviewing src/ --thorough --fix --dry-run
```

## Reviewing a Large Codebase

For repos with > 200 files, use `--force` with targeted scope:

```
/adversarial-reviewing src/api/ src/services/ --force --thorough
```

Or break into focused reviews:

```
/adversarial-reviewing src/api/ --security --save
/adversarial-reviewing src/services/ --quality --correctness --save
```

## Custom Reference Modules

Add project-specific security patterns at `.adversarial-review/references/security/`:

```markdown
---
name: Internal Auth Patterns
specialist: security
version: "1.0.0"
enabled: true
---

## Custom OAuth Flow
- Verify token rotation happens on every refresh
- Check that PKCE is enforced for public clients
```

Then review — the module is automatically discovered:

```
/adversarial-reviewing src/auth/ --security --list-references
```

## Delta Reviews

After fixing issues from a previous review, re-review only what changed:

```
/adversarial-reviewing --delta --save
```
