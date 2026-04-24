---
name: rhoai-platform-constraints
specialist: all
version: "1.0.0"
last_updated: "2026-04-04"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-review/main/adversarial-review/skills/adversarial-review/packs/rhoai/rhoai-platform-constraints.md"
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

- **Istio integration.** RHOAI integrates with OpenShift Service Mesh (Istio-based). Strategies adding new services must account for sidecar injection, mTLS, and network policies. However, RHOAI is actively reducing its Istio dependency: new hard Istio requirements need strong justification.
- **Mesh mTLS.** Inter-service communication within the mesh has mTLS for transport security. Transport-layer TLS on top of mesh mTLS is redundant and should be avoided. However, application-layer encryption of sensitive payloads (credentials, PII, keys) is still required for defense-in-depth and is NOT redundant with mTLS.

## RBAC Scope

- **Namespace-scoped by default.** ServiceAccount RBAC must use namespace-scoped Role/RoleBinding by default. ClusterRoleBindings require written justification specifying: (1) why namespace-scoped RBAC is insufficient, (2) which cluster-wide resources the SA needs, (3) mitigation for privilege escalation risk.
- **Least privilege.** Each component should have its own ServiceAccount (not the default SA). Avoid cluster-admin. Use specific verbs and resource names in Role rules.

## Secrets Management

- **Approved patterns.** Use OpenShift Secrets (with encryption-at-rest) or external secret stores (HashiCorp Vault, external-secrets-operator). CRDs should use SecretKeyRef, not inline values.
- **Banned patterns.** Credentials in environment variables, ConfigMaps, container images, or source code. Secret values in log output.

## Image Provenance

- **Trusted registries only.** Container images must come from registry.redhat.io or quay.io. Images from untrusted registries (Docker Hub, GHCR) are not permitted in production.
- **Certification.** All new container images must pass the Red Hat container certification pipeline.

## Compute and Storage

- **GPU scheduling.** GPU allocation uses Kubernetes device plugins and NVIDIA GPU Operator. Strategies must not assume direct GPU access outside the scheduling framework.
- **Storage backends.** RHOAI supports S3-compatible object storage and PVCs. Strategies should specify storage requirements and whether they work with both.

## Versioning

- **N-1 compatibility.** Upgrades must support N-1 backward compatibility. Strategies introducing API changes must specify the migration path.
- **Component matrix.** RHOAI bundles specific versions of KServe, Ray, Kubeflow Pipelines, etc. Strategies must note which component versions they depend on.
