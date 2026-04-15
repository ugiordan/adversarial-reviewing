---
name: rhoai-auth-patterns
specialist: all
version: "1.0.0"
last_updated: "2026-04-04"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-review/main/adversarial-review/skills/adversarial-review/profiles/strat/references/all/rhoai-auth-patterns.md"
description: "Approved RHOAI authentication and authorization patterns for strategy review"
enabled: true
---

# Approved RHOAI Auth Patterns

Strategies proposing auth changes must align with one of these approved patterns. Deviations are valid review findings.

## Pattern 1: kube-auth-proxy (Platform Ingress)

- **Where:** Gateway API layer via Envoy ext_authz filter
- **What:** Authenticates all external traffic entering the platform
- **Components using it:** Dashboard, notebook spawner UI, model serving endpoints
- **When to use:** Any new externally-reachable endpoint that needs platform-level auth
- **What to check:** Strategy mentions auth at the ingress/gateway level, references kube-auth-proxy or ext_authz

## Pattern 2: kube-rbac-proxy (Per-Service RBAC)

- **Where:** Sidecar container on individual services
- **What:** Kubernetes RBAC enforcement via SubjectAccessReview for service-level access control
- **Components using it:** Prometheus metrics endpoints, operator webhooks, internal APIs
- **When to use:** Service needs fine-grained Kubernetes RBAC beyond what ingress provides
- **What to check:** Strategy mentions per-service authorization, references kube-rbac-proxy or SubjectAccessReview

## Pattern 3: Kuadrant (API-Level Auth + Rate Limiting)

- **Where:** API gateway layer via Authorino + Limitador
- **What:** AuthPolicy for API auth (OAuth, API keys, OIDC), TokenRateLimitPolicy for rate limiting
- **Components using it:** Model serving APIs, inference endpoints, external integrations
- **When to use:** APIs needing OAuth/OIDC token validation, per-client rate limiting, or multi-tenant API access control
- **What to check:** Strategy mentions API auth, token validation, rate limiting, references Kuadrant/Authorino/Limitador

## Review Guidance

- If a strategy introduces a new endpoint without specifying which auth pattern applies, that is a finding
- If a strategy proposes a custom auth mechanism not listed above, that requires strong justification
- Platform-level auth (Pattern 1) is not sufficient for multi-tenant isolation; Pattern 2 or 3 is also needed
- Strategies touching auth should reference the specific pattern by name, not just "authentication will be handled"
