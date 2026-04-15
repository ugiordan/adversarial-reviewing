# Constraint Packs

Constraint packs are organizational bundles containing enforced rules and reference material for the adversarial-review tool. Unlike `--context` (informational knowledge), constraints set **severity floors**: findings that match a constraint violation are automatically flagged at the constraint's specified severity or higher.

## Usage

```bash
# Load a constraint pack
adversarial-review --constraints packs/rhoai/ src/

# Constraints work with both profiles
adversarial-review --profile strat --constraints packs/rhoai/ strategy.md

# Combine with context for maximum coverage
adversarial-review --constraints packs/rhoai/ --context architecture=./docs src/
```

## Pack Structure

Each pack is a directory containing:

```
packs/<org-name>/
  constraints.yaml       # Required: constraint definitions with severity enforcement
  *.md                   # Optional: reference modules providing detailed context
  README.md              # Optional: pack documentation
```

## Creating Your Own Pack

1. Create a directory under `packs/` (or anywhere, and reference it by path)
2. Write a `constraints.yaml` following the schema below
3. Optionally add `.md` reference modules for detailed context

### constraints.yaml Schema

```yaml
name: "My Organization Constraints"
version: "1.0"
description: "Brief description of what these constraints cover"

constraints:
  - id: ORG-001            # Unique constraint ID (used in findings)
    title: "Short title"   # Human-readable title
    category: security     # Category: cryptography, authentication, networking, etc.
    severity: high         # Severity floor: critical, high, important, minor
    profile: both          # Which profiles: code, strat, both
    description: >         # What the constraint requires
      Detailed description of the requirement.
    detection_guidance: >  # How agents should check for violations
      What to look for in code or strategy documents.
    remediation: >         # How to fix violations
      Recommended fix approach.
```

### Severity Enforcement

Constraint severity is a **floor**, not a ceiling. Agents can escalate above the constraint's severity (e.g., a "high" constraint can produce a "critical" finding if evidence warrants it), but they cannot downgrade below the floor.

### Profile Filtering

Constraints are filtered by the active review profile. A constraint with `profile: strat` is ignored during code reviews, and vice versa. Use `profile: both` for constraints that apply universally.

## Trust Model

Packs are user-provided reference material. The tool does not cryptographically verify pack contents. For production reviews, version-control your packs alongside your code and review changes to constraint files with the same rigor as code changes.

## Included Packs

- `rhoai/`: Red Hat OpenShift AI platform constraints (10 constraints covering FIPS, auth, RBAC, secrets, image provenance, and more)
