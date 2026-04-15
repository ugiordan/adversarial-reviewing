# Recurring NFR Checklist for RHOAI Strategy Reviews

**Derived from:** Adversarial review of 5 STRATs (1452, 1454, 1456, 1446, 1444)
**Date:** 2026-04-09
**Purpose:** Every STRAT should be checked against these items before approval. Items marked with frequency indicate how many of the 5 reviewed STRATs had the gap.

---

## Authentication & Authorization (5/5 STRATs had gaps)

- [ ] **Auth pattern specified**: Strategy names which RHOAI-approved auth pattern gates every new API/UI surface (kube-auth-proxy via Istio, kube-rbac-proxy sidecar, or Kuadrant)
- [ ] **RBAC mapping defined**: New operations are mapped to specific Kubernetes RBAC verbs/resources/scopes
- [ ] **Multi-tenant access control**: User-facing data is filtered to the requesting tenant's scope (no cross-tenant visibility by default)
- [ ] **Privilege delegation bounded**: If non-admins get new capabilities (provisioning, configuration), admission controls and quota ceilings are specified

## Testability (4/5 STRATs had gaps)

- [ ] **ACs are measurable**: Every acceptance criterion has a concrete pass/fail definition (not "seamlessly", "successfully", "without degradation")
- [ ] **Deterministic vs non-deterministic separated**: System behavior ACs (testable) are distinct from model quality ACs (probabilistic)
- [ ] **Performance targets quantified**: Latency, throughput, and resource consumption targets specify percentile (p50/p95/p99), load conditions, hardware, and measurement methodology
- [ ] **Regression baseline defined**: Strategy references or creates a specific test suite with recorded baselines for regression comparison
- [ ] **Interoperability matrix explicit**: If strategy spans multiple models, formats, or backends, the coverage matrix is explicitly defined (not "at least" or "applicable combinations")

## Security (4/5 STRATs had gaps)

- [ ] **Threat model for new surfaces**: Every new endpoint, data store, or trust boundary has a threat model (even lightweight)
- [ ] **Supply chain provenance**: External dependencies (model weights, drivers, firmware, SDKs) specify verification method (checksums, signatures, pinned versions, SBOM)
- [ ] **Observability for security events**: Security-relevant actions (enforcement, access decisions, provisioning) emit metrics or logs at configurable verbosity
- [ ] **Defense-in-depth preserved**: New enforcement mechanisms are additive to existing validation, not replacements
- [ ] **Session/state management**: Any persistent state specifies encryption at rest, TTL/expiry, deletion API, and access control

## Feasibility (4/5 STRATs had gaps)

- [ ] **Effort estimated**: Strategy includes T-shirt sizing per work stream and maps to release trains
- [ ] **Dependency chain assessed**: External dependencies (upstream RFCs, third-party releases, hardware availability) have contingency plans and fallback dates
- [ ] **Team capacity identified**: Required skills and team composition are documented (not just an assignee name)
- [ ] **Phased delivery**: Large strategies are decomposed into independently deliverable stages with validation gates between stages
- [ ] **Upstream gap analysis**: If strategy depends on upstream project APIs, features, or releases, a gap analysis confirms the required capabilities exist (or documents what needs to be contributed)

## Compliance & Governance (3/5 STRATs had gaps)

- [ ] **Audit logging specified**: All administrative and security-relevant actions emit audit events compatible with OpenShift audit pipeline
- [ ] **Data retention policy**: Persistent data (sessions, logs, cached state) has defined retention, access control, and purge mechanisms
- [ ] **Disconnected environment considered**: If targeting regulated/government customers, strategy addresses air-gapped deployment and testing

## Cross-Cutting

- [ ] **Streaming considered**: If strategy involves streaming (SSE, gRPC streams), partial-state behavior, connection limits, and backpressure are specified
- [ ] **Backward compatibility assessed**: Breaking changes are identified with migration paths and compatibility periods
- [ ] **Version pinning**: External tools, SDKs, or models specify pinned versions (not "latest" or "at least one")

---

## How to Use

1. Before a STRAT is approved, run through this checklist
2. Items that are N/A for the STRAT should be marked as such with a brief reason
3. Items that are gaps should be flagged as findings for revision
4. This checklist should be updated as more STRATs are reviewed and new patterns emerge
