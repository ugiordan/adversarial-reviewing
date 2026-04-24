# Quick Start

After [installing](installation.md) the plugin, here's how to run your first review in under a minute.

## Basic code review

In a Claude Code session, point it at a file or directory:

```bash
/adversarial-reviewing src/auth/
```

This runs all 5 specialists (Security, Performance, Quality, Correctness, Architecture) with default settings: 2 self-refinement iterations, 350K token budget.

## Quick mode

For a fast check with fewer specialists:

```bash
/adversarial-reviewing src/ --quick
```

Quick mode uses 2 specialists (Security + Correctness), 2 iterations, and a 150K budget.

## Thorough mode

For a deep review:

```bash
/adversarial-reviewing src/ --thorough
```

Thorough mode uses all 5 specialists, 3 iterations, and an 800K budget.

## Save the report

```bash
/adversarial-reviewing src/ --save
```

Writes the report to `docs/reviews/YYYY-MM-DD-<topic>-review.md`.

## Strategy document review

```bash
/adversarial-reviewing artifacts/strat-tasks/ --profile strat
```

Runs 6 strategy specialists and produces per-document verdicts (Approve/Revise/Reject).

## What happens during a review

1. **Phase 1**: Each specialist analyzes the code independently in isolation, self-refining through 2-3 iterations until findings converge
2. **Phase 2**: Specialists debate each other's findings through mediated challenge rounds
3. **Phase 3**: The orchestrator resolves disagreements, deduplicates, and classifies agreement levels
4. **Phase 4**: A structured report is generated with findings by severity and remediation roadmap
5. **Phase 5** (with `--fix`): Findings are classified, Jira tickets drafted, and fixes implemented via worktree branches

Each phase has programmatic validation: structure checks, injection detection, budget tracking, and convergence detection.
