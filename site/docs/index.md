---
hide:
  - navigation
  - toc
---

# Adversarial Review

<div style="text-align: center; padding: 40px 0;">
  <p style="font-size: 1.4em; color: #666;">
    Multi-agent adversarial code and strategy review.<br>
    Isolated specialists. Structured debate. Evidence-based resolution.
  </p>
  <p>
    <a href="getting-started/installation/" class="md-button md-button--primary">Get Started</a>
    <a href="https://github.com/ugiordan/adversarial-reviewing" class="md-button">GitHub</a>
  </p>
</div>

## What Is This?

Adversarial Review orchestrates independent specialist agents who review code or strategy documents from different perspectives, debate their findings through structured challenge rounds with evidence-based rebuttals, and surface validated findings with transparent agreement labeling.

Unlike single-pass review tools, findings must survive cross-agent scrutiny before reaching the final report. This reduces false positives and catches issues that single-perspective reviews miss.

## How It Works

The review runs in 5 phases:

1. **Self-Refinement.** Each specialist agent runs independently in its own isolated context. It reads the code or strategy, produces findings, then iterates 2-3 times, refining its analysis until the finding set stabilizes (convergence detection). Agents don't see each other's work at this stage. Reference modules (OWASP, ASVS, K8s patterns) are loaded on iteration 2+ for cross-checking.

2. **Challenge Round.** Findings from all agents are sanitized (stripped of raw output, validated structurally) and routed to other specialists based on domain affinity. Each agent reviews findings in its domain and can challenge them with a counter-argument citing specific evidence, or concur. The original author then defends or retracts.

3. **Resolution.** Duplicate findings are merged. Each finding is classified by agreement level: *unanimous* (all specialists agree), *majority* (most agree), *escalated* (significant disagreement), or *dismissed* (majority challenged). For strategy reviews, per-document verdicts (Approve/Revise/Reject) are resolved using conservative tiebreak.

4. **Report.** The final report is assembled with an executive summary, findings grouped by agreement level, and a remediation roadmap. The report transparently labels which findings had full consensus vs. majority overrides vs. unresolved disputes. Optional: finding persistence tracks new/recurring/resolved across runs.

5. **Remediation** (code profile only, `--fix`). Confirmed findings are classified (Jira-worthy, quick chore, blocked), Jira tickets are drafted, worktree branches created, and fixes implemented. Each fix is verified by re-invoking the original specialist. Every step requires explicit user confirmation.

```mermaid
flowchart LR
    subgraph Phase1["Phase 1: Self-Refinement"]
        direction TB
        A1["Spawn isolated specialists"]
        A2["2-3 iterations per agent"]
        A3["Convergence detection"]
        A4["Reference modules\n(finding-aware selection)"]
        A1 --> A2 --> A3
        A4 -.-> A1
    end

    subgraph Phase2["Phase 2: Challenge Round"]
        direction TB
        B1["Domain-aware routing"]
        B2["Cross-agent debate"]
        B3["Evidence-based rebuttal"]
        B1 --> B2 --> B3
    end

    subgraph Phase3["Phase 3: Resolution"]
        direction TB
        C1["Deduplication"]
        C2["Agreement classification"]
        C3["Verdict resolution"]
        C1 --> C2 --> C3
    end

    subgraph Phase4["Phase 4: Report"]
        direction TB
        D1["Executive summary"]
        D2["Findings by agreement level"]
        D3["Remediation roadmap"]
        D4["Finding persistence\n(--persist)"]
        D5["Prompt version tracking"]
        D1 --> D2 --> D3
        D4 -.-> D1
        D5 -.-> D1
    end

    subgraph Phase5["Phase 5: Remediation"]
        direction TB
        E1["Classify findings"]
        E2["Draft Jira tickets"]
        E3["Implement fixes"]
        E4["Fix verification\n(re-invoke specialist)"]
        E1 --> E2 --> E3 --> E4
    end

    Phase1 --> Phase2 --> Phase3 --> Phase4 --> Phase5

    style Phase5 stroke-dasharray: 5 5
    style D4 stroke-dasharray: 3 3
    style D5 stroke-dasharray: 3 3
```

> Phase 5 (dashed) only runs when `--fix` is specified (code profile only). Finding persistence and prompt version tracking (dotted) are optional (`--persist` flag).

## Two Review Profiles

<div class="grid cards" markdown>

- **Code Profile** (default)

    ---

    Reviews source code with file:line evidence. 5 specialist agents: Security Auditor, Performance Analyst, Code Quality Reviewer, Correctness Verifier, Architecture Reviewer.

    [:octicons-arrow-right-24: Code review guide](guides/code-reviews/index.md)

- **Strategy Profile** (`--profile strat`)

    ---

    Reviews strategy documents with text citation evidence and per-document verdicts (Approve/Revise/Reject). 6 specialist agents including Feasibility, User Impact, Scope, and Testability analysts.

    [:octicons-arrow-right-24: Strategy review guide](guides/strategy-reviews/index.md)

</div>

## Key Features

| Feature | Description |
|---------|-------------|
| **Agent isolation** | Each specialist runs in its own context with no access to others' raw output |
| **Mediated communication** | All inter-agent exchange goes through the orchestrator |
| **Convergence detection** | Agents self-refine until their findings stabilize |
| **Evidence-based rebuttal** | Disagreements resolved by citing `file:line` evidence or retracting |
| **Programmatic validation** | 20 bash/python scripts validate structure, detect injection, track budget |
| **Reference modules** | Pluggable knowledge bases (OWASP, ASVS, K8s security) for cross-checking |
| **Triage mode** | Evaluate external review comments (CodeRabbit, human reviewers, PR conversations) |
| **Change-impact analysis** | Git diff with caller/callee graph for tracing side effects |
| **Remediation pipeline** | Jira ticket drafts, worktree branches, PRs with user confirmation gates |

## Use Cases by Profile

The **code profile** (default) reviews source code with file:line evidence and supports the full feature set: triage of external comments, change-impact analysis via git diffs, delta re-reviews, and automated remediation. The **strategy profile** reviews design documents with text citation evidence and per-document verdicts, using context injection for architecture-aware analysis. Some features (persistence, normalization, custom budgets) work across both profiles.

```mermaid
flowchart TB
    subgraph code["Code Profile (default)"]
        direction TB
        CR["Code review\n/adversarial-reviewing src/"]
        TR["Triage external comments\n--triage pr:42"]
        CI["Change-impact analysis\n--diff"]
        DL["Delta re-review\n--delta"]
        FX["Remediation\n--fix"]
        DR["Dry run preview\n--fix --dry-run"]
        CR --> FX
        CR --> DL
        TR --> CI
    end

    subgraph strat["Strategy Profile (--profile strat)"]
        direction TB
        SR["Strategy review\n--profile strat"]
        CX["Context injection\n--context arch=./docs"]
    end

    subgraph both["Both Profiles"]
        direction TB
        PS["Finding persistence\n--persist"]
        NM["Output normalization\n--normalize"]
        SV["Save report\n--save"]
        BG["Custom budget\n--budget 500000"]
        SS["Strict scope\n--strict-scope"]
    end

    code --> both
    strat --> both

    style strat fill:#e8f5e9
    style code fill:#e3f2fd
    style both fill:#fff3e0
```

## Platform Support

| Feature | Claude Code | Cursor | AGENTS.md |
|---------|------------|--------|-----------|
| Multi-agent isolation | Enforced | Degraded (sequential) | Depends on tool |
| Strategy profile | Full support | Degraded (sequential) | Depends on tool |
| Mediated communication | Enforced | Advisory only | Advisory only |
| Output validation | Programmatic | Agent compliance | Agent compliance |
| Injection detection | Enforced | Advisory only | Advisory only |
| Phase 5 remediation | Full support | Limited | Limited |

!!! note "Cursor and AGENTS.md limitations"
    Cursor and most AGENTS.md-compatible tools cannot spawn isolated sub-agents. The plugin adapts to a **sequential persona mode** where the agent role-plays each specialist one at a time without enforcement boundaries. Both code and strategy profiles work, but isolation between specialists is advisory only. See [Installation](getting-started/installation.md) for details.
