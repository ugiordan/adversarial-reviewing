---
strat_id: STRAT-001
title: RHOAI support for Ingress / Gateway API sharding
source_rfe: RHAIRFE-953
priority: Major
status: Refined
jira_key: null
---
## Business Need (from RFE)

#### **Problem Statement**

* RHOCP customers typically rely on Ingress sharding to expose a specific route / gateway to different network zones (i.e. where "zone" could either be "a specific network segment", as well as a designated "test/dev/production development stage").
* While this was already an issue with RHOAI 2.x - i.e. RHOAIENG-35058 - the Gateway API implementation in RHOAI 3.x has unfortunately been a step back, as it now moved to a path based routing architecture and using single domain for all notebooks.

#### **Business Alignment**

* RHOAI customers often need to expose notebooks / workbenches on specific network segments through Ingress / Gateway API sharding.

#### **Proposed Solution/Rationale**

* For this specific customer scenario, one Gateway for each IngressController shard be the preferred approach, as opposed to using one single Gateway for the default IngressController

#### **Acceptance Criteria**

* One Gateway API for each IngressController would be preferable

## Strategy

**Effort**: L
**Components**: odh-operator (DSCInitialization, DSCI networking config), odh-notebook-controller, kserve (KNative Gateway bindings), istio/ossm (service mesh gateway configuration), odh-dashboard
**Impacted Teams**: Platform/Operator, Notebooks, Model Serving, Dashboard

### Technical Approach

RHOAI 3.x consolidated routing behind a single Gateway resource bound to the default IngressController, using path-based routing under one domain for all notebooks and inference endpoints. This architecture fundamentally conflicts with Ingress sharding, where customers partition traffic across multiple IngressControllers mapped to distinct network zones (e.g., internal vs. external, dev vs. prod).

The core change is to move from a single, operator-managed Gateway to a model where multiple Gateway resources can coexist, each bound to a specific IngressController (via the `gatewayClassName` or listener configuration targeting a specific GatewayClass provisioned by each shard's IngressController). The approach breaks down into three layers:

**1. Operator-level Gateway lifecycle management.** Currently, `DSCInitialization` creates a single Gateway as part of the networking/servicemesh setup. This needs to be extended so the operator can either (a) create multiple Gateway resources based on a new sharding configuration in the DSCI spec, or (b) allow users to bring their own pre-created Gateway resources and reference them. Option (b) is more flexible and lower risk for the operator team, as it avoids the operator needing to understand the full IngressController topology. The DSCI spec would gain a `gateways` list (replacing or extending the current single gateway reference), where each entry specifies a Gateway name/namespace and an optional label selector for which workloads route through it.

**2. Notebook and workbench routing.** The `odh-notebook-controller` currently creates HTTPRoute resources pointing at the single platform Gateway. With multi-gateway support, the controller needs to determine which Gateway a given notebook should use. This could be driven by namespace labels/annotations (e.g., `rhoai.opendatahub.io/gateway: zone-a-gateway`), by a field on the Notebook CR, or by a namespace-level default. The controller would then set the correct `parentRef` on the HTTPRoute. Each Gateway would have its own domain/listener, so the path-based single-domain constraint is resolved: notebooks on different gateways naturally get different hostnames.

**3. Model serving routing (KServe).** KServe InferenceService resources create their own routing through KNative or raw Kubernetes mode. In KNative mode, the `knative-local-gateway` and `knative-ingress-gateway` references in the KNative Serving ConfigMap would need to support per-namespace or per-InferenceService gateway overrides. In raw deployment mode, the KServe controller creates HTTPRoutes directly, and the same parentRef logic as notebooks applies.

The recommended phased approach: Phase 1 delivers BYO Gateway support for notebooks (the primary customer pain point from the RFE). Phase 2 extends to KServe/model serving. This limits initial blast radius while solving the stated customer need.

### Affected Components

| Component | Change | Owner Team |
|-----------|--------|------------|
| odh-operator (DSCI) | Extend networking spec to support multiple gateway references. Validate gateway existence. Stop hard-coding single gateway. | Platform/Operator |
| odh-notebook-controller | Support multi-gateway parentRef selection on HTTPRoute creation. Add namespace/notebook-level gateway annotation. | Notebooks |
| kserve | Support gateway override per InferenceService or namespace for HTTPRoute parentRef (Phase 2). | Model Serving |
| odh-dashboard | Surface gateway selection in workbench creation UI if multiple gateways are configured. | Dashboard |
| istio/ossm configuration | Ensure mesh configuration allows multiple Gateway resources from different GatewayClasses. May need adjustments to SMCP or Istio operator config managed by RHOAI. | Platform/Operator |

### Dependencies

- **Gateway API v1 support in OpenShift**: RHOAI 3.x already uses Gateway API, but multi-GatewayClass support depends on the OpenShift IngressController operator correctly provisioning separate GatewayClass resources per shard. This is an OCP platform capability, not RHOAI-controlled.
- **OSSM/Istio Gateway API integration**: The service mesh component must support multiple Gateway resources across different GatewayClasses. Istio's Gateway API support has matured, but the OSSM (OpenShift Service Mesh) packaging may impose constraints.
- **KNative Gateway API support (Phase 2)**: KNative Serving's Gateway API integration needs to support configurable gateway references. Upstream KNative has been evolving this, status of the specific version bundled in RHOAI needs verification.

### Non-Functional Requirements

- **Performance**: No degradation expected. Multiple gateways distribute load rather than concentrating it.
- **Security**: Gateway sharding is fundamentally a security/network isolation feature. The implementation must ensure that a workload assigned to Gateway A cannot be accessed through Gateway B. HTTPRoute parentRef binding provides this guarantee at the Gateway API level, but it needs to be validated end-to-end.
- **Backwards Compatibility**: Existing single-gateway deployments must continue to work without configuration changes. The multi-gateway support should be opt-in. Default behavior (single gateway, path-based routing) must be preserved for upgrades.

### Risks

- **OCP IngressController sharding + Gateway API interop is undertested**: Gateway API sharding via multiple GatewayClasses provisioned by different IngressController shards is relatively new in OpenShift. There may be edge cases in how the OCP ingress operator provisions and manages these. Mitigation: early spike/PoC to validate the OCP-level plumbing before building RHOAI logic on top of it.
- **OSSM constraints on multi-Gateway**: OSSM may impose a single-gateway-per-mesh assumption in certain configurations. Mitigation: validate with OSSM team early. If OSSM is a blocker, the BYO Gateway approach (gateways outside the mesh, with mesh integration via mTLS) may be needed.
- **Scope creep into full multi-tenancy**: Gateway sharding touches network isolation, which is adjacent to multi-tenancy concerns. There is risk that stakeholders expand scope to include tenant isolation, RBAC per gateway, and quota management. Mitigation: define clear scope boundary (see below).
- **Path-based routing removal complexity**: If some workloads share a gateway and others don't, the path-based routing logic in the notebook controller may need to support both modes simultaneously during the transition. This increases testing surface.

### Open Questions

- **Does OCP 4.x currently support provisioning separate GatewayClass resources per IngressController shard?** This is a prerequisite. If not, the strategy needs to define a workaround or depend on a specific OCP version.
- **Should gateway assignment be per-namespace or per-workload?** Per-namespace is simpler (one annotation on the namespace), per-workload is more flexible but adds complexity to the notebook controller and dashboard.
- **What is the OSSM/Istio version compatibility matrix for multi-Gateway support?** Need to verify which OSSM versions support this cleanly.
- **Is the single-domain path-based routing in RHOAI 3.x a hard architectural constraint, or was it a simplification?** Understanding why the 3.x architecture chose single-domain routing will inform how invasive the change is to undo.
- **Are there other RHOAI components (e.g., TrustyAI, data science pipelines) that also create routes/HTTPRoutes and would need gateway-awareness?** Scope could expand if other components have the same single-gateway assumption.

### Scope Boundary

**Delivers**: The ability to configure multiple Gateway resources in RHOAI, each bound to a different IngressController shard, so that notebooks/workbenches can be exposed on specific network zones. Phase 1 targets notebook routing. Phase 2 extends to model serving.

**Does NOT deliver**: Full multi-tenancy, per-user network policies, or automated IngressController shard provisioning. The customer is expected to have their OCP Ingress sharding already configured.

**Assumptions**: OCP IngressController sharding with Gateway API is functional in the target OCP version. Customers have pre-existing IngressController shards they want RHOAI to integrate with.
