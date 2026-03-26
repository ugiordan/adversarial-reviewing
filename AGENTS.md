# AGENTS.md -- Universal Entry Point for Adversarial Review

## Installation Check

Before proceeding, verify that adversarial-review is installed:

```bash
AR_HOME="${ADVERSARIAL_REVIEW_HOME:-$HOME/.adversarial-review/adversarial-review}"
[ -d "$AR_HOME/scripts" ] || echo "ERROR: adversarial-review not found at $AR_HOME. Clone it or set ADVERSARIAL_REVIEW_HOME."
```

## Overview

Multi-agent adversarial code review with isolated specialists, programmatic
validation, and consensus-based findings. Reviews code from 5 specialist
perspectives: Security, Performance, Code Quality, Correctness, Architecture.

## Multi-Agent Mode

For tools with sub-agent support (e.g., Claude Code Agent tool), spawn isolated
sub-agents for each specialist and execute the following phases:

- **Phase 1 -- Self-refinement**: Each specialist performs 2-3 iterations of
  analysis with convergence detection. Run
  `bash $AR_HOME/scripts/detect-convergence.sh` to determine when a specialist
  has stabilized its findings.

- **Phase 2 -- Challenge round**: Cross-agent debate with mediated communication.
  Specialists challenge each other's findings through structured rebuttals.

- **Phase 3 -- Resolution**: Consensus-based filtering and deduplication. Run
  `bash $AR_HOME/scripts/deduplicate.sh` to merge overlapping findings.

- **Phase 4 -- Report generation**: Aggregate validated findings into a
  structured report. Run `bash $AR_HOME/scripts/validate-output.sh` to verify
  report structure and completeness.

- **Phase 5 -- Remediation** (optional, with `--fix`): Generate and apply
  patches for confirmed findings.

- **Triage mode** (`--triage`): Specialists evaluate external review comments
  instead of finding issues. Use `validate-triage-output.sh` for output validation.
  Convergence detection uses `detect-convergence.sh --triage`.

### Script References

All scripts use the `$AR_HOME/` prefix:

- `bash $AR_HOME/scripts/validate-output.sh` -- validate report structure
- `bash $AR_HOME/scripts/detect-convergence.sh` -- detect specialist convergence
- `bash $AR_HOME/scripts/deduplicate.sh` -- deduplicate findings
- `bash $AR_HOME/scripts/track-budget.sh` -- track token budget consumption
- `bash $AR_HOME/scripts/generate-delimiters.sh` -- generate unique delimiters
- `bash $AR_HOME/scripts/build-impact-graph.sh` -- build change-impact graph from git diff
- `bash $AR_HOME/scripts/parse-comments.sh` -- normalize external review comments
- `bash $AR_HOME/scripts/validate-triage-output.sh` -- validate triage output format
- `bash $AR_HOME/scripts/discover-references.sh` -- discover and filter reference modules (3-layer: built-in, user, project)
- `bash $AR_HOME/scripts/update-references.sh` -- update reference modules from remote `source_url`

## Degraded Single-Agent Mode

For tools without sub-agent support, the agent assumes each specialist persona
sequentially:

1. For each specialist (SEC, PERF, QUAL, CORR, ARCH):
   - Read the specialist prompt from `$AR_HOME/agents/<name>.md`
   - Analyze the target code from that perspective
   - Produce findings using the template from `$AR_HOME/templates/finding-template.md`

2. Self-challenge findings using a simplified Phase 2 (devil's advocate approach).

3. Deduplicate findings and produce the final report.

**Limitations in degraded mode:**

- Agent isolation and mediated communication are advisory only in this mode.
  There is no enforcement mechanism when a single agent assumes all roles.
- Output validation via scripts still applies when shell access is available.

## Specialist and Mode Flags

Specialist flags (default: all 5):

- `--security` -- Security specialist only
- `--performance` -- Performance specialist only
- `--quality` -- Code Quality specialist only
- `--correctness` -- Correctness specialist only
- `--architecture` -- Architecture specialist only

Mode flags:

- `--delta` -- Review only changed lines (diff mode)
- `--save` -- Save report to disk
- `--fix` -- Generate and apply remediation patches
- `--quick` -- Reduced iteration count for faster reviews
- `--thorough` -- Increased iteration count for deeper analysis
- `--budget <tokens>` -- Set token budget cap
- `--diff` -- Enable change-impact analysis (diff + caller/callee graph)
- `--diff --range <range>` -- Specify git commit range for diff analysis
- `--triage <source>` -- Evaluate external review comments (pr:<N>, file:<path>, -)
- `--gap-analysis` -- Include coverage gap analysis in triage report
- `--list-references` -- List all discovered reference modules with metadata
- `--update-references` -- Update modules that have a `source_url` (interactive)
- `--update-references --check-only` -- Check for updates without applying
- `--strict-scope` -- Reject (not demote) out-of-scope findings and patches
- `--fix --dry-run` -- Preview remediation without writing anything

## Report Save Path

When `--save` is used, reports are written to:

```
docs/reviews/YYYY-MM-DD-<topic>-review.md
```

## Security Properties

| Property | Multi-agent | Single-agent (degraded) |
|---|---|---|
| Agent isolation | Enforced | Not available |
| Mediated communication | Enforced | Advisory only |
| Output validation | Programmatic | Depends on shell access |
| Injection detection | Enforced | Advisory only |

## References

Companion files in `$AR_HOME/`:

- Agent prompts: `$AR_HOME/agents/`
- Phase procedures: `$AR_HOME/phases/`
- Protocols: `$AR_HOME/protocols/`
- Templates: `$AR_HOME/templates/`
- Scripts: `$AR_HOME/scripts/`
- Reference modules: `$AR_HOME/references/` (built-in), `~/.adversarial-review/references/` (user), `.adversarial-review/references/` (project)

## Dependencies

- bash 4.0+
- python3
- git (for `--diff` change-impact analysis)
- GitHub MCP tools (optional, for `--triage pr:<N>`)
