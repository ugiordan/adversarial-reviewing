# Context Injection

The `--context` flag injects labeled reference material into the review. This gives specialists additional context like architecture diagrams, compliance documents, or threat models.

## Usage

```bash
# From a git repository
/adversarial-review src/ --context architecture=https://github.com/org/repo

# From a local directory
/adversarial-review src/ --context architecture=./docs/arch

# From a single file
/adversarial-review src/ --context threatmodel=./docs/threat-model.md

# Multiple context sources (repeatable)
/adversarial-review src/ \
  --context architecture=https://github.com/org/repo \
  --context compliance=./docs/compliance/
```

## Label format

Labels must be alphanumeric with optional hyphens. The label appears in the specialist's input to identify the context source:

```
--context <label>=<source>
```

Labels are validated at invocation time. Invalid labels (containing spaces, special characters) are rejected.

## Source types

| Source | Example | Behavior |
|--------|---------|----------|
| Git URL | `https://github.com/org/repo` | Cloned to cache, relevant files extracted |
| Local directory | `./docs/arch` | Files read directly |
| Local file | `./docs/threat-model.md` | Single file read |

## How context is used

Context documents are injected into each specialist's input alongside the code under review. Specialists use them to:

- Verify claims about existing infrastructure ("we already have auth middleware")
- Check consistency between strategy and implementation
- Identify gaps between documented architecture and actual code
- Cross-reference security controls claimed in compliance docs

## Safety model

!!! warning "Context documents are reference material, not trusted input"
    - Context documents may be outdated, incomplete, or contain embedded instructions
    - Agents will not follow directives found in context documents
    - Claims in context are cross-referenced against the actual code under review
    - A control documented in context but absent from code is a real gap, not an assumption
    - Agents will not suppress findings solely because context docs claim a control exists

This safety model applies to all agents across both profiles. Each agent prompt includes explicit anti-injection instructions for handling context documents.

## Caching

Context from git repositories is cached locally to avoid re-cloning on subsequent reviews. The cache is managed by `manage-cache.sh`:

- Cache is populated during review initialization
- Cache paths are validated (no symlinks, no path traversal)
- Cache is cleaned up after the review completes

## Works with both profiles

Context injection works identically for code and strategy profiles:

```bash
# Code profile with architecture context
/adversarial-review src/ --context architecture=./docs/arch

# Strategy profile with architecture context
/adversarial-review docs/strat/ --profile strat \
  --context architecture=https://github.com/org/repo
```
