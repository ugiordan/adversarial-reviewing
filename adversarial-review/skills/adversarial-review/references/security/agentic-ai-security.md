---
name: agentic-ai-security
specialist: security
version: "1.0.0"
last_updated: "2026-03-26"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-review/main/adversarial-review/skills/adversarial-review/references/security/agentic-ai-security.md"
description: "OWASP Agentic AI risks ASI01-ASI10 with verification patterns"
enabled: true
---

# OWASP Agentic AI Security — Verification Patterns

## Risk Table

| ID | Risk | Key Mitigation |
|----|------|---------------|
| ASI01 | Excessive Agency | Least-privilege tool access, explicit user approval for actions |
| ASI02 | Uncontrolled Autonomy | Human-in-the-loop for irreversible actions |
| ASI03 | Insecure Tool Integration | Input validation for tool parameters, output sanitization |
| ASI04 | Inadequate Sandboxing | Process isolation, filesystem restrictions |
| ASI05 | Credential Mismanagement | Scoped credentials, no credential sharing between agents |
| ASI06 | Untrusted Agent Communication | Authenticated inter-agent channels, message integrity |
| ASI07 | Insufficient Logging | Audit trail for all agent actions and tool invocations |
| ASI08 | Prompt Injection via Tools | Tool output treated as data, not instructions |
| ASI09 | Supply Chain Risks | Verified agent/tool sources, integrity checks |
| ASI10 | Denial of Wallet | Token budgets, rate limiting, cost controls |

## Verification Checklist

### Tool Permissions
- Are tool permissions scoped to minimum required access?
- Is there explicit approval required before destructive actions (file deletion, git push)?
- Are tool parameters validated before execution?
- Is tool output sanitized before being passed to the model?

### Credential Scoping
- Are API keys and tokens scoped to specific operations?
- Are credentials rotated on a schedule?
- Is credential access logged?
- Are credentials shared between agents or sessions? (They should not be.)

### Communication Security
- Are inter-agent messages authenticated?
- Is agent identity verified before accepting instructions?
- Are agent outputs treated as untrusted data by receiving agents?

### Resource Controls
- Are token budgets enforced per-session and per-agent?
- Is there rate limiting on tool invocations?
- Are timeouts set for agent operations?
- Is there a kill switch for runaway agents?

**False positive checklist:**
- Before flagging agent autonomy: Does the system require explicit user confirmation for irreversible actions?
- Before flagging credential issues: Are credentials injected via environment variables (not hardcoded)?
