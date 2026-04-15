---
name: rhoai-platform-constraints
specialist: all
version: "1.0.0"
last_updated: "2026-04-04"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-review/main/adversarial-review/skills/adversarial-review/profiles/strat/references/all/rhoai-platform-constraints.md"
description: "RHOAI platform constraints and assumptions for strategy feasibility review"
enabled: true
---

# RHOAI Platform Constraints

Strategies must account for these platform constraints. Proposals that assume capabilities not available in the platform are valid review findings.

## Deployment Target

- **OpenShift only** (not vanilla Kubernetes). Strategies must not assume features absent from OpenShift (e.g., certain CSI drivers, Ingress controllers other than HAProxy/OCP Router).
- **OLM-managed lifecycle.** All RHOAI components are installed and upgraded via OLM (Operator Lifecycle Manager). Strategies must account for OLM constraints: CSV-based upgrades, install plan approval, and subscription channels.
- **Disconnected/air-gapped environments.** Strategies should note whether the feature works in disconnected clusters (no internet access, mirrored registries).

## Multi-Tenancy

- **Namespace-scoped vs cluster-scoped.** RHOAI supports both. Strategies must specify the scope of any new CRDs, RBAC, or controllers. Cluster-scoped resources require stronger justification.
- **DSC/DSCI model.** The DataScienceCluster (DSC) and DSCInitialization (DSCI) CRDs are the top-level configuration. New features must integrate with this model, not create parallel configuration paths.

## Service Mesh

- **Istio integration.** RHOAI integrates with OpenShift Service Mesh (Istio-based). Strategies adding new services must account for sidecar injection, mTLS, and network policies.
- **Existing mTLS.** Inter-service communication within the mesh already has mTLS. Strategies should not propose redundant TLS termination for mesh-internal traffic.

## Compute and Storage

- **GPU scheduling.** GPU allocation uses Kubernetes device plugins and NVIDIA GPU Operator. Strategies must not assume direct GPU access outside the scheduling framework.
- **Storage backends.** RHOAI supports S3-compatible object storage and PVCs. Strategies should specify storage requirements and whether they work with both.

## Versioning

- **N-1 compatibility.** Upgrades must support N-1 backward compatibility. Strategies introducing API changes must specify the migration path.
- **Component matrix.** RHOAI bundles specific versions of KServe, Ray, Kubeflow Pipelines, etc. Strategies must note which component versions they depend on.
