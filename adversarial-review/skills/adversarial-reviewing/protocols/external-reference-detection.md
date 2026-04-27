# External Reference Detection

Scans cached code for references to resources defined outside the reviewed scope. Runs after cache initialization (Step 3) and before agent dispatch (Step 4).

## Purpose

Agents cannot reason about resources they haven't read. When reviewed code references external definitions (SCCs, CRDs, controllers in other repos, kustomize overlays), agents either skip those references or infer behavior from context clues. Inferred behavior is a common source of false positives and incorrect severity classifications.

This step detects external references early so the orchestrator can fetch the actual definitions before agents start.

## Procedure

### 1. Run detection

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/detect-external-refs.py ${CACHE_DIR}/code/ --source-root <SOURCE_ROOT>
```

The script outputs JSON:

```json
{
  "references": [
    {
      "type": "go_import",
      "reference": "github.com/opendatahub-io/kserve",
      "file": "controllers/modelcache_controller.go",
      "line": 12,
      "fetchable": true,
      "fetch_source": "https://github.com/opendatahub-io/kserve"
    },
    {
      "type": "file_path",
      "reference": "overlays/odh-modelcache/localmodel-scc.yaml",
      "file": "controllers/rbac.go",
      "line": 45,
      "fetchable": false,
      "fetch_source": null
    }
  ],
  "summary": {
    "total": 2,
    "fetchable": 1,
    "unfetchable": 1
  }
}
```

### 2. Filter already-covered references

If `--context` was already specified, check whether any detected references fall within an already-fetched context directory. Remove those from the list.

### 3. Present to user

If references remain after filtering:

```
External references detected in reviewed code:

  Fetchable (can auto-include as context):
    [1] github.com/opendatahub-io/kserve (Go import in controllers/modelcache_controller.go:12)

  Not fetchable (agents will be warned about scope gaps):
    [2] overlays/odh-modelcache/localmodel-scc.yaml (file path in controllers/rbac.go:45)

Fetch [1] as review context? (yes/no/skip all)
```

### 4. Auto-fetch approved references

For each approved fetchable reference, invoke the existing context mechanism:

```bash
CONTEXT_LABEL="external-<sanitized_name>" CONTEXT_SOURCE="<fetch_source>" \
  ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-context
```

Then regenerate navigation:

```bash
${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh generate-navigation 1 1
```

### 5. Record unfetchable references as scope warnings

Write unfetchable references to `${CACHE_DIR}/scope-warnings.md`:

```markdown
## Scope Warnings

The following external resources are referenced in the reviewed code but could not be fetched.
Findings about these resources should be marked Confidence: Low.

- `overlays/odh-modelcache/localmodel-scc.yaml` (referenced in controllers/rbac.go:45)
```

Include `scope-warnings.md` in the navigation file so agents see it.

## Detection Patterns

The detection script looks for these patterns:

### Code profile (Go/Python/YAML)

| Pattern | Type | Fetchable? |
|---------|------|-----------|
| `import "github.com/<org>/<repo>/..."` | `go_import` | Yes: `https://github.com/<org>/<repo>` |
| `from <package> import` where package is external | `python_import` | Maybe: PyPI package, not a repo |
| File paths in comments (`// See <path>`, `# <path>`) pointing outside source root | `file_path` | If path resolves relative to parent directories |
| RBAC `resourceNames: [<name>]` | `rbac_resource` | No: need cluster context |
| Kustomize `resources:` or `bases:` with external paths | `kustomize_ref` | If path resolves |
| CRD GVK references (`apiVersion: <group>/<version>`) for non-standard groups | `crd_ref` | No: need cluster context |

### Strat/RFE profile

For document review, detection is limited to explicit references:
- URLs pointing to external repos or documentation
- Component names referencing known platform services
- Architecture context references

### Deployment dependency signals

Beyond code-level references, scan for signals that the component is managed by an external controller whose policies affect the component's security posture:

| Signal | Implication |
|--------|-------------|
| `app.kubernetes.io/managed-by` label in manifests | Component is operator-managed. The operator likely deploys namespace-level resources (NetworkPolicy, RBAC) separately. |
| Kustomize overlays referencing parent directories (`../../`) | Deployment composition happens outside this repo. |
| CRD references to `*Operator`, `*Controller` kinds | An operator manages this component's lifecycle. |
| `podSelector: {}` in any NetworkPolicy | Policy applies to ALL pods in the namespace, not just this component. Other such policies may exist outside the review scope. |
| Namespace-scoped resources (NetworkPolicy, ResourceQuota, LimitRange) | These may have counterparts deployed by operators or platform controllers that combine additively. |

When deployment dependency signals are detected, include an advisory in the scope confirmation:

```
Advisory: This component appears to be deployed by [operator/controller].
Namespace-level policies deployed by the operator may affect security findings
(NetworkPolicies are additive across a namespace). Consider adding:
  --context deployment=<operator-repo>
```

This is advisory only. It does not block the review.

## Skip conditions

Skip this step entirely when:
- `--reuse-cache` is active (cache is pre-populated, detection already ran on original cache)
- No code files exist in cache (empty scope)
- All detected references are already covered by `--context` labels

## Error handling

Detection script failures are non-fatal. If the script errors, log the error, emit a warning, and proceed to Step 4. Missing context is handled by the "Unverified External References" instructions in each agent's prompt.
