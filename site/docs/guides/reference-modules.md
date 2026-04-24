# Reference Modules

Reference modules are pluggable knowledge bases that specialists cross-check their findings against during self-refinement (iteration 2+).

## Built-in modules (code profile)

| Module | Description |
|--------|-------------|
| `owasp-top10-2025` | OWASP Top 10:2025 vulnerability verification patterns |
| `agentic-ai-security` | OWASP Agentic AI risks ASI01-ASI10 |
| `asvs-5-highlights` | ASVS 5.0 key requirements by verification level |
| `k8s-security` | Kubernetes/operator security patterns with false positive checklists |

## Built-in modules (strategy profile)

| Module | Scope | Description |
|--------|-------|-------------|
| `rhoai-platform-constraints` | All specialists | RHOAI platform limits and constraints |
| `rhoai-auth-patterns` | All specialists | Auth and RBAC patterns |
| `productization-requirements` | All specialists | Productization checklist |

## Discovery layers

Modules are discovered from three locations, in priority order:

1. **Built-in** (`$AR_HOME/profiles/<profile>/references/`): Shipped with the tool
2. **User-level** (`~/.adversarial-review/references/<specialist>/`): Applied to all projects
3. **Project-level** (`.adversarial-review/references/<specialist>/`): Repo-specific

Project-level modules override user-level, which override built-in.

## Module format

Each module is a markdown file with YAML frontmatter:

```markdown
---
name: my-security-patterns
description: Custom security patterns for our API framework
specialist: security
version: 1.0.0
source_url: https://github.com/org/security-refs/blob/main/api-patterns.md
token_estimate: 2500
---

# API Security Patterns

## Pattern 1: Authentication bypass via header injection
...
```

### Required fields

| Field | Description |
|-------|-------------|
| `name` | Unique identifier |
| `description` | What the module covers |
| `specialist` | Which specialist uses it (`security`, `all`, etc.) |
| `version` | Semantic version |

### Optional fields

| Field | Description |
|-------|-------------|
| `source_url` | Remote URL for updates |
| `token_estimate` | Estimated token count (calculated automatically if missing) |

## Managing modules

### List discovered modules

```bash
/adversarial-reviewing --list-references
```

Shows all modules across all three layers with metadata: name, version, token count, staleness, and source.

### Check for updates

```bash
/adversarial-reviewing --update-references --check-only
```

Checks modules with a `source_url` for newer versions without applying changes.

### Update modules

```bash
/adversarial-reviewing --update-references
```

Interactively updates modules from their `source_url`. Shows a diff for each update and asks for confirmation.

## Adding custom modules

### User-level (all projects)

```bash
mkdir -p ~/.adversarial-review/references/security/
# Write your module markdown file here
```

### Project-level (repo-specific)

```bash
mkdir -p .adversarial-review/references/security/
# Write your module markdown file here
```

## How modules are used

During self-refinement iteration 2+, each specialist receives their applicable reference modules. The specialist cross-checks findings against module patterns:

- A finding that matches a known vulnerability pattern gets higher confidence
- A finding that matches a known false positive pattern from a module's checklist gets lower confidence or is dismissed
- Module patterns can suggest additional checks the specialist should perform

Modules do not generate findings on their own. They sharpen the specialist's analysis.
