# Constraint Packs

Constraint packs are organizational bundles containing enforced rules and reference material. Unlike `--context` (informational knowledge), constraints set **severity floors**: findings that match a constraint violation are automatically flagged at the constraint's specified severity or higher.

## Usage

```bash
# Strategy review with RHOAI constraints
adversarial-review --profile strat --constraints packs/rhoai/ strategy.md

# Code review with RHOAI constraints
adversarial-review --constraints packs/rhoai/ src/

# Combine with context for maximum coverage
adversarial-review --constraints packs/rhoai/ --context architecture=./docs src/
```

## How constraints work

When `--constraints` is specified, the tool:

1. Loads the constraint pack (YAML + reference `.md` files)
2. Filters constraints by the active profile (code, strat, or both)
3. Populates the cache with filtered constraints and reference modules
4. Adds a `## Constraints` section to the agent navigation, listing every active constraint with its severity floor
5. Agents see clear instructions: "Any finding that matches a constraint violation MUST use the constraint's severity as a FLOOR (you can escalate above but not below)"

### Severity floor model

Constraint severity is a **floor**, not a ceiling. Agents can escalate above the constraint's severity if evidence warrants it (e.g., a "High" constraint can produce a "Critical" finding), but they cannot downgrade below the floor.

### Profile filtering

Each constraint has a `profile` field: `code`, `strat`, or `both`. When loading a pack, constraints are filtered by the active review profile. A constraint with `profile: strat` is ignored during code reviews, and vice versa. Use `profile: both` for constraints that apply universally.

## Pack structure

Each pack is a directory containing:

```
packs/<org-name>/
  constraints.yaml       # Required: constraint definitions with severity enforcement
  *.md                   # Optional: reference modules providing detailed context
  README.md              # Optional: pack documentation (not loaded into cache)
```

## Creating your own pack

### 1. Create the directory

```bash
mkdir -p packs/my-org/
```

### 2. Write constraints.yaml

```yaml
name: "My Organization Constraints"
version: "1.0"
description: "Brief description of what these constraints cover"

constraints:
  - id: ORG-001
    title: "Short title"
    category: security          # Category: cryptography, authentication, networking, etc.
    severity: high              # Severity floor: critical, high, important, minor
    profile: both               # Which profiles: code, strat, both
    description: >
      Detailed description of the requirement.
    detection_guidance: >
      What to look for in code or strategy documents.
    remediation: >
      Recommended fix approach.
```

Required fields per constraint: `id`, `title`, `severity`, `profile`.

Optional but recommended: `category`, `description`, `detection_guidance`, `remediation`.

### 3. Add reference modules (optional)

Add `.md` files to the pack directory for detailed context. These are loaded alongside the constraints and appear in agent navigation as "Constraint Reference Modules." Reference modules provide the depth that short YAML descriptions cannot.

### 4. Validate

```bash
# Test with strat profile (shows filtering)
CONSTRAINTS_SOURCE=packs/my-org/ CACHE_DIR=/tmp/test REVIEW_PROFILE=strat \
  python3 scripts/manage_cache.py populate-constraints

# Test with code profile
CONSTRAINTS_SOURCE=packs/my-org/ CACHE_DIR=/tmp/test REVIEW_PROFILE=code \
  python3 scripts/manage_cache.py populate-constraints
```

## Constraints vs Context

| | `--constraints` | `--context` |
|---|---|---|
| **Purpose** | Policy enforcement | Knowledge injection |
| **Severity** | Sets a floor (cannot be downgraded) | Informational only |
| **Schema** | Structured YAML with validation | Free-form markdown |
| **Agent behavior** | MUST check and cite violations | MAY reference for analysis |
| **Use case** | Org security policies, compliance rules | Architecture docs, threat models |

Both flags are composable: use `--constraints` for hard rules and `--context` for supporting knowledge.

## Included packs

### RHOAI (Red Hat OpenShift AI)

10 constraints covering FIPS compliance, auth patterns, RBAC scope, secrets management, image provenance, and more. 3 reference modules with detailed platform context.

```bash
adversarial-review --profile strat --constraints packs/rhoai/ strategy.md
```

| ID | Title | Severity | Profile |
|----|-------|----------|---------|
| RHOAI-FIPS | FIPS 140-3 compliance required | High | Both |
| RHOAI-PQC | Post-quantum/FIPS transition awareness | Minor | Strat |
| RHOAI-TLS | TLS profile compliance | High | Both |
| RHOAI-GATEWAY | Use OpenShift Gateway API | Important | Strat |
| RHOAI-MESH | Do not require Istio unless necessary | Important | Strat |
| RHOAI-IMAGES | Image provenance from trusted registries | High | Both |
| RHOAI-UPSTREAM | Upstream-first contribution policy | Important | Strat |
| RHOAI-AUTH | Use approved auth patterns | High | Both |
| RHOAI-SECRETS | Approved secrets management patterns | High | Both |
| RHOAI-RBAC | ServiceAccount RBAC namespace-scoped | High | Both |

## Trust model

Packs are user-provided reference material. The tool does not cryptographically verify pack contents. For production reviews, version-control your packs alongside your code and review changes to constraint files with the same rigor as code changes.
