# Change-Impact Analysis

!!! info "Code profile only"
    Change-impact analysis is only available with the code profile (default). It requires source code with git history and is not applicable to strategy document reviews.

The `--diff` flag enriches the review with git diff context and a change-impact graph showing callers and callees of modified symbols.

## Usage

```bash
# Diff against current HEAD
/adversarial-review src/ --diff

# Specify a commit range
/adversarial-review src/ --diff --range main..HEAD

# Combined with triage
/adversarial-review --triage pr:42 --diff
```

## What it provides

When `--diff` is active, each specialist receives:

1. **The raw git diff** of changed files
2. **Changed files list** with modification type (added/modified/deleted)
3. **Change-impact graph** built by `build-impact-graph.sh`

### Change-impact graph

The impact graph uses grep-based symbol analysis to trace:

- **Callers**: Functions that call the modified symbols
- **Callees**: Functions called by the modified code
- **Affected types**: Structs and interfaces used by changed functions

This helps specialists identify side effects. For example, if a function signature changes, the impact graph shows all callers that might need updating.

### Example output

```
Changed symbol: pkg/auth.ValidateToken
  Callers:
    - pkg/middleware.AuthMiddleware (middleware.go:28)
    - cmd/server.handleLogin (server.go:115)
    - pkg/api.RefreshToken (api.go:72)
  Callees:
    - pkg/crypto.VerifySignature (crypto.go:45)
    - pkg/store.GetPublicKey (store.go:33)
```

## When to use it

- Reviewing PRs where you want specialists to focus on what changed
- Re-reviewing after fixes to verify the fix doesn't break callers
- Combining with `--triage` to give specialists full context when evaluating external comments

## How it works internally

1. `build-impact-graph.sh` extracts changed symbols from the git diff
2. For each changed symbol, it searches the codebase for references (callers)
3. It also extracts function calls within the changed code (callees)
4. The graph is serialized and injected into each specialist's input alongside the diff

The graph is grep-based (not AST-based) to stay fast and language-agnostic. This means it may produce false positives for common symbol names, but it prioritizes recall over precision.
