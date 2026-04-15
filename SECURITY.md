# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Adversarial Review, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email: **ugo.giordano@proton.me**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive a response within 72 hours. We will work with you to understand the issue and coordinate a fix before any public disclosure.

## Security Architecture

This tool handles security-sensitive operations:

- **Code review** — agents analyze source code that may contain secrets or sensitive logic
- **External input parsing** — `--triage` mode processes external review comments that could contain injection attempts
- **Shell script execution** — validation scripts run on agent output
- **External integrations** — `--fix` mode can interact with GitHub and Jira APIs

### Design Principles

- All agent output validation is **programmatic** (shell scripts), never LLM-based
- Agent contexts are **fully isolated** — no agent sees another's raw output
- Input is wrapped with **CSPRNG random delimiters** (128-bit) to prevent injection
- **Unicode normalization** (NFKC) and injection heuristics detect prompt manipulation
- The tool **never commits to git** without explicit user confirmation
- **Destructive pattern detection** scans recommended fixes for dangerous commands

### Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Scope

The following are in scope for security reports:

- Prompt injection bypasses (delimiter escape, instruction override)
- Shell injection through agent output or external comments
- Unauthorized external actions (git push, Jira ticket creation without consent)
- Budget enforcement bypasses
- Information leakage between isolated agents

The following are out of scope:

- Issues requiring physical access to the machine
- Social engineering of the human user
- Denial of service via resource exhaustion (covered by budget guardrails)
