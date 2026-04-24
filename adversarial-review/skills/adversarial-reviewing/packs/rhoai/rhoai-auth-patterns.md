---
name: rhoai-auth-patterns
specialist: all
version: "1.0.0"
last_updated: "2026-04-04"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-reviewing/main/adversarial-review/skills/adversarial-reviewing/packs/rhoai/rhoai-auth-patterns.md"
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
- **API key lifecycle (when using Kuadrant API keys):** Keys must be crypto-random (min 32 bytes), stored encrypted at rest (OpenShift Secrets with encryption-at-rest or external secret store), rotated every 90 days max, support revocation without service restart (dynamic config reload), and never logged in plaintext.

## Pattern 4: ServiceAccount RBAC (Workload Authorization)

- **Where:** Kubernetes API server, evaluated on every API call from a Pod's ServiceAccount
- **What:** Controls which Kubernetes resources a workload (Pod) can access via its ServiceAccount
- **Components using it:** All RHOAI controllers, operators, and workloads that interact with the Kubernetes API
- **When to use:** Any component that makes Kubernetes API calls (creating/watching resources, accessing secrets, managing CRDs)
- **Design principles:**
    - Each component gets its own ServiceAccount (never use the default SA)
    - Use namespace-scoped Role/RoleBinding by default
    - ClusterRole/ClusterRoleBinding requires written justification (why namespace scope is insufficient, which cluster resources are needed, privilege escalation mitigation)
    - Use specific verbs and resource names (never `*`)
    - Prefer TokenRequest API for short-lived tokens over long-lived SA tokens
- **What to check:** Strategy specifies RBAC scope, uses least-privilege verbs, justifies any cluster-wide permissions

## Review Guidance

- If a strategy introduces a new endpoint without specifying which auth pattern applies, that is a finding
- If a strategy proposes a custom auth mechanism not listed above, that requires strong justification
- Platform-level auth (Pattern 1) is not sufficient for multi-tenant isolation; Pattern 2 or 3 is also needed
- Strategies touching auth should reference the specific pattern by name, not just "authentication will be handled"
