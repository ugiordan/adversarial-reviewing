---
strat_id: STRAT-001
recommendation: reject
reviewers:
  feasibility: reject
  testability: revise
  scope: reject
  architecture: reject
  security: revise
---
## Feasibility

**Feasibility**: Infeasible without significant architecture changes.
**Effort estimate**: Dramatically underestimated (claimed L, actual XXL or split into 3+ L epics).
**RFE alignment**: Partial (notebooks addressed, model serving deferred without validation).

Key concerns:
1. **Critical architectural conflict: Gateway is singleton by design**: GatewayConfig CR is singleton (`default-gateway`), Gateway Controller creates one Gateway (`data-science-gateway`). GatewayClass `data-science-gateway-class` uses `openshift.io/gateway-controller/v1`, a cluster-wide controller, not per-IngressController.
2. **OCP does not support per-shard GatewayClasses**: No evidence in architecture docs of GatewayClass-per-shard capability. Listed as "Open Question" but is the foundational dependency.
3. **Authentication coupling blocks multi-gateway**: kube-auth-proxy is singleton Deployment. EnvoyFilter `data-science-authn-filter` scoped to `data-science-gateway`. BYO Gateways would bypass platform authentication.
4. **HTTPRoute cross-namespace architecture prevents multi-gateway**: Notebook controller creates HTTPRoutes in central namespace. Multi-Gateway requires cross-namespace parent references (HTTPRoute → Gateway), which may require ReferenceGrant changes.
5. **Model serving uses Istio VirtualService, not Gateway API**: KServe uses VirtualService by default. Gateway API disabled. Strategy assumes HTTPRoute (incorrect).
6. **Single-domain is not the problem**: Gateway already has two listeners with different hostnames. Path-based routing is a choice, not a constraint. Notebook controller already reads `NOTEBOOK_GATEWAY_NAME`/`NOTEBOOK_GATEWAY_NAMESPACE` env vars.
7. **Effort 4-5x underestimated**: Missing OCP validation spike, DSCI schema migration (breaking API version bump), Gateway Controller redesign, kube-auth-proxy multi-instance architecture, KServe ingress mode change, Dashboard UI, combinatorial testing.
8. **Risks are blockers**: OCP GatewayClass per-shard is a missing capability, not a risk. OSSM EnvoyFilter is singleton-scoped.
9. **Missing 10+ components from scope**: kube-auth-proxy, EnvoyFilter, DestinationRule, odh-model-controller, TrustyAI, MLflow, Model Registry, KubeRay, guardrails, batch-gateway all create HTTPRoutes.

**Recommendation**: reject

## Testability

**Overall assessment**: Partially testable with critical gaps in acceptance criteria, success metrics, and edge case coverage.

Key concerns:
1. **Vague acceptance criteria**: "One Gateway API for each IngressController would be preferable" is not testable. Needs Given/When/Then: "Given namespace with annotation `gateway: zone-a`, when notebook is created, then HTTPRoute parentRef must reference zone-a Gateway and workload must be accessible only via zone-a listener."
2. **12+ missing edge cases**: Gateway deletion while workloads running, IngressController shard failure, concurrent workload creation, namespace migration between Gateways, RBAC edge cases, certificate rotation, upgrade backwards compatibility, scale testing (10+ Gateways), mixed-mode operation, HTTPRoute naming collisions, NetworkPolicy interactions, auth proxy scalability, KNative reconciliation.
3. **6 untestable criteria**: RFE acceptance criteria lacks observable conditions. "No performance degradation" lacks baselines. "Network zone isolation" lacks verification method. "Backwards compatibility" lacks success criteria. Gateway selection mechanism unspecified (3 options, no commitment). BYO Gateway auth model undefined.
4. **Requires significant test infrastructure**: OCP cluster with IngressController sharding, multi-GatewayClass setup (unvalidated prerequisite), OSSM multi-Gateway config, cross-zone network simulation. Combinatorial matrix: 24+ scenarios minimum.
5. **No test strategy**: No unit/integration/E2E breakdown. No CI vs manual QE split. No performance test plan. No upgrade test strategy. No failure injection testing.

**Recommendation**: revise

## Scope

**Scope assessment**: Too large. Split into 4 epics recommended.
**Effort vs scope**: Severely underestimated (L claimed, actual XL-XXL).
**RFE coverage**: Partial with silent scope expansion.

Key concerns:
1. **Phase boundary arbitrary and unvalidated**: Defers model serving without customer confirmation notebooks-only solves their problem.
2. **Silent scope expansion beyond RFE**: Adds Dashboard UI, DSCI spec evolution, BYO Gateway model (RFE asks for "one Gateway per IngressController," not user-provided gateways).
3. **Missing component scope**: 8+ components create HTTPRoutes, only 2 scoped. kube-auth-proxy, EnvoyFilter, DestinationRule, ReferenceGrant, NetworkPolicy not in affected components.
4. **Authentication architecture is out of scope but blocking**: Multi-gateway requires duplicating auth infrastructure per gateway or documenting BYO auth. Neither scoped.
5. **Backwards compatibility unbounded**: "Without configuration changes" can expand indefinitely. No migration path, dual-mode support, or upgrade validation scoped.

**Split recommendation**:
- **STRAT-001A**: Gateway API sharding infrastructure (M-L). OCP validation spike + DSCI multi-gateway reference support (BYO model).
- **STRAT-001B**: Notebook multi-gateway routing (M, depends on 001A). Notebook controller parentRef selection via namespace annotation.
- **STRAT-001C**: Model serving multi-gateway routing (M-L, depends on 001A). KServe InferenceService multi-gateway support.
- **STRAT-001D**: Multi-gateway authentication (L-XL, depends on 001B or 001C). Replicate kube-auth-proxy + EnvoyFilter per gateway OR document BYO auth.

**Recommendation**: reject

## Architecture

**Architecture assessment**: Conflicts with platform. Multiple foundational assumptions incorrect.

Key findings:
1. **No per-shard GatewayClass in OCP**: Architecture shows single `data-science-gateway-class` with `openshift.io/gateway-controller/v1` (PLATFORM.md:323, rhods-operator.md:136). No mechanism for per-shard GatewayClasses.
2. **Multi-domain already works**: Gateway has two listeners with different hostnames (`rh-ai.{domain}` and `data-science-gateway.{domain}`). Path-based routing is a choice, not a constraint.
3. **Gateway already configurable**: Notebook controller reads `NOTEBOOK_GATEWAY_NAME`/`NOTEBOOK_GATEWAY_NAMESPACE` env vars (kubeflow.md:117-118). KServe reads from ConfigMap (kserve.md:248). Multi-gateway partially exists.
4. **GatewayConfig is singleton by design**: `default-gateway`, single Gateway per DSCI. Extending to list requires API versioning (v1alpha1 → v1beta1), conversion webhook.
5. **HTTPRoute cross-namespace parent references**: HTTPRoutes in central namespace referencing Gateways in different IngressController-managed namespaces may require ReferenceGrant for parent (not just backend) references.
6. **EnvoyFilter singleton-scoped**: `data-science-authn-filter` targets `data-science-gateway` workload. Multi-Gateway needs per-Gateway EnvoyFilters or mesh-wide conditional routing.
7. **DestinationRule singleton**: `data-science-tls-rule` configures TLS for upstream services. Multi-Gateway requires either multiple DestinationRules or shared rule with multi-host entries.
8. **kube-auth-proxy Gateway-coupled**: Singleton Deployment created by Gateway Controller. Multi-gateway requires one per Gateway (resource overhead) or shared proxy (complex EnvoyFilter routing).
9. **10+ components create HTTPRoutes**: odh-dashboard, notebooks, mlflow, model-registry, kuberay, TrustyAI, guardrails, eval-hub, batch-gateway, llama-stack. Strategy scopes only 2.
10. **NetworkPolicy gaps**: kube-auth-proxy NetworkPolicy allows ingress from `openshift-ingress` only. Additional Gateways in different namespaces need NetworkPolicy updates.

**Prerequisite validation required**:
1. Does OCP 4.19-4.21 provision separate GatewayClass per IngressController shard?
2. Does OpenShift Gateway Controller support multiple Gateway resources bound to different shards?
3. OSSM/Istio compatibility for multi-Gateway with shared EnvoyFilter ext_authz?
4. Can HTTPRoutes in central namespace reference Gateways in different namespaces?

**Recommendation**: reject (escalate to architecture review)

## Security

### STRAT-001: RHOAI support for Ingress / Gateway API sharding
**Review depth**: Standard
**Threat surfaces**:
- New trust boundary: multiple Gateway resources with independent listeners on different network zones
- Modified data flow: HTTPRoute parentRef selection determining which network zone a workload is exposed on
- New configuration surface: DSCI gateways list and namespace/workload-level gateway annotations

#### Security Risks

1. **Unauthenticated access via BYO Gateways without ext_authz** (Severity: Critical)
   **Why this change creates this risk**: Technical Approach paragraph 1 proposes "allow users to bring their own pre-created Gateway resources." The current auth architecture relies on a singleton EnvoyFilter `data-science-authn-filter` attached to `data-science-gateway` (rhods-operator.md:297). This filter calls kube-auth-proxy at 8443/TCP via ext_authz for every request. BYO Gateways would not have this filter, meaning workloads on those gateways would bypass platform authentication entirely.
   **Component affected**: rhods-operator (Gateway Controller), kube-auth-proxy, odh-notebook-controller
   **Description**: If a user creates their own Gateway and the notebook controller allows notebooks to reference it via annotation, those notebooks would be accessible without OAuth/OIDC authentication. The strategy does not address auth provisioning for additional gateways.
   **Mitigation**: (a) Reject BYO Gateway until auth story is solved, or (b) require DSCI `gateways` list to include auth config and deploy EnvoyFilter + kube-auth-proxy per gateway, or (c) admission validation rejecting HTTPRoute creation if parent Gateway lacks required EnvoyFilter.

2. **Cross-gateway data exfiltration via annotation override** (Severity: Important)
   **Why this change creates this risk**: Technical Approach paragraph 2 proposes gateway assignment via "namespace labels/annotations" or "a field on the Notebook CR." NFR section acknowledges isolation requirement but delegates to "HTTPRoute parentRef binding, needs to be validated end-to-end." No validation logic, admission control, or RBAC on annotation setting described.
   **Component affected**: odh-notebook-controller, kserve (Phase 2)
   **Description**: A user could annotate their notebook with a gateway reference targeting an unintended network zone, bypassing network segmentation. Namespace admins could change gateway annotations to exfiltrate data through alternative network zones.
   **Mitigation**: (a) Admission webhook validating gateway references against DSCI-approved list, (b) RBAC on gateway selection (custom verb on virtual resource), (c) fail-closed default when no annotation set, (d) reconciliation logic for stale/removed gateways.

#### NFR Gaps (Low severity, informational)
- TLS certificate provisioning for additional gateways not addressed (cert-manager? user-provided?)
- NetworkPolicy implications for multi-namespace gateways not discussed (kube-auth-proxy allows ingress only from `openshift-ingress`)
- RBAC model for gateway annotation setting not addressed (who can set `rhoai.opendatahub.io/gateway`?)
- Audit logging for gateway assignment changes or cross-gateway access attempts not mentioned

#### Suggested Security Acceptance Criteria
1. Auth enforcement: every Gateway in DSCI `gateways` list MUST have EnvoyFilter with ext_authz. Unauthenticated request to notebook on non-default gateway returns 401.
2. Gateway isolation: notebook on Gateway A MUST NOT be accessible via Gateway B's hostname/listener. HTTPRoute with parentRef to Gateway A returns 404 via Gateway B.
3. Admission validation: notebook CR with invalid/unapproved gateway reference MUST be rejected.
4. RBAC enforcement: user without permission on gateway MUST NOT create notebooks using that gateway.

**Recommendation**: revise

## Agreements

All 5 reviewers agree:
- **OCP foundational dependency unvalidated and likely missing**: Must be validated via technical spike before any design work. Architecture docs show no per-shard GatewayClass mechanism.
- **Effort dramatically underestimated**: L is not credible. All reviewers estimate XL-XXL or multiple L epics.
- **Authentication coupling is a blocker**: EnvoyFilter/kube-auth-proxy are singleton-scoped to `data-science-gateway`. Multi-gateway requires auth architecture redesign. Flagged independently by architecture, security, and feasibility reviewers.
- **Phase 1 notebooks-only may not deliver RFE**: Customer need for model serving sharding not validated.
- **Missing design decisions**: Gateway selection mechanism, auth proxy architecture, routing mode, DSCI spec design all unspecified.
- **10+ components create HTTPRoutes, only 2 scoped**: Missing components will need multi-gateway awareness or explicit exclusion.
- **Single-domain is not the problem**: Gateway already supports multiple listeners/hostnames. Path-based routing is a configuration choice.

## Disagreements

- **Verdict severity**: Feasibility and architecture reviewers recommend **reject** (foundational dependency missing, infeasible without architecture changes). Scope reviewer recommends **reject** with split into 4 epics. Security and testability reviewers recommend **revise**. The reject position is strongest: if OCP doesn't support per-shard GatewayClass, revising won't help.
- **BYO Gateway risk severity**: Security reviewer upgraded BYO Gateway auth gap from Important (prior review) to **Critical** based on architecture doc cross-reference showing EnvoyFilter is singleton. Architecture reviewer frames the same issue as a structural conflict. Both framings are valid, but Critical severity is warranted given unauthenticated access is the outcome.
- **Split granularity**: Scope reviewer recommends 4 epics (infrastructure, notebooks, model serving, auth). Feasibility reviewer suggests 3+ L epics without specifying boundaries. Both agree current scope is too large for single strategy.
