# Project Principles Protocol

## Purpose

Defines the YAML format for `--principles <path>` and how principles are injected into refine agents and review specialists as hard constraints.

## YAML Format

The principles file is a YAML document with a `principles` list and an optional `upstream_mapping` section:

```yaml
# .strat-principles.yml
principles:
  - id: PROXY-001
    statement: "Proxy sidecars must not perform business logic. They handle routing, auth, and observability only."
    scope: [evalhub, model-registry]
  - id: UPSTREAM-001
    statement: "All strategies must consider divergence between upstream OSS and Red Hat product variants for dependencies."
    scope: all

upstream_mapping:
  - component: mlflow
    upstream: mlflow/mlflow
    product: red-hat-data-services/mlflow
    known_divergences:
      - area: artifact_endpoints
        description: "Red Hat MLflow uses different artifact storage URLs than upstream"
      - area: auth
        description: "Red Hat MLflow adds OIDC auth layer not present upstream"
```

### Fields

#### `principles[]`

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (e.g., `PROXY-001`). Used in findings to reference the violated principle. |
| `statement` | Yes | The principle as a declarative assertion. Must be falsifiable: agents can determine whether a strategy violates it. |
| `scope` | No | Which components this principle applies to. Value: `all` (default) or a list of component names. |

#### `upstream_mapping[]`

| Field | Required | Description |
|-------|----------|-------------|
| `component` | Yes | Component name as used in the strategy / Jira ticket. |
| `upstream` | Yes | Upstream OSS repo (org/repo format). |
| `product` | Yes | Product variant repo (org/repo format). |
| `known_divergences[]` | No | List of known areas where upstream and product differ. |
| `known_divergences[].area` | Yes | Short label for the divergence area. |
| `known_divergences[].description` | Yes | Human-readable description of the divergence. |

## Validation

When `--principles <path>` is specified, the orchestrator validates before proceeding:

1. File exists and is readable
2. YAML parses without errors
3. Every principle has `id` and `statement` fields
4. All `id` values are unique
5. `scope` is either `all` or a non-empty list of strings

6. If more than 20 principles are defined, emit a warning: "Large principle set (N principles) will consume significant token budget. Consider consolidating related principles." This is a warning, not a hard limit.

If validation fails, abort with a descriptive error message.

## Injection into Agents

### Refine Agents

Principles are appended to each refine agent's prompt as a dedicated section:

```
## Project Principles (Non-Negotiable)

The following principles are hard constraints for this project. Your refined strategy
MUST NOT violate any of them. If the current draft violates a principle, fix the
violation in your refinement. If a principle constrains a design choice, note the
constraint explicitly.

- [PROXY-001] Proxy sidecars must not perform business logic. They handle routing, auth, and observability only. (scope: evalhub, model-registry)
- [UPSTREAM-001] All strategies must consider divergence between upstream OSS and Red Hat product variants for dependencies. (scope: all)
```

When `upstream_mapping` is present, append it to the Product Architect and Security Engineer refine agents:

```
## Upstream vs Product Divergence

For each component below, the strategy must explicitly address differences between
the upstream OSS version and the Red Hat product variant.

- **mlflow**: upstream=mlflow/mlflow, product=red-hat-data-services/mlflow
  - artifact_endpoints: Red Hat MLflow uses different artifact storage URLs than upstream
  - auth: Red Hat MLflow adds OIDC auth layer not present upstream
```

### Mediator

When `--principles` is active, principles are appended to the mediator's prompt as a tie-breaking criterion:

```
## Project Principles (Tie-Breaking Criterion)

When selecting between section versions of equal quality, prefer the version that
better complies with these project principles. If a version violates a principle,
do not select it unless all versions violate the same principle.

- [PROXY-001] Proxy sidecars must not perform business logic. (scope: evalhub, model-registry)
- [UPSTREAM-001] All strategies must consider upstream-vs-product divergence. (scope: all)
```

### Review Specialists

Principles are appended to each review specialist's prompt during Phase 1 (self-refinement):

```
## Project Principles (Hard Constraints)

The strategy under review must comply with all project principles below. If you
identify a violation, flag it as a finding with severity Critical and reference
the principle ID.

- [PROXY-001] Proxy sidecars must not perform business logic. (scope: evalhub, model-registry)
- [UPSTREAM-001] All strategies must consider upstream-vs-product divergence. (scope: all)
```

### Scope Filtering

When a principle has `scope: [componentA, componentB]`, it is only injected into agent prompts when the strategy mentions at least one of those components. The orchestrator checks component names against the strategy draft content (case-insensitive substring match). Principles with `scope: all` are always injected.

## Finding Format for Violations

When a specialist identifies a principle violation, the finding must include:

- **Title:** `Principle violation: [PRINCIPLE-ID]`
- **Severity:** Critical (minimum; orchestrator enforces this floor)
- **Evidence:** Quote the specific strategy text that violates the principle
- **Recommended fix:** How to modify the strategy to comply

The orchestrator validates that principle violations are flagged at Critical severity. If a specialist flags a principle violation at a lower severity, the orchestrator escalates it to Critical and logs a `PRINCIPLE_SEVERITY_ESCALATION` event to the guardrail trip log.
