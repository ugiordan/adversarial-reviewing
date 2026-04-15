# Profile System Design: STRAT Review Integration

**Date:** 2026-04-04
**Status:** Draft
**Repo:** `ugiordan/adversarial-review`

## Summary

Extend adversarial-review with a profile system that supports reviewing different artifact types (code, strategy documents, RFEs) using profile-specific agent sets, templates, and validation rules. The core debate pipeline (Phases 2-3) remains domain-agnostic and shared across all profiles.

This spec covers the `strat` profile. The `rfe` profile is deferred to v1.1.

## Motivation

adversarial-review's debate pipeline (self-refinement, challenge round with evidence-based rebuttal, resolution with agreement labeling) is domain-agnostic. The value isn't in code review specifically, it's in structured multi-perspective adversarial analysis. Strategy documents benefit from the same treatment: independent specialists analyzing a strategy, debating findings, and surfacing validated issues with transparent agreement levels.

rfe-creator currently runs 5 independent forked reviewers with no debate. adversarial-review's challenge round and evidence-based rebuttal would produce higher-quality reviews by forcing specialists to defend their positions with evidence.

## Non-Goals

- Replacing rfe-creator's Jira integration, frontmatter system, or artifact lifecycle
- Merging adversarial-review and rfe-creator into one tool
- Shipping all profiles simultaneously (RFE profile is deferred)
- Adding remediation (Phase 5) for strategy profiles

## Architecture

### Profile System

A `--profile <name>` flag selects the active profile. Default is `code` (current behavior, fully backward compatible).

```
/adversarial-review src/ --security              # code profile (default)
/adversarial-review strategies/ --profile strat   # strat profile
/adversarial-review strategies/ --profile strat --quick
```

Each profile defines:
- Agent set (`profiles/<name>/agents/`)
- Templates (`profiles/<name>/templates/`)
- Reference modules (`profiles/<name>/references/`)
- Configuration manifest (`profiles/<name>/config.yml`)

Shared infrastructure is profile-agnostic:
- `phases/` (debate pipeline)
- `protocols/` (mediated communication, convergence, budget, etc.)
- `scripts/` (profile-aware via `--profile` flag)

### Directory Structure

```
adversarial-review/skills/adversarial-review/
  phases/              # shared across all profiles
  protocols/           # shared
  scripts/             # shared (profile-aware)
  profiles/
    code/
      config.yml
      agents/
        security-auditor.md
        performance-analyst.md
        code-quality-reviewer.md
        correctness-verifier.md
        architecture-reviewer.md
        devils-advocate.md
      templates/
        finding-template.md
        challenge-response-template.md
        report-template.md
        ...
      references/
        security/
          owasp-top10-2025.md
          agentic-ai-security.md
          asvs-5-highlights.md
          k8s-security.md
    strat/
      config.yml
      agents/
        feasibility-analyst.md
        architecture-reviewer.md
        security-analyst.md
        user-impact-analyst.md
        scope-completeness-analyst.md
        devils-advocate.md
      templates/
        finding-template.md
        challenge-response-template.md
        report-template.md
      references/
        security/
          rhoai-auth-patterns.md
        architecture/
          rhoai-platform-constraints.md
        operations/
          productization-requirements.md
```

### Migration: Code Profile

Current top-level `agents/`, `templates/`, and `references/` directories are copied (not symlinked) to `profiles/code/`. Symlinks are fragile across platforms and Git.

**v1.0 (this work):**
- Create `profiles/code/` with copies of current files
- Create `profiles/strat/` with new files
- Update SKILL.md to read from `profiles/<profile>/` based on `--profile` flag
- Top-level `agents/`, `templates/`, `references/` remain as fallback. If `profiles/code/` doesn't exist, fall back to top-level directories. Emit deprecation warning.

**v1.1:**
- Remove top-level `agents/`, `templates/`, `references/`
- All profiles required to live under `profiles/`

### Profile Configuration Manifest

Each profile has a `config.yml` that scripts and the orchestrator read:

```yaml
# profiles/strat/config.yml
name: strat
description: Strategy document review
evidence_format: text_citation    # vs "file_line" for code
has_verdicts: true                # enables verdict resolution
verdict_values: [approve, revise, reject]
phase5_enabled: false             # no remediation for strat

agents:
  - prefix: FEAS
    file: feasibility-analyst.md
  - prefix: ARCH
    file: architecture-reviewer.md
  - prefix: SEC
    file: security-analyst.md
  - prefix: USER
    file: user-impact-analyst.md
  - prefix: SCOP
    file: scope-completeness-analyst.md

quick_specialists: [SEC, FEAS]
default_specialists: all
thorough_specialists: all

templates:
  finding: finding-template.md
  challenge_response: challenge-response-template.md
  report: report-template.md
```

Scripts read this manifest via a helper:

```bash
# Example: get evidence format for current profile
scripts/profile-config.sh <profile_dir> evidence_format
# Returns: text_citation
```

## STRAT Agent Set

Five agents, designed for maximum adversarial tension with odd-number majority guarantee.

### FEAS (Feasibility Analyst)

- **Domain:** Can we build this? Effort estimates credibility, codebase readiness, team capability assumptions, dependency availability
- **Key behavior:** Reads architecture context to verify component claims. Challenges strategies that assume capabilities the platform doesn't have.
- **Natural adversaries:** ARCH (pragmatism vs ideal design), SEC (speed vs safety), SCOP (effort vs scope)

### ARCH (Architecture Reviewer)

- **Domain:** Does this fit the platform? Integration patterns, component boundaries, API contracts, dependency correctness, coupling
- **Key behavior:** Cross-references architecture context docs. Challenges strategies proposing patterns inconsistent with the platform.
- **Natural adversaries:** FEAS (ideal vs practical), USER (extensibility vs simplicity), SCOP (completeness vs over-engineering)

### SEC (Security Analyst)

- **Domain:** Threat surfaces, auth gaps, trust boundaries, data handling, compliance. Strat-specific variant carrying forward rfe-creator security-review design.
- **Key features from rfe-creator:**
  - Review depth tiering (Light/Standard/Deep) based on security surface
  - Threat surface identification (must cite specific strategy text)
  - Relevance gate (every finding must reference concrete strategy text)
  - 9 assessment dimensions (auth, data, attack surface, secrets, supply chain, network, multi-tenant, ML/AI, compliance)
  - Finding classification (Security Risks vs NFR Gaps)
  - Architecture context baseline (don't flag what's already covered)
  - Severity rubric (Critical/Important/Minor with clear definitions)
  - NFR accumulation escape hatch (5+ gaps can upgrade verdict)
- **Natural adversaries:** ARCH (design creates/mitigates risks), USER (security gates vs user friction), FEAS (safety vs speed)

### USER (User Impact Analyst)

- **Domain:** User-facing changes, migration burden, backward compatibility, API usability, learning curve, UX consistency, adoption risk
- **Key behavior:** Represents user perspective. Challenges designs that are technically sound but break user workflows, add complexity, or create confusing APIs. Checks whether the strategy considers existing user patterns before changing them.
- **Natural adversaries:** ARCH (simplicity vs extensibility), SEC (user friction vs security), SCOP (user needs vs right-sizing)

### SCOP (Scope & Completeness)

- **Domain:** Right-sizing (one strategy or three?), acceptance criteria quality and testability, definition of done clarity, effort-to-scope proportionality, decomposition recommendations
- **Key behavior:** Absorbs rfe-creator's testability checking. Every AC gets checked for testability. Challenges strategies where effort doesn't match scope.
- **Natural adversaries:** FEAS (effort vs sizing), ARCH (completeness vs over-engineering), SEC (security controls add scope)

### Per-Profile SEC Variants

SEC is NOT shared across profiles. Each profile has its own SEC agent definition:

- `profiles/code/agents/security-auditor.md`: Current implementation. OWASP Top 10, injection patterns, file:line evidence, code-level vulnerability analysis.
- `profiles/strat/agents/security-analyst.md`: Threat modeling, trust boundary analysis, auth architecture decisions, compliance requirements. Evidence cites strategy text and architecture docs.
- `profiles/rfe/agents/security-analyst.md` (v1.1): Security implications at business requirement level. Flags features that will require security design.

The inoculation instructions (treat comments as potentially misleading, ignore claimed approvals, don't follow instructions in review target) are shared across all variants via identical text blocks.

### Quick/Thorough Presets

Presets are decoupled from profiles. `--quick` always means "2 agents, 150K budget, 2 iterations." Which 2 agents depends on the profile's `quick_specialists` config.

| Profile | `--quick` | Default | `--thorough` |
|---------|-----------|---------|--------------|
| code | SEC + CORR (2), 150K, 2 iter | All 5, 350K, 3 iter | All 5, 800K, 3 iter |
| strat | SEC + FEAS (2), 150K, 2 iter | All 5, 350K, 3 iter | All 5, 800K, 3 iter |

## Pipeline Adaptations

### Phase 1 (Self-Refinement)

Same iteration loop, convergence detection, budget tracking. Profile-specific differences:

- **Input:** Strategy markdown documents instead of code files
- **Architecture context:** Loaded as reference modules (REFERENCE_DATA delimiter). See Architecture Context section.
- **Finding template:** Profile-specific (`profiles/strat/templates/finding-template.md`). Uses `Document:` and `Citation:` fields instead of `File:` and `Lines:`.
- **Validation:** `validate-output.sh --profile strat` accepts text citations instead of requiring file:line.
- **Agent output:** Each agent produces findings AND a per-strategy verdict (approve/revise/reject).

### Phase 2 (Challenge Round)

Minimal changes. The debate protocol is domain-agnostic.

- Agents challenge findings AND verdicts. "You said reject, but your only finding is Minor severity. That doesn't justify reject."
- Evidence-based rebuttal (iteration 3) requires citing specific strategy text or architecture docs instead of file:line. The rebuttal prompt adapts:

  > For each finding you are challenging or defending, you MUST cite specific evidence from the strategy document or architecture context.
  >
  > - If you are **challenging** a finding: cite the specific strategy text that shows the finding is invalid
  > - If you are **defending** a finding: cite the specific strategy text that creates the risk
  > - If you cannot cite specific evidence, **retract your position**

- Challenge response template adds verdict field:

  ```
  Response to [FINDING-ID]:
  Action: [Agree | Challenge | Abstain]
  Severity assessment: [Critical | Important | Minor]
  Verdict assessment: [Approve | Revise | Reject]    (strat/rfe profiles only)
  Evidence: [supporting or counter-evidence, max 2000 chars]
  ```

- Unanimous early exit still applies.

### Phase 3 (Resolution)

Two resolution tracks running in parallel:

**Finding resolution:** Unchanged. Consensus/majority/escalated/dismissed with the existing rules.

**Verdict resolution (new, strat/rfe profiles only):**

Per-strategy, tally agent verdicts after debate:

| Condition | Result |
|-----------|--------|
| All agents agree | Unanimous verdict |
| Strict majority agrees | Majority verdict |
| No majority (e.g., 2-2-1) | **Most conservative verdict wins** (reject > revise > approve) |

Rationale for conservative tiebreaker: a strategy with split opinions should not be approved. "Revise" is safer than "approve" when specialists can't agree.

Agreement level classification applies to verdicts, not just findings. A 4-1 split on approve/revise is "Strong Agreement: approve" with the dissenting position preserved in the report.

### Phase 4 (Report)

Profile-specific report template (`profiles/strat/templates/report-template.md`).

Key differences from code report:

- **Executive summary** includes per-strategy verdict table with agreement level
- **Findings grouped by strategy** (not by severity like code review)
- **Verdict breakdown** shows each agent's verdict with rationale
- **Dissenting verdicts** shown transparently with full positions
- **Architecture context citations** included in evidence

Report structure:

```markdown
# Strategy Review Report

## Executive Summary
**Review Date:** YYYY-MM-DD
**Specialists:** FEAS, ARCH, SEC, USER, SCOP
**Strategies Reviewed:** N
**Agreement Level:** [Full Consensus | Strong Agreement | ...]

| Strategy | Verdict | Agreement | Critical | Important | Minor |
|----------|---------|-----------|----------|-----------|-------|
| STRAT-001 | Revise | Strong (4/5) | 1 | 2 | 0 |
| STRAT-002 | Approve | Full Consensus | 0 | 0 | 1 |

## STRAT-001: [Title]

### Verdict: Revise (Strong Agreement, 4/5)
| Agent | Verdict | Rationale |
|-------|---------|-----------|
| FEAS | Approve | Effort is achievable |
| ARCH | Revise | Missing HA design |
| SEC | Revise | Auth gap on new endpoint |
| USER | Revise | Breaks existing API contract |
| SCOP | Revise | ACs not testable |

### Findings
[standard finding format, grouped by severity]

### Dissenting Position
FEAS: "Effort is achievable as-is. The missing HA design is a v2 concern."
```

### Phase 5 (Remediation)

**Code profile only.** Strat profile skips Phase 5 entirely. Strategy revision suggestions are included inline in findings (each finding with severity >= Important includes a concrete rewrite recommendation for the strategy text). No separate remediation phase, Jira integration, or worktree workflow.

## Evidence Format

### Code Profile (unchanged)

```
File: src/auth/handler.go
Lines: 42-58
Evidence: The validateToken() call at line 42 does not check token expiry...
```

Validation regex: `[a-zA-Z0-9_/.-]+\.(go|py|ts|js|...):[0-9]+`

### STRAT Profile

```
Document: STRAT-001-gateway-api-sharding
Citation: Technical Approach, paragraph 3
Evidence: The strategy proposes a new OAuth token exchange but does not specify...
```

Validation: Checks for `Document:` and `Citation:` fields. No file extension requirement. `Citation:` must reference a section, paragraph, or acceptance criterion.

### Validation Script Changes

`validate-output.sh` gains a `--profile <name>` flag (or reads `--evidence-format` from profile config):

```bash
# Code profile (current behavior)
scripts/validate-output.sh <file> <role_prefix> --profile code

# Strat profile
scripts/validate-output.sh <file> <role_prefix> --profile strat
```

When `--profile strat`:
- Evidence regex accepts text citations instead of file:line
- Finding template expects `Document:` + `Citation:` instead of `File:` + `Lines:`
- Verdict field is validated (must be approve/revise/reject)
- MIN_EVIDENCE_CHARS threshold is maintained (100 chars) since strategy evidence should be equally substantive

`manage-cache.sh` propagates `--profile` to all internal `validate-output.sh` calls.

## Architecture Context

Architecture context is treated as a **reference module**, not a separate input type. This avoids introducing a 5th delimiter category and reuses the existing REFERENCE_DATA infrastructure.

### Fetch Script

New script: `scripts/fetch-architecture-context.sh`

```bash
# Fetch/update architecture context
scripts/fetch-architecture-context.sh --repo <url_or_path> --output <dir>

# Default: clones opendatahub-io/architecture-context
scripts/fetch-architecture-context.sh
```

The script:
1. Clones or updates the architecture context repo into `.context/architecture-context/`
2. Reads `PLATFORM.md` and component directories under `architecture/rhoai-*/`
3. For each strategy being reviewed, matches component names mentioned in the strategy text against available architecture docs (simple grep-based matching on component names and directory names)
4. Writes matched docs as reference modules to a temp directory with proper frontmatter (one module per component doc, `applicable_to: all`)
5. `discover-references.sh` picks them up as ephemeral reference modules via a `--extra-dir` flag

### Invocation

```bash
# Auto-fetch from default repo
/adversarial-review strategies/ --profile strat --arch-context

# Specify repo or local path
/adversarial-review strategies/ --profile strat --arch-context https://github.com/org/arch-context.git
/adversarial-review strategies/ --profile strat --arch-context /path/to/local/context
```

When `--arch-context` is not specified, agents still run but without platform context. Each agent notes "Architecture context unavailable" in its assessment.

### Reference Module Format

Architecture context docs are wrapped as reference modules with standard frontmatter:

```yaml
---
module: rhoai-platform-context
version: auto-fetched
applicable_to: [FEAS, ARCH, SEC, USER, SCOP]
source_url: https://github.com/opendatahub-io/architecture-context
---
```

All agents receive architecture context. The existing 3-layer reference discovery (built-in, user, project) applies. Architecture context is an additional ephemeral layer.

## Reference Modules

### Built-in (profiles/strat/references/)

| Module | Applicable To | Content |
|--------|--------------|---------|
| `rhoai-auth-patterns` | SEC | 3 approved auth patterns (kube-auth-proxy, kube-rbac-proxy, Kuadrant) with scope and usage |
| `rhoai-platform-constraints` | ARCH, FEAS | Service Mesh stance, Gateway API status, supported operators, component ownership |
| `productization-requirements` | SCOP, SEC | FIPS compliance, SBOM requirements, supported dependency list, upgrade path policy |

### Discovery

`discover-references.sh` gains profile awareness:

```bash
# Discover references for strat profile
scripts/discover-references.sh <specialist> --profile strat
```

When `--profile strat`, discovery searches:
1. `profiles/strat/references/<specialist>/` (built-in)
2. `~/.adversarial-review/references/strat/<specialist>/` (user-level)
3. `.adversarial-review/references/strat/<specialist>/` (project-level)

Code profile references (OWASP, ASVS, k8s-security) are NOT discovered for strat profile. Each profile has its own reference namespace.

## Scope Resolution (STRAT Profile)

For code profile, scope is resolved from files/dirs/git diff. For strat profile:

1. **User specifies files/dirs**: Use exactly those strategy markdown files
2. **All files in directory**: If user passes a directory, glob for `*.md` files
3. **Nothing found**: Ask the user explicitly

No git diff mode for strat profile (strategies aren't diffed). No sensitive file blocklist (strategy docs don't contain secrets).

The scope file lists strategy document paths. Scope confinement ensures findings reference only the reviewed strategies.

## Backward Compatibility

- No `--profile` flag = code profile. All existing behavior unchanged.
- All existing flags (`--quick`, `--thorough`, `--delta`, `--diff`, `--triage`, `--fix`, `--save`, etc.) work with code profile.
- `--delta`, `--diff`, `--triage`, `--fix` are code-profile-only flags. Using them with `--profile strat` produces an error: "Flag X is not supported with --profile strat."
- `--save` works with all profiles.
- `--budget`, `--force`, `--keep-cache`, `--reuse-cache` work with all profiles.
- `--arch-context` is strat-profile-only. Using it with code profile produces an error.

## Testing

### Unit Tests (scripts)

- `validate-output.sh` with `--profile strat`: accepts text citations, rejects file:line requirement, validates verdict field
- `validate-output.sh` with `--profile code`: unchanged behavior (regression)
- `profile-config.sh`: reads config.yml correctly
- `discover-references.sh --profile strat`: discovers strat-specific modules only
- `detect-convergence.sh`: works with strat findings (domain-agnostic, should pass)
- `deduplicate.sh`: works with strat findings (domain-agnostic, should pass)

### Integration Tests

- End-to-end strat review with `--profile strat --quick` (SEC + FEAS, 2 agents)
- Verdict resolution with split verdicts (test conservative tiebreaker)
- Evidence-based rebuttal with strategy text citations
- Architecture context as reference module injection

### Regression Tests

- Full code profile pipeline unchanged after adding profile system
- All existing tests pass without modification

## Implementation Order

1. **Profile infrastructure:** `config.yml` schema, `profile-config.sh` helper, `--profile` flag parsing in SKILL.md
2. **Migrate code profile:** Copy current `agents/`, `templates/`, `references/` to `profiles/code/`. Add fallback logic. Verify all existing tests pass.
3. **Validation changes:** Add `--profile` support to `validate-output.sh` and `manage-cache.sh`
4. **STRAT agents:** Write 5 agent prompts + devil's advocate for `profiles/strat/agents/`
5. **STRAT templates:** Finding template, challenge response template, report template for `profiles/strat/templates/`
6. **Verdict resolution:** Add verdict resolution track to `phases/resolution.md`
7. **Report adaptation:** Add verdict table and per-strategy grouping to strat report template
8. **Architecture context:** `fetch-architecture-context.sh`, reference module wrapping, `--arch-context` flag
9. **Reference modules:** Write built-in strat reference modules
10. **Phase adaptations:** Update phase docs for profile-aware behavior (evidence rebuttal prompt, Phase 5 skip)
11. **Testing:** Unit tests, integration tests, regression tests
12. **Documentation:** Update README.md, AGENTS.md, SKILL.md

## Deferred to v1.1

- `rfe` profile (3-5 agents: CLAR, FEAS, SCOP, IMPT, SEC)
- Removal of top-level `agents/`, `templates/`, `references/` directories
- Cross-profile review (review STRAT with context from its source RFE)
- Phase 5 for strat profile (strategy revision automation)
- Jira integration for strat findings

## Dependencies

- bash 4.0+
- python3 (JSON, YAML parsing for config.yml)
- git (for `--arch-context` repo cloning)
- No new npm or pip packages

## Risks

| Risk | Mitigation |
|------|------------|
| Profile abstraction is too leaky (scripts assume code) | Comprehensive grep for hardcoded file:line patterns before shipping |
| STRAT agents don't produce good debate | Test with real strategies (STRAT-001 gateway sharding). Iterate on prompts. |
| USER agent is too subjective | Clear prompt with concrete checkpoints (API changes, migration burden, learning curve) |
| Architecture context fetch is slow | Cache locally, reuse across runs via `--keep-cache` |
| Config.yml adds YAML parsing dependency | python3 already required. Simple schema, no complex parsing. |
