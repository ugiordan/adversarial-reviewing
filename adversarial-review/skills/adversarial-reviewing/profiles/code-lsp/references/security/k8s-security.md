---
name: k8s-security
specialist: security
version: "1.0.0"
last_updated: "2026-03-26"
source_url: "https://raw.githubusercontent.com/ugiordan/adversarial-reviewing/main/adversarial-review/skills/adversarial-reviewing/references/security/k8s-security.md"
description: "Kubernetes and operator security patterns with false positive checklists"
enabled: true
---

# Kubernetes & Operator Security — Verification Patterns

## Container Security Contexts

### Required Fields
- Is `runAsNonRoot: true` set?
- Is `readOnlyRootFilesystem: true` set?
- Are capabilities dropped (`drop: ["ALL"]`)?
- Is privilege escalation disabled (`allowPrivilegeEscalation: false`)?

**False positive checklist:**
- Before flagging missing securityContext: Is this an init container that inherits from the pod-level securityContext?
- Before flagging readOnlyRootFilesystem: Does the container actually need to write to the filesystem? Check what processes run and where they write.
- Before flagging capabilities: Are specific capabilities added back for a documented reason (e.g., `NET_BIND_SERVICE` for port < 1024)?

## EmptyDir and Volume Security

### Verification Questions
- What process writes to this mount path? Cite file:line evidence.
- What is the estimated write volume for the mounted path?
- Is the volume actually used for data, or is it a mount point parent for a Secret/ConfigMap volume?
- Is the sizeLimit set appropriately for the actual write volume?

**False positive checklist — emptyDir size:**
1. What process writes to this mount path? Cite file:line.
2. What is the estimated write volume?
3. Is the volume actually used for data or just as a mount point parent?
4. If no process writes to the path, the sizeLimit is a safety bound, not a capacity requirement.

**Common false positive:** Flagging emptyDir sizeLimit as "too small" when the volume is only used as a parent mount point for a Secret volume and no process writes data to it.

## RBAC Escalation Patterns

### Verification Questions
- Are wildcard permissions (`*`) used in RBAC rules? Which resources do they cover?
- Is the `escalate` verb granted on any Role/ClusterRole?
- Can the service account create or modify Roles/ClusterRoles?
- Is the service account token auto-mounted when not needed?

**False positive checklist:**
- Before flagging wildcard RBAC: Is this a cluster-admin role that is intentionally broad? Is it bound to a specific namespace?
- Before flagging service account token: Is the pod actually making API calls? Check for client-go or kubernetes SDK usage.

## Init Container Patterns

### Verification Questions
- Does the init container use the same image as the main container (reduces supply chain risk)?
- Does the init container have its own securityContext, or does it inherit from pod-level?
- Is the init container performing privilege-requiring setup that the main container cannot do?

## Network Policy

### Verification Questions
- Is a default-deny NetworkPolicy applied to the namespace?
- Are ingress and egress rules scoped to specific pods/namespaces?
- Is DNS egress allowed (required for most applications)?

## CRD Validation

### Verification Questions
- Are CRD schemas validated with OpenAPI v3 validation?
- Are webhook validations in place for complex business rules?
- Is the CRD conversion strategy defined for multi-version CRDs?
