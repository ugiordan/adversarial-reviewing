---
name: productization-requirements
specialist: all
version: "1.0.0"
last_updated: "2026-04-04"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-review/main/adversarial-review/skills/adversarial-review/profiles/strat/references/all/productization-requirements.md"
description: "Red Hat productization requirements checklist for strategy completeness review"
enabled: true
---

# Red Hat Productization Requirements

Strategies that introduce or modify RHOAI features must address these productization areas. Missing coverage is a valid completeness finding.

## Supportability

- **Documentation.** User-facing features need docs updates (upstream + downstream). API changes require reference docs with examples.
- **Runbooks.** New alerts must have corresponding runbooks. New failure modes need troubleshooting guidance.
- **must-gather.** New components or data stores must be covered by must-gather scripts for support diagnostics.

## Upgrade Path

- **N-1 compatibility.** APIs, CRDs, and stored data formats must remain compatible with the previous version during rolling upgrades.
- **Migration scripts.** Breaking changes require automated migration (not manual steps). Migration must be idempotent and reversible where possible.
- **Feature gates.** New features should support a feature gate mechanism for phased rollout and emergency disable.

## Telemetry and Monitoring

- **Metrics.** New components must expose Prometheus metrics. Strategy should name the key metrics.
- **Alerts.** Critical failure modes need PrometheusRule alerts. Strategy should specify alert conditions and severity.
- **SLOs.** Features with user-facing latency or availability requirements should define SLO targets.

## Security Hardening

- **CVE response.** Strategy must account for how CVEs in new dependencies will be tracked and patched.
- **Image scanning.** All new container images must pass the Red Hat container certification pipeline.
- **FIPS compliance.** If the feature handles cryptographic operations, note whether FIPS 140-2/3 validated libraries are used.

## Testing

- **E2E tests.** New features require end-to-end test coverage before GA.
- **Upgrade tests.** N-1 to N upgrade path must be tested, including data migration.
- **Interop matrix.** Test combinations with supported OpenShift versions, storage backends, and GPU configurations.

## Release Gating

- **GA readiness.** Features are Tech Preview by default. GA promotion requires: full test coverage, documentation, upgrade path validation, and support readiness.
- **Release notes.** New features, breaking changes, and deprecations must have release note entries.
