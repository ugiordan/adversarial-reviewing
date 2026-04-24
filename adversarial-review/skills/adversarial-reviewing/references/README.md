# Reference Modules — Authoring Guidelines

Reference modules are curated knowledge bases that adversarial-review specialists cross-check their findings against during self-refinement iterations.

## Module Format

Each module is a markdown file with YAML frontmatter:

```yaml
---
name: my-module-name
specialist: security          # security | performance | quality | correctness | architecture | all
version: "1.0.0"             # semver for update comparison
last_updated: "2026-03-26"   # ISO date for staleness checking
source_url: "https://..."    # remote URL for auto-update (omit for local-only modules)
description: "Brief description"
enabled: true                 # set to false to disable without deleting
---
```

**Required fields:** `name`, `specialist`, `enabled`
**Optional fields:** `version`, `last_updated`, `source_url`, `description`

## Directory Locations

Modules are discovered from three directories (highest precedence last):

1. **Built-in** (ships with plugin): `references/<specialist>/`
2. **User-level** (org-wide): `~/.adversarial-review/references/<specialist>/`
3. **Project-level** (repo-specific): `.adversarial-review/references/<specialist>/`

Project-level modules override user-level, which override built-in, when they share the same `(name, specialist)` pair.

## Authoring Guidelines

### 1. Use Descriptive Phrasing
Write "implementations must validate input" not "you must validate input." Imperative second-person phrasing may trigger injection detection false positives.

### 2. Include False Positive Checklists
For each issue pattern, describe what evidence the agent should look for before flagging it:
```
Before flagging emptyDir size:
1. What process writes to this mount path? Cite file:line.
2. What is the estimated write volume?
3. Is the volume actually used for data or just as a mount point parent?
```

### 3. Keep Modules Focused
One topic per module, under 5K tokens. Multiple small modules are better than one large module.

### 4. Use Verification Questions
Phrase checklist items as questions the agent should answer:
- "Is user input validated before being passed to the SQL query?"
- NOT "Always validate user input."

## Testing

Verify your module is discoverable:
```bash
scripts/discover-references.sh --list-all
scripts/discover-references.sh <specialist> --token-count
```

## Updating

Modules with `source_url` can be auto-updated:
```bash
scripts/update-references.sh --check-only
scripts/update-references.sh
```
