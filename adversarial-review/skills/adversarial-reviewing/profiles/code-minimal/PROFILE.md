# Code-Minimal Profile Details

Eval variant of the `code` profile with specialist persona framing removed. Agent definitions keep identical focus areas, detection patterns, and operational instructions. Only the Role Definition line and header are modified to strip identity language ("You are a X specialist").

Loaded by the orchestrator when `--profile code-minimal` is active.

## Specialist Flags

| Flag | Specialist | Agent File |
|------|-----------|------------|
| `--security` | Security Auditor | `profiles/code-minimal/agents/security-auditor.md` |
| `--performance` | Performance Analyst | `profiles/code-minimal/agents/performance-analyst.md` |
| `--quality` | Code Quality Reviewer | `profiles/code-minimal/agents/code-quality-reviewer.md` |
| `--correctness` | Correctness Verifier | `profiles/code-minimal/agents/correctness-verifier.md` |
| `--architecture` | Architecture Reviewer | `profiles/code-minimal/agents/architecture-reviewer.md` |

## Preset Profiles

| Flag | Specialists | Iterations | Budget |
|------|-------------|------------|--------|
| `--quick` | SEC + CORR (2) | 2 | 150K |
| `--thorough` | All 5 | 3 | 800K |
| *(default)* | All 5 | 3 | 350K |

## What Changed vs code Profile

Only the Role Definition section of each agent file:

| Original (code) | Modified (code-minimal) |
|-----------------|------------------------|
| `# Security Auditor (SEC)` | `# SEC Agent` |
| "You are a **Security Auditor** specialist. Your role prefix is **SEC**. You perform adversarial security review..." | "Review code for security vulnerabilities, weaknesses, and security anti-patterns. Use role prefix **SEC** and specialist name **Security Auditor** in your findings." |

Same pattern for all 5 agents. Everything else is symlinked from the `code` profile (shared/, templates/, references/).
