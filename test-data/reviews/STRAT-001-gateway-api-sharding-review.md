---
strat_id: STRAT-001
title: RHOAI support for Ingress / Gateway API sharding
tool: adversarial-review
profile: strat
mode: default (all 5 specialists, iteration 1)
date: 2026-04-08
recommendation: reject
verdicts:
  feasibility: revise
  architecture: revise
  security: revise
  user-impact: revise
  scope-completeness: reject
total_findings: 36
findings_by_severity:
  critical: 7
  important: 20
  minor: 9
---

# STRAT-001: Gateway API Sharding — Adversarial Review

## Executive Summary

Strategy STRAT-001 proposes moving RHOAI from a single-gateway architecture to multi-gateway support, allowing customers to route notebooks and model serving endpoints through different IngressController shards for network zone isolation. Five specialist agents (Feasibility, Architecture, Security, User Impact, Scope & Completeness) independently reviewed the strategy.

**Overall recommendation: REJECT** (for revision). All five specialists found significant issues. The strategy has a sound technical premise but critical gaps in feasibility validation, security enforcement, architectural integration, and scope definition make it unimplementable as written.

**Key cross-cutting findings** (agreed by 3+ specialists):

1. **OCP Gateway API sharding is an unvalidated prerequisite** (FEAS, ARCH, SCOP, SEC, USER): The entire strategy depends on OCP IngressController provisioning separate GatewayClass resources per shard, but this capability is listed as an "Open Question," not a validated dependency. If it doesn't exist, the strategy collapses.

2. **Gateway selection mechanism is undecided** (FEAS, ARCH, USER, SCOP, SEC): Three options are presented (namespace annotation, Notebook CR field, namespace default) with no decision. This blocks implementation, RBAC design, and UX planning.

3. **Authentication/authorization model is missing** (SEC, ARCH, USER): No RBAC model for who can assign gateways, no admission control for gateway references, no enforcement preventing zone reclassification by namespace admins.

4. **Effort dramatically underestimated** (FEAS, SCOP): "L" estimate covers 5 components across 4 teams with no breakdown. Multiple specialists estimate XL-XXL or recommend splitting into 3-4 epics.

5. **Backwards compatibility is promised but unspecified** (ARCH, USER, SCOP): DSCI spec migration, dual-mode routing during transition, and upgrade testing are all undefined.

---

## Feasibility (FEAS) — Verdict: REVISE

### FEAS-001 — OCP Gateway API sharding capability is unverified prerequisite
- **Severity:** Critical | **Confidence:** High
- **Citation:** Dependencies section
- **Evidence:** Strategy states "multi-GatewayClass support depends on the OpenShift IngressController operator correctly provisioning separate GatewayClass resources per shard. This is an OCP platform capability, not RHOAI-controlled." Listed as Open Question but is the foundational dependency. The mitigation ("early spike/PoC") does not answer whether the feature exists at all.
- **Fix:** Require pre-implementation spike (1-2 weeks) to validate OCP multi-GatewayClass support. Document minimum OCP version. If capability doesn't exist, strategy must be revised or blocked.

### FEAS-002 — Effort estimate "L" lacks breakdown for multi-team coordination
- **Severity:** Important | **Confidence:** High
- **Citation:** Affected Components table, Effort estimate
- **Evidence:** 4 impacted teams, 5 major components, no per-component breakdown, no timeline, no cross-team coordination buffer.
- **Fix:** Decompose into spike (1-2 weeks), Phase 1 by component (DSCI, notebook-controller, integration testing), Phase 2, with 20-30% coordination overhead.

### FEAS-003 — OSSM multi-Gateway support verification missing
- **Severity:** Important | **Confidence:** Medium
- **Citation:** Dependencies, Risks section
- **Evidence:** OSSM multi-Gateway support assumed but not verified. Fallback ("BYO Gateway outside mesh") would require different architecture not costed.
- **Fix:** Engage OSSM team to confirm support. If not available, revise strategy to use fallback as primary design with updated effort.

### FEAS-004 — Gateway assignment model undecided impacts scope and effort
- **Severity:** Important | **Confidence:** Medium
- **Citation:** Open Questions
- **Evidence:** Per-namespace vs per-workload is not a minor detail but a fundamental design decision affecting controller logic, dashboard UI, and testing surface.
- **Fix:** Decide before accepting strategy. Recommend per-namespace for Phase 1.

### FEAS-005 — Scope expansion risk to other RHOAI components
- **Severity:** Important | **Confidence:** High
- **Citation:** Open Questions, Scope Boundary
- **Evidence:** TrustyAI, data science pipelines, and other components may have single-gateway assumptions. No audit planned.
- **Fix:** Add pre-implementation audit (1 week) of all components creating routes/HTTPRoutes.

### FEAS-006 — Backwards compatibility testing scope not defined
- **Severity:** Minor | **Confidence:** Medium
- **Citation:** Technical Approach, NFR
- **Evidence:** Upgrade path (3.x to multi-gateway version) not specified. No test plan for validating single-gateway deployments unaffected.
- **Fix:** Define upgrade path explicitly with automated test cases.

---

## Architecture (ARCH) — Verdict: REVISE

### ARCH-001 — DSCI spec change lacks backward compatibility migration path
- **Severity:** Important | **Confidence:** High
- **Citation:** Technical Approach, paragraph 1
- **Evidence:** Moving from single gateway reference to "gateways list" without specifying how existing DSCI resources are migrated during upgrade.
- **Fix:** Auto-populate new gateways list with existing single gateway during upgrade. Define deprecation timeline for old field.

### ARCH-002 — Gateway selection mechanism lacks integration with DSCI namespace model
- **Severity:** Important | **Confidence:** Medium
- **Citation:** Technical Approach, paragraph 2
- **Evidence:** Unclear whether DSCI controller owns namespace gateway annotations or users set them manually. No validation that referenced gateway is in DSCI-configured list.
- **Fix:** Define ownership model. Add validation hook preventing namespace annotations from referencing unauthorized gateways.

### ARCH-003 — KNative gateway override conflicts with global configuration model
- **Severity:** Critical | **Confidence:** High
- **Citation:** Technical Approach, paragraph 3 (KNative mode)
- **Evidence:** KNative Serving's config-istio ConfigMap is intentionally global. Per-namespace overrides would require forking KNative or adding a controller layer.
- **Fix:** Limit Phase 2 to raw Kubernetes mode only, or add dependency on upstream KNative adding per-namespace gateway support.

### ARCH-004 — OSSM/SMCP configuration changes underspecified
- **Severity:** Important | **Confidence:** High
- **Citation:** Affected Components, istio/ossm row
- **Evidence:** "May need adjustments to SMCP" without specifying what. Multiple GatewayClass-backed Gateways may not map cleanly to Istio ingress gateway model.
- **Fix:** Add technical spike on SMCP configuration required. Clarify in-mesh vs mesh-external gateway topology.

### ARCH-005 — OCP dependency lacks version specificity
- **Severity:** Minor | **Confidence:** Medium
- **Citation:** Dependencies
- **Evidence:** No minimum OCP version specified for IngressController GatewayClass provisioning.
- **Fix:** Move from Open Questions to Dependencies with specific OCP version requirement.

### ARCH-006 — Dual-mode routing architecture has undefined conflict resolution
- **Severity:** Important | **Confidence:** High
- **Citation:** Technical Approach paragraph 2, Risks
- **Evidence:** Path-based and host-based routing may coexist during transition. No conflict resolution for overlapping path prefixes within a shared gateway.
- **Fix:** Clarify routing model within a single gateway. Specify whether path-based routing continues or all notebooks get unique hostnames.

### ARCH-007 — Dashboard gateway selection lacks RBAC boundary enforcement
- **Severity:** Minor | **Confidence:** Medium
- **Citation:** Affected Components, dashboard row
- **Evidence:** Dashboard will "surface gateway selection" but no RBAC filtering of available gateways per user.
- **Fix:** Dashboard should filter available gateways based on namespace permissions.

---

## Security (SEC) — Verdict: REVISE

### SEC-001 — Cross-gateway access control enforcement mechanism undefined
- **Severity:** Critical | **Confidence:** High | **Category:** Security Risk
- **Citation:** Technical Approach (notebook routing), NFR (Security)
- **Evidence:** Strategy claims "HTTPRoute parentRef binding provides this guarantee" for cross-gateway isolation, but parentRef determines routing attachment, not access control. No NetworkPolicies, no admission webhooks, no RBAC on Gateway resource access.
- **Fix:** Namespace-level RBAC restricting Gateway references. NetworkPolicy templates per zone. Validation webhook rejecting unauthorized parentRef values.

### SEC-002 — No authentication/authorization model for multi-gateway configuration
- **Severity:** Critical | **Confidence:** High | **Category:** NFR Gap
- **Evidence:** DSCI "gateways list" has no security model. Who can modify it? Can namespace admins add gateways exposing workloads to external zones?
- **Fix:** Restrict DSCI modification to cluster-admin. Implement Gateway allowlist. Namespace-to-gateway mapping enforcement.

### SEC-003 — KNative gateway override enables privilege escalation
- **Severity:** Critical | **Confidence:** Medium | **Category:** Security Risk
- **Evidence:** Per-namespace or per-InferenceService gateway overrides break KNative's cluster-scoped security model. Users could route through less-restricted gateways.
- **Fix:** Use per-namespace defaults only. Implement admission controller validating InferenceService routing.

### SEC-004 — Unvalidated OCP dependency creates undefined trust boundary
- **Severity:** Important | **Confidence:** High | **Category:** Security Risk
- **Evidence:** Trusting OCP GatewayClass provisioning without verification violates defense-in-depth. No runtime monitoring for GatewayClass convergence.
- **Fix:** DSCI validation querying Gateway resources. Runtime monitoring. Admission webhook rejecting same-GatewayClass configurations.

### SEC-005 — mTLS enforcement model undefined for multi-gateway
- **Severity:** Important | **Confidence:** High | **Category:** NFR Gap
- **Evidence:** Unclear whether Gateways are in-mesh or separate meshes. No PeerAuthentication policies specified for cross-zone isolation.
- **Fix:** Define mesh architecture. Document PeerAuthentication configuration. Specify workload identity model per zone.

### SEC-006 — Gateway reference SSRF risk via uncontrolled namespace
- **Severity:** Important | **Confidence:** High | **Category:** Security Risk
- **Evidence:** BYO Gateway model without namespace restrictions allows referencing Gateways in user-controlled namespaces, creating SSRF vector.
- **Fix:** Restrict Gateway references to controlled namespaces. Required authorization label on Gateway resources.

### SEC-007 — Namespace annotation gateway assignment enables zone reclassification
- **Severity:** Important | **Confidence:** Medium | **Category:** Security Risk
- **Evidence:** If namespace admins can modify gateway annotation, they can reassign workloads from restricted to permissive zones.
- **Fix:** Restrict annotation modification via admission webhook. Only cluster-admins set gateway assignment.

### SEC-008 — No audit logging for gateway assignment changes
- **Severity:** Important | **Confidence:** High | **Category:** NFR Gap
- **Evidence:** No audit events for gateway assignment changes, no monitoring for unexpected parentRef values, no cross-zone access metrics.
- **Fix:** Kubernetes audit events for all gateway changes. Prometheus metrics for routing distribution. AlertManager rules for drift detection.

### SEC-009 — Per-workload gateway assignment enables covert channel
- **Severity:** Important | **Confidence:** Medium | **Category:** NFR Gap
- **Evidence:** If per-workload gateway assignment is supported, users can spawn notebooks in different zones within same namespace, enabling data exfiltration via shared storage.
- **Fix:** Use per-namespace assignment only for zone separation. Document covert channel risk if per-workload is required.

### SEC-010 — Upgrade path security validation missing
- **Severity:** Minor | **Confidence:** High | **Category:** NFR Gap
- **Evidence:** Functional backwards compatibility promised but no security regression testing specified.
- **Fix:** Automated security regression tests for single-gateway mode on upgraded clusters.

### SEC-011 — Dashboard gateway selection without access control guidance
- **Severity:** Minor | **Confidence:** Medium | **Category:** Security Risk
- **Evidence:** All users see all gateways without zone labels or RBAC filtering.
- **Fix:** Show only authorized gateways with security zone labels.

### SEC-012 — Undefined scope creates inconsistent security posture
- **Severity:** Minor | **Confidence:** Low | **Category:** Security Risk
- **Evidence:** TrustyAI and pipelines may route through default gateway while notebooks use sharded gateways, breaking zone consistency.
- **Fix:** Component inventory. Phase 1 must ensure all user-accessible services in a namespace use the same gateway.

---

## User Impact (USER) — Verdict: REVISE

### USER-001 — Backward compatibility promise lacks implementation detail
- **Severity:** Critical | **Confidence:** High
- **Citation:** NFR, Backwards Compatibility
- **Evidence:** DSCI spec change (single gateway to gateways list) with no migration path, no version compatibility matrix, no upgrade validation.
- **Fix:** Define DSCI field migration. Automatic upgrade behavior. Validation tests. Rollback procedure.

### USER-002 — Three gateway selection mechanisms create usability confusion
- **Severity:** Important | **Confidence:** High
- **Citation:** Technical Approach, paragraph 2
- **Evidence:** Namespace annotation, Notebook CR field, and namespace default all proposed with no precedence order or recommendation.
- **Fix:** Choose single primary mechanism. Document precedence. Dashboard UI interaction model.

### USER-003 — Critical platform dependency creates adoption blocker
- **Severity:** Important | **Confidence:** Medium
- **Citation:** Dependencies, Risks
- **Evidence:** Users may adopt RHOAI expecting multi-gateway but their OCP version doesn't support it. No minimum version, no validation procedure, no fallback.
- **Fix:** Run spike to determine minimum OCP version. Operator-level validation with clear error messages.

### USER-004 — BYO Gateway shifts operational burden without documentation
- **Severity:** Important | **Confidence:** High
- **Citation:** Technical Approach, paragraph 1 (option b)
- **Evidence:** Users must create Gateway resources, understand GatewayClass mappings, configure listeners. No documentation on how to create compatible Gateways.
- **Fix:** User documentation with example YAML. Validation commands. Troubleshooting guide.

### USER-005 — Phased delivery creates partial feature with unclear limitations
- **Severity:** Minor | **Confidence:** High
- **Citation:** Technical Approach, paragraph 3
- **Evidence:** Phase 1 notebooks only, model serving deferred. Users may expect uniform gateway support. Incomplete network isolation in Phase 1.
- **Fix:** Explicit Phase 1 limitations in docs. Workaround guidance for inference endpoint isolation.

### USER-006 — Dual-mode routing during transition with no migration timeline
- **Severity:** Important | **Confidence:** Medium
- **Citation:** Risks section
- **Evidence:** Legacy path-based and new multi-gateway routing coexist with no deprecation timeline, no migration checklist.
- **Fix:** Define deprecation timeline. Migration checklist. Operator health checks for mixed-mode.

---

## Scope & Completeness (SCOP) — Verdict: REJECT

### SCOP-001 — Acceptance criteria are non-specific and untestable
- **Severity:** Important | **Confidence:** High
- **Citation:** Acceptance Criteria
- **Evidence:** AC states only "One Gateway API for each IngressController would be preferable." No testable pass/fail conditions.
- **Fix:** Add refined ACs with Given/When/Then format mapping to test cases.

### SCOP-002 — Prerequisites are blockers, not scoped into phased delivery
- **Severity:** Critical | **Confidence:** High
- **Citation:** Open Questions, Dependencies
- **Evidence:** OCP multi-GatewayClass and OSSM multi-Gateway support are assumed true but unvalidated. Should be Phase 0 spike, not assumptions.
- **Fix:** Decompose into Phase 0 (spike, S effort), Phase 1 (notebooks), Phase 2 (model serving).

### SCOP-003 — Component phasing is ambiguous
- **Severity:** Important | **Confidence:** Medium
- **Citation:** Affected Components, Scope Boundary
- **Evidence:** DSCI, OSSM changes not assigned to phases. Dashboard not phase-specific. Other components (TrustyAI, pipelines) unaddressed.
- **Fix:** Phase Breakdown table mapping each component to a phase. Explicit handling of unscoped components.

### SCOP-004 — Backwards compatibility strategy underspecified
- **Severity:** Minor | **Confidence:** Medium
- **Citation:** Technical Approach, NFR
- **Evidence:** Requirement stated but no DSCI migration, no hybrid deployment strategy, no upgrade test scenarios.
- **Fix:** Add "Backwards Compatibility & Migration" subsection with specific scenarios.

### SCOP-005 — Gateway selection mechanism unresolved blocks implementation
- **Severity:** Important | **Confidence:** High
- **Citation:** Technical Approach, Open Questions
- **Evidence:** Three options presented, no decision made. Strategy marked "Refined" but cannot be implemented without this decision.
- **Fix:** Make decision (recommend per-namespace for Phase 1). Or reclassify as "Draft" until resolved.

---

## Cross-Specialist Agreements

All 5 specialists independently identified:

1. **OCP foundational dependency unvalidated** — must be resolved via technical spike before any design work
2. **Gateway selection mechanism undecided** — blocks implementation, RBAC design, and UX planning
3. **Effort underestimated** — "L" is not credible for 5 components across 4 teams
4. **Backwards compatibility undefined** — DSCI migration, dual-mode routing, upgrade testing all missing
5. **Authentication/authorization model absent** — no RBAC, no admission control, no gateway access enforcement

## Cross-Specialist Disagreements

- **Overall verdict severity:** SCOP recommends REJECT (unimplementable without decisions). FEAS, ARCH, SEC, USER recommend REVISE. The REJECT position is strongest: without resolving OCP validation, gateway selection mechanism, and RBAC model, revisions are premature.
- **SEC severity vs others:** SEC found 3 Critical findings (cross-gateway isolation, DSCI auth model, KNative privilege escalation) while other specialists rated similar concerns as Important. SEC's Critical ratings are warranted given the security outcomes (unauthenticated access, privilege escalation).

## Remediation Roadmap

**Priority 1 (before strategy approval):**
1. Validate OCP multi-GatewayClass support via spike (FEAS-001, SCOP-002)
2. Decide gateway selection mechanism (FEAS-004, SCOP-005, USER-002)
3. Define RBAC and admission control model (SEC-001, SEC-002, SEC-007)

**Priority 2 (before implementation):**
4. Confirm OSSM multi-Gateway support (FEAS-003, ARCH-004)
5. Resolve KNative integration approach for Phase 2 (ARCH-003, SEC-003)
6. Define DSCI migration path (ARCH-001, USER-001)
7. Add refined acceptance criteria (SCOP-001)

**Priority 3 (during implementation):**
8. Component audit for routing dependencies (FEAS-005, SEC-012)
9. Audit logging and monitoring (SEC-008)
10. User documentation for BYO Gateway (USER-004)

---

*Review generated by adversarial-review v1.0.0 (strat profile, 5 specialists, iteration 1)*
*Date: 2026-04-08*
