# RHOAI Constraint Pack

Organizational constraint pack for Red Hat OpenShift AI (RHOAI) reviews. Contains 10 enforced constraints covering FIPS, auth patterns, RBAC scope, secrets management, image provenance, and more, plus 3 detailed reference modules.

## Usage

```bash
# Strategy review with RHOAI constraints
adversarial-review --profile strat --constraints packs/rhoai/ strategy.md

# Code review with RHOAI constraints
adversarial-review --constraints packs/rhoai/ src/
```

## Constraints (constraints.yaml)

| ID | Title | Severity | Profile |
|----|-------|----------|---------|
| RHOAI-FIPS | FIPS 140-3 compliance required | High | Both |
| RHOAI-PQC | Post-quantum/FIPS transition awareness | Minor | Strat |
| RHOAI-TLS | TLS profile compliance | High | Both |
| RHOAI-GATEWAY | Use OpenShift Gateway API | Important | Strat |
| RHOAI-MESH | Do not require Istio unless necessary | Important | Strat |
| RHOAI-IMAGES | Image provenance from trusted registries | High | Both |
| RHOAI-UPSTREAM | Upstream-first contribution policy | Important | Strat |
| RHOAI-AUTH | Use approved auth patterns | High | Both |
| RHOAI-SECRETS | Approved secrets management patterns | High | Both |
| RHOAI-RBAC | ServiceAccount RBAC namespace-scoped | High | Both |

## Reference Modules

Detailed context supporting the constraints:

- `rhoai-auth-patterns.md`: 4 approved auth patterns (kube-auth-proxy, kube-rbac-proxy, Kuadrant, ServiceAccount RBAC)
- `rhoai-platform-constraints.md`: Platform deployment model, multi-tenancy, service mesh, RBAC scope, secrets, image provenance
- `productization-requirements.md`: Red Hat productization checklist (docs, upgrade, telemetry, FIPS, testing)
