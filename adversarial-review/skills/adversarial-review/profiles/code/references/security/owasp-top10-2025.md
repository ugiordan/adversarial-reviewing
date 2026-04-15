---
name: owasp-top10-2025
specialist: security
version: "1.0.0"
last_updated: "2026-03-26"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-review/main/adversarial-review/skills/adversarial-review/references/security/owasp-top10-2025.md"
description: "OWASP Top 10:2025 vulnerability categories with code-level verification patterns"
enabled: true
---

# OWASP Top 10:2025 — Verification Patterns

## Quick Reference

| # | Category | Key Prevention |
|---|----------|---------------|
| A01 | Broken Access Control | Authorization checks at every access point |
| A02 | Cryptographic Failures | Strong algorithms, proper key management |
| A03 | Injection | Parameterized queries, input validation |
| A04 | Insecure Design | Threat modeling, secure design patterns |
| A05 | Security Misconfiguration | Hardened defaults, minimal permissions |
| A06 | Vulnerable Components | Dependency scanning, version pinning |
| A07 | Authentication Failures | MFA, credential rotation, session management |
| A08 | Data Integrity Failures | Signed updates, CI/CD pipeline security |
| A09 | Logging & Monitoring Failures | Audit trails, alerting on anomalies |
| A10 | SSRF | Allowlist URLs, validate redirects |

## Verification Patterns

### A01: Broken Access Control
- Is authorization checked on EVERY endpoint, not just the UI layer?
- Are object-level authorization checks present (IDOR prevention)?
- Does the API enforce access control for each function, not just at the route level?
- Are CORS policies restrictive (not `Access-Control-Allow-Origin: *`)?

**False positive checklist:**
- Before flagging missing auth: Is this an intentionally public endpoint (health check, metrics, login)?
- Before flagging CORS: Is the wildcard origin on a truly public API with no credentials?

### A02: Cryptographic Failures
- Are deprecated algorithms used (MD5, SHA1, DES, RC4)?
- Is TLS certificate validation disabled (`InsecureSkipVerify`, `verify=False`)?
- Are encryption keys hardcoded or committed to source control?
- Is sensitive data encrypted at rest and in transit?

**Safe/unsafe patterns:**
```
# Unsafe: disabled TLS verification
http.Client{Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}}}
# Safe: default TLS verification
http.Client{}
```

### A03: Injection
- Are SQL queries parameterized (not string-concatenated)?
- Is user input passed to shell commands via proper escaping?
- Are template engines configured for auto-escaping?
- Is deserialization restricted to known types?

**False positive checklist:**
- Before flagging SQL injection: Is the query using parameterized placeholders ($1, ?, :param)?
- Before flagging command injection: Is the input from a trusted internal source (not user-facing)?

### A04: Insecure Design
- Are rate limits implemented for authentication and sensitive endpoints?
- Is input validated against a schema (not just "is it present")?
- Are business logic flows protected against abuse (e.g., order manipulation)?

### A05: Security Misconfiguration
- Are default credentials changed?
- Are unnecessary features/ports/services disabled?
- Are error messages generic (no stack traces to users)?
- Are security headers present (CSP, X-Content-Type-Options, X-Frame-Options)?

### A06: Vulnerable Components
- Are dependencies pinned to specific versions (not floating ranges)?
- Is there a dependency scanning mechanism (Dependabot, Snyk, Trivy)?
- Are known-vulnerable versions in use?

### A07: Authentication Failures
- Are passwords hashed with modern algorithms (bcrypt, scrypt, argon2)?
- Is session management secure (HttpOnly, Secure, SameSite cookies)?
- Are brute-force protections in place (rate limiting, account lockout)?

### A08: Data Integrity Failures
- Are software updates and CI/CD pipelines integrity-checked?
- Is deserialization from untrusted sources avoided or type-restricted?

### A09: Logging & Monitoring Failures
- Are authentication events (login, logout, failed attempts) logged?
- Are logs protected against injection (structured logging, not string formatting)?
- Is sensitive data excluded from logs (passwords, tokens, PII)?

### A10: SSRF
- Are outbound URLs validated against an allowlist?
- Are internal network addresses (RFC 1918, localhost, metadata endpoints) blocked?
- Is URL redirection validated?

**False positive checklist:**
- Before flagging SSRF: Does the code actually make outbound HTTP requests with user-controlled URLs?
- Before flagging metadata access: Is the code running in a cloud environment with instance metadata?
