# Triage Mode

Triage mode evaluates external review comments instead of performing independent review. Use it to assess feedback from CodeRabbit, human reviewers, or PR conversations.

## Usage

```bash
# Triage PR comments (requires GitHub MCP tools)
/adversarial-reviewing --triage pr:42

# Triage comments from a file
/adversarial-reviewing --triage file:reviews/comments.json

# Read comments from stdin
/adversarial-reviewing --triage -
```

## How it works

1. Comments are parsed and normalized via `parse-comments.sh`
2. Each specialist evaluates every comment from their perspective
3. Each comment receives a verdict: **Fix**, **No-Fix**, or **Investigate**
4. Verdicts include confidence levels and technical analysis
5. Comments go through the same challenge/resolution pipeline as regular findings

## Triage verdict format

```
Comment ID: C-001
Source: CodeRabbit
File: src/auth/handler.go
Line: 42
Original comment: "This function doesn't validate the JWT token expiry"
Verdict: Fix
Confidence: High
Severity: Important
Analysis: The comment correctly identifies that jwt.Parse() at line 42
does not check the exp claim. The token is used for authorization at
line 58 without expiry validation, allowing expired tokens to access
protected resources.
```

## Combined with diff context

For deeper analysis, combine triage with change-impact analysis:

```bash
/adversarial-reviewing --triage pr:42 --diff --thorough
```

This gives specialists both the external comments and the full change-impact graph for context.

## Gap analysis

Add `--gap-analysis` to identify areas the reviewers missed:

```bash
/adversarial-reviewing --triage pr:42 --gap-analysis
```

The gap analysis section shows coverage by specialist domain and highlights files or patterns that received no review attention.

## Comment sources

### PR comments (`pr:<N>`)

Requires GitHub MCP tools. Fetches comments from the specified PR number.

### File (`file:<path>`)

Reads comments from a JSON file. Expected format:

```json
[
  {
    "id": "C-001",
    "source": "human",
    "file": "src/auth/handler.go",
    "line": 42,
    "body": "This function doesn't validate the JWT token expiry"
  }
]
```

### Stdin (`-`)

Reads the same JSON format from stdin. Useful for piping from other tools.
