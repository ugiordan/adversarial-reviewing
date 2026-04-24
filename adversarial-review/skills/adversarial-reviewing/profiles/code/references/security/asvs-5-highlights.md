---
name: asvs-5-highlights
specialist: security
version: "1.0.0"
last_updated: "2026-03-26"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-reviewing/main/adversarial-review/skills/adversarial-review/references/security/asvs-5-highlights.md"
description: "ASVS 5.0 most commonly violated requirements by verification level"
enabled: true
---

# ASVS 5.0 Highlights — Verification Patterns

## Most Commonly Violated Requirements

### Level 1 (Minimum)

**Authentication (V2)**
- Is multi-factor authentication available for sensitive operations?
- Are password policies enforced (minimum length, no common passwords)?
- Is credential stuffing protection present (rate limiting, CAPTCHA)?

**Session Management (V3)**
- Are session tokens generated with sufficient entropy (128+ bits)?
- Are sessions invalidated on logout?
- Is session fixation prevented (new session ID after authentication)?

**Access Control (V4)**
- Is the principle of least privilege applied?
- Are access control decisions made server-side (not client-only)?
- Is directory listing disabled?

### Level 2 (Standard)

**Input Validation (V5)**
- Is all input validated against an expected schema?
- Are file uploads restricted by type, size, and scanned for malware?
- Is output encoding context-aware (HTML, URL, JavaScript, CSS)?

**Cryptography (V6)**
- Are all random values generated using a CSPRNG?
- Are cryptographic keys managed through a key management system?
- Is certificate pinning implemented for mobile and sensitive applications?

**Error Handling (V7)**
- Do error messages avoid exposing sensitive information?
- Is exception handling consistent (no silent catch-and-ignore)?
- Are security events logged with sufficient detail for forensics?

### Level 3 (Advanced)

**Data Protection (V8)**
- Is sensitive data classified and handled according to classification?
- Is data retention enforced (automatic expiry of temporary data)?
- Are privacy controls implemented (data minimization, right to deletion)?

**Communication (V9)**
- Is TLS 1.2+ enforced for all connections?
- Is certificate validation enabled (no skipping for convenience)?
- Are WebSocket connections authenticated?

**False positive checklist:**
- Before flagging missing input validation: Is the input from a trusted internal service with its own validation?
- Before flagging error handling: Is the catch-and-ignore in a best-effort cleanup path (e.g., closing resources)?
- Before flagging TLS version: Is the system on an internal network with no external exposure?
