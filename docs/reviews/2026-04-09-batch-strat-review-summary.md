# Batch STRAT Security Review Summary

**Date:** 2026-04-09
**Reviewer:** Adversarial Review (strat profile, SEC+TEST+FEAS specialists)
**STRATs Reviewed:** 5

## Results

| STRAT | Topic | Specialists | Findings | Verdict |
|-------|-------|------------|----------|---------|
| RHAISTRAT-1452 | Structured Output Enforcement for Auto Tool Calls | SEC, TEST, FEAS | 22 (7C, 12I, 3m) | REVISE |
| RHAISTRAT-1454 | Tool Call Test and Supported Matrix | SEC, FEAS, TEST | 17 (4C, 10I, 3m) | REVISE |
| RHAISTRAT-1456 | LlamaStack Support for OpenAI Codex Agent SDK | SEC, TEST | 12 (4C, 8I, 0m) | REJECT |
| RHAISTRAT-1446 | GPUaaS and Kueue Experience in OpenShift AI | SEC, FEAS | 11 (4C, 7I, 1m) | REVISE |
| RHAISTRAT-1444 | AMD GPU MI355X/MI350X Support | SEC, FEAS | 8 (1C, 4I, 3m) | REVISE |
| **Total** | | | **68 (20C, 41I, 10m)** | |

## Cross-STRAT Finding Patterns

### 1. No auth/authz model specified (1452, 1456, 1446)
Strategies introduce new API surfaces, session stores, or provisioning endpoints without specifying which RHOAI-approved auth pattern (kube-auth-proxy via Istio, kube-rbac-proxy sidecar, Kuadrant) gates access.

### 2. No performance baselines or latency budgets (1452, 1454, 1456)
Features that affect production inference latency provide zero measurable performance targets (p50/p95/p99, TTFT, throughput regression bounds).

### 3. No observability or audit logging (1452, 1454, 1446)
Security-relevant actions (grammar enforcement, tool call parsing, GPU provisioning) become invisible. No metrics, logging, or alerting requirements specified.

### 4. Acceptance criteria untestable (1452, 1454, 1456)
ACs use vague language ("seamlessly", "successfully", "unaffected", "without major degradation") without measurable pass/fail criteria. Non-deterministic model behavior conflated with deterministic system behavior.

### 5. No effort estimates or timeline (1452, 1454, 1446)
Strategies describe complex multi-component scope without T-shirt sizing, team capacity assessment, or milestone mapping.

### 6. Supply chain / dependency chain risks unassessed (1454, 1444, 1456)
External dependencies (model weights, ROCm stack, upstream RFCs, Codex CLI) introduced without provenance verification, version pinning, or contingency plans.

### 7. Multi-tenant isolation not addressed (1446, 1452, 1456)
Features expose cross-tenant data (GPU topology, session state, cached inference) without tenant-scoped filtering or isolation verification.

### 8. No threat model for new attack surfaces (1452, 1456, 1444)
Features introduce security-critical boundaries (grammar enforcement transition, tool execution boundary, kernel GPU drivers) without threat modeling.

## Notable Findings

### RHAISTRAT-1456 (REJECT): Session store security
The LlamaStack/Codex strategy proposes a server-side session store holding multi-turn coding context (source code, bash outputs, file contents) accessible via `session_id` alone. No authentication, no tenant scoping, no data-at-rest encryption, no session TTL. In multi-tenant RHOAI, this is a session hijacking and data exfiltration surface. Additionally, the tool definitions (bash, write_file, edit_file) have ambiguous execution boundaries that could create RCE if server-side.

### RHAISTRAT-1452: Grammar enforcement as security boundary
Token-level grammar enforcement in auto mode creates a new security-critical boundary. The "commitment point" (detecting when model starts generating a tool call) is the novel mechanism, and adversarial prompt injection targeting this boundary is an unexamined attack vector. Removing parser validation as defense-in-depth creates a single point of failure.

### RHAISTRAT-1446: Self-service GPU provisioning for non-admins
Delegating GPU pool provisioning to non-admin users without RBAC specification, admission control, or quota ceilings creates a privilege escalation surface in clusters managing $25K-$40K/GPU resources for regulated financial customers.

### RHAISTRAT-1444: Serial dependency chain
Four-deep external dependency chain (ROCm 7 -> PyTorch 2.10 -> vLLM 0.15.0 -> RHAI) with 3-day gaps between targets and zero contingency plan. Near-certain timeline slip.

## Methodology

Each STRAT was reviewed by 2-3 specialist agents from the adversarial-review strat profile:
- **SEC** (Security Analyst): 9 security dimensions, RHOAI auth pattern awareness
- **TEST** (Testability Analyst): 8 testability dimensions, AC measurability
- **FEAS** (Feasibility Analyst): effort, dependencies, timeline, codebase readiness

Agents operated independently with self-refinement. Findings required specific strategy text citations (relevance gate). No challenge round was run for this batch (time constraint).
