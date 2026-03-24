# Adversarial Review

Multi-agent adversarial code review with isolated specialists, programmatic validation, and consensus-based findings.

This plugin orchestrates independent specialist agents who review code from different perspectives, debate their findings through structured challenge rounds, and surface only validated, high-confidence issues through consensus.

## How It Works

```
                          +-------------------+
                          |   Orchestrator    |
                          | (mediates all     |
                          |  communication)   |
                          +--------+----------+
                                   |
                 +-----------------+-----------------+
                 |                 |                 |
          +------+------+  +------+------+  +------+------+
          |  Phase 1    |  |  Phase 2    |  |  Phase 3    |
          | Self-Refine |->| Challenge   |->| Resolution  |
          | (isolated)  |  | (debate)    |  | (consensus) |
          +------+------+  +------+------+  +------+------+
                 |                 |                 |
          +------+------+  +------+------+  +------+------+
          |  Phase 4    |  |  Phase 5    |  |             |
          |  Report     |  | Remediation |  |    Done     |
          | (generate)  |  | (--fix only)|  |             |
          +-------------+  +-------------+  +-------------+
```

### Phase 1: Self-Refinement

Each specialist reviews the code independently in full isolation. No specialist sees another's output. Each agent self-refines through 2-3 iterations with convergence detection.

```
  +-------+   +-------+   +-------+   +-------+   +-------+
  |  SEC  |   | PERF  |   | QUAL  |   | CORR  |   | ARCH  |
  |       |   |       |   |       |   |       |   |       |
  | iter1 |   | iter1 |   | iter1 |   | iter1 |   | iter1 |
  | iter2 |   | iter2 |   | iter2 |   | iter2 |   | iter2 |
  | iter3 |   | iter3 |   | iter3 |   | iter3 |   | iter3 |
  +---+---+   +---+---+   +---+---+   +---+---+   +---+---+
      |           |           |           |           |
      +-----+-----+-----+-----+-----+-----+-----+----+
            |                 |                 |
      [validate-output.sh] [detect-convergence.sh] [track-budget.sh]
```

### Phase 2: Challenge Round

Specialists challenge each other's findings through structured debate. The orchestrator mediates all communication — agents never see raw output from other agents.

### Phase 3: Resolution

The orchestrator synthesizes challenges and defenses, applies consensus rules, deduplicates findings, and produces the final validated finding set.

### Phase 4: Report

Generates a structured report with executive summary, validated findings by severity, dismissed findings with rationale, and a remediation roadmap.

### Phase 5: Remediation (optional)

When invoked with `--fix`, classifies findings as Jira tickets, chores, or blocked items. Creates isolated worktree branches, implements fixes, and proposes PRs — all with explicit user confirmation gates.

## Specialists

| Specialist | Flag | Focus Area |
|-----------|------|------------|
| Security Auditor | `--security` | Vulnerabilities, injection, auth, crypto, OWASP Top 10 |
| Performance Analyst | `--performance` | Complexity, memory, I/O, caching, scalability |
| Code Quality Reviewer | `--quality` | Maintainability, SOLID, patterns, readability |
| Correctness Verifier | `--correctness` | Logic errors, edge cases, race conditions, invariants |
| Architecture Reviewer | `--architecture` | Coupling, cohesion, boundaries, extensibility |

Default: all 5 specialists. Use flags to select specific ones.

## Installation

### Claude Code Plugin (Full Feature Set)

```bash
# One-time marketplace registration
claude marketplace add --git https://github.com/ugiordan/adversarial-review.git

# Install globally (works in every project)
claude plugin add adversarial-review --scope user
```

After installation, invoke via `/adversarial-review` or through the Skill tool.

### Cursor (Degraded Single-Agent Mode)

```bash
# Clone the repo
git clone https://github.com/ugiordan/adversarial-review.git $HOME/.adversarial-review

# Copy rules to your project
mkdir -p .cursor/rules
cp $HOME/.adversarial-review/.cursor/rules/adversarial-review.mdc .cursor/rules/
```

Cursor cannot spawn isolated sub-agents. The plugin adapts to a sequential persona mode where the agent role-plays each specialist in sequence.

### AGENTS.md (Universal)

```bash
# Clone the repo
git clone https://github.com/ugiordan/adversarial-review.git $HOME/.adversarial-review
```

Reference or inline `AGENTS.md` in your AI tool's context. Feature set depends on tool capabilities.

## Usage

```
/adversarial-review [files/dirs] [flags]
```

### Mode Flags

| Flag | Effect |
|------|--------|
| `--quick` | 2 specialists (SEC + CORR), 2 iterations, 200K budget |
| `--thorough` | All 5 specialists, 3 iterations, 800K budget |
| `--delta` | Re-review only changes since last review |
| `--save` | Write report to `docs/reviews/YYYY-MM-DD-<topic>-review.md` |
| `--fix` | Enable Phase 5 (remediation with Jira drafts, worktree branches, PRs) |
| `--budget <N>` | Override default 500K token budget |
| `--force` | Override 200-file hard ceiling |

### Examples

```bash
# Review staged changes with all specialists
/adversarial-review

# Security-focused review of specific files
/adversarial-review src/auth/ --security

# Quick review of recent changes
/adversarial-review --quick --delta

# Thorough review with report saved and fixes proposed
/adversarial-review src/ --thorough --save --fix
```

## Security Properties by Install Path

The three installation paths provide different security guarantees:

```
+---------------------------+----------------+----------------+----------------+
| Property                  | Claude Code    | Cursor (.mdc)  | AGENTS.md      |
+---------------------------+----------------+----------------+----------------+
| Agent isolation           | Enforced       | Not available  | Depends on tool|
| Mediated communication    | Enforced       | Advisory only  | Advisory only  |
| Output validation         | Programmatic   | Agent compliance| Agent compliance|
| Input isolation           | Orchestrator   | Advisory only  | Advisory only  |
| Provenance markers        | Verified       | Not enforced   | Not enforced   |
| Injection detection       | Enforced       | Advisory only  | Advisory only  |
| Update mechanism          | claude plugin  | Manual git pull| Manual git pull|
+---------------------------+----------------+----------------+----------------+
```

The full multi-agent architecture with enforced isolation is only available in Claude Code.

## Architecture

```
adversarial-review/
+-- .claude-plugin/marketplace.json        # Marketplace metadata
+-- adversarial-review/                    # Plugin directory
|   +-- .claude-plugin/plugin.json         # Plugin metadata
|   +-- commands/adversarial-review.md     # /adversarial-review slash command
|   +-- skills/adversarial-review/         # Skill directory
|       +-- SKILL.md                       # Main orchestrator
|       +-- agents/                        # 6 specialist prompts
|       +-- phases/                        # 5 phase procedures
|       +-- protocols/                     # 6 protocol definitions
|       +-- scripts/                       # 5 bash validation scripts
|       +-- templates/                     # 6 output templates
|       +-- tests/                         # 5 test scripts + 14 fixtures
|       +-- config/                        # Model configuration (v2)
+-- AGENTS.md                              # Universal AI tool entry point
+-- .cursor/rules/adversarial-review.mdc   # Cursor rules (degraded mode)
+-- .github/workflows/test.yml             # CI: runs 51 tests
```

## Programmatic Validation

All agent outputs are validated through bash scripts — not just LLM judgment:

| Script | Purpose |
|--------|---------|
| `validate-output.sh` | Validates finding structure, detects injection attempts |
| `detect-convergence.sh` | Checks if finding set is stable between iterations |
| `deduplicate.sh` | Removes duplicate findings across specialists |
| `track-budget.sh` | Token budget initialization, tracking, and estimation |
| `generate-delimiters.sh` | Produces unique delimiters for code isolation |

## Testing

```bash
cd adversarial-review/skills/adversarial-review
bash tests/run-all-tests.sh
```

Test suite: **51 tests** covering validation, injection resistance, convergence detection, budget tracking, deduplication, and single-agent pipeline integration.

## Dependencies

- `bash` 4.0+
- `python3` (JSON serialization and unicode normalization)
- Claude Code Agent tool (for full multi-agent feature set)
- No npm or pip packages required

## License

Apache-2.0
