# Profile System

The profile system enables the same multi-agent framework to review different types of artifacts (code vs. strategy documents) with appropriate specialists, templates, and reference modules.

## Profile structure

Each profile lives in `profiles/<profile>/` and contains:

```
profiles/
  code/
    config.yml           # Profile configuration
    agents/              # Specialist prompts
      security-auditor.md
      performance-analyst.md
      code-quality-reviewer.md
      correctness-verifier.md
      architecture-reviewer.md
      devils-advocate.md
    templates/           # Output format definitions
      finding-template.md
      challenge-response-template.md
      report-template.md
      ...
    references/          # Knowledge base modules
      security/
        owasp-top10-2025.md
        agentic-ai-security.md
        ...
  strat/
    config.yml
    agents/
      feasibility-analyst.md
      architecture-reviewer.md
      security-analyst.md
      user-impact-analyst.md
      scope-completeness-analyst.md
      testability-analyst.md
      devils-advocate.md
    templates/
      finding-template.md
      challenge-response-template.md
      report-template.md
      requirements-template.md
    references/
      all/
        rhoai-platform-constraints.md
        rhoai-auth-patterns.md
        productization-requirements.md
      architecture/
      security/
      operations/
```

## config.yml

Each profile's `config.yml` defines:

```yaml
name: code
description: Source code review
agents:
  - tag: SEC
    name: Security Auditor
    file: security-auditor.md
    flag: --security
  - tag: PERF
    name: Performance Analyst
    file: performance-analyst.md
    flag: --performance
  # ...
quick_preset:
  agents: [SEC, CORR]
  iterations: 2
  budget: 150000
thorough_preset:
  agents: all
  iterations: 3
  budget: 800000
default:
  iterations: 2
  budget: 350000
```

The profile configuration is read by `profile-config.sh` and used by SKILL.md to determine which agents to spawn, which templates to use, and which presets apply.

## How profiles are selected

1. Default: `code` profile
2. With `--profile strat`: `strat` profile
3. Profile determines: agent list, templates, references, presets, validation rules

## Key differences between profiles

| Aspect | Code | Strategy |
|--------|------|----------|
| Evidence type | `file:line` references | Text citations (section, paragraph) |
| Findings have | Source Trust field | Verdict field (Approve/Revise/Reject) |
| Report includes | Remediation roadmap | Per-document verdicts |
| Specialists | 5 | 6 |
| Reference scope | `security/` only | `all/`, `architecture/`, `security/`, `operations/` |
| Supplementary outputs | None | Threat surface, NFR scan, requirements |
| Quick preset agents | SEC + CORR | SEC + FEAS |

## Adding a new profile

To create a new profile (e.g., `docs` for documentation review):

1. Create `profiles/docs/config.yml` with agent definitions
2. Create agent prompts in `profiles/docs/agents/`
3. Create templates in `profiles/docs/templates/`
4. Add reference modules in `profiles/docs/references/` (optional)
5. Update `profile-config.sh` if needed
6. Update SKILL.md to recognize the new profile flag
7. Add validation rules to `validate-output.sh`

The phase procedures (self-refinement, challenge, resolution, report) are profile-agnostic. They read the active profile's configuration and adapt automatically.

## Shared components

These components work identically across profiles:

- **Phases**: Self-refinement, challenge, resolution, report, remediation
- **Protocols**: Isolation, injection resistance, mediated communication, convergence
- **Scripts**: Validation, deduplication, budget tracking, cache management
- **Devil's advocate**: Both profiles include one, with profile-specific context handling
