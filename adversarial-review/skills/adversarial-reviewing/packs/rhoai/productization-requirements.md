---
name: productization-requirements
specialist: all
version: "1.0.0"
last_updated: "2026-04-04"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-reviewing/main/adversarial-review/skills/adversarial-reviewing/packs/rhoai/productization-requirements.md"
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
- **FIPS compliance (MANDATORY).** Identify all cryptographic operations in the feature, including: random number generation, hashing (SHA, HMAC), encryption/decryption, TLS/mTLS, signed tokens, digital signatures. For each operation, verify: (1) library used (OpenSSL, Go crypto, etc.), (2) FIPS 140-3 certification status on RHEL 9, (3) FIPS mode enforcement mechanism. Features without crypto operations must explicitly state: "No cryptographic operations identified; FIPS compliance N/A." Note: NIST post-quantum algorithms (ML-KEM, ML-DSA) are not yet FIPS-validated. Strategies introducing new crypto primitives should document the migration path for post-quantum readiness.

## Testing

- **E2E tests.** New features require end-to-end test coverage before GA.
- **Upgrade tests.** N-1 to N upgrade path must be tested, including data migration.
- **Interop matrix.** Test combinations with supported OpenShift versions, storage backends, and GPU configurations.

## Release Gating

- **GA readiness.** Features are Tech Preview by default. GA promotion requires: full test coverage, documentation, upgrade path validation, and support readiness.
- **Release notes.** New features, breaking changes, and deprecations must have release note entries.
