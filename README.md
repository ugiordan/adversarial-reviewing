# Adversarial Review

Multi-agent adversarial code review with isolated specialists, programmatic validation, and consensus-based findings.

This plugin orchestrates independent specialist agents who review code from different perspectives, debate their findings through structured challenge rounds, and surface only validated, high-confidence issues through consensus.

## How It Works

```mermaid
flowchart LR
    subgraph Phase1["Phase 1: Self-Refinement"]
        direction TB
        A1["Spawn isolated specialists"]
        A2["2-3 iterations per agent"]
        A3["Convergence detection"]
        A1 --> A2 --> A3
    end

    subgraph Phase2["Phase 2: Challenge Round"]
        direction TB
        B1["Cross-agent debate"]
        B2["Mediated communication"]
        B3["Challenge + Defense"]
        B1 --> B2 --> B3
    end

    subgraph Phase3["Phase 3: Resolution"]
        direction TB
        C1["Consensus rules"]
        C2["Deduplication"]
        C3["Final finding set"]
        C1 --> C2 --> C3
    end

    subgraph Phase4["Phase 4: Report"]
        direction TB
        D1["Executive summary"]
        D2["Findings by severity"]
        D3["Remediation roadmap"]
        D1 --> D2 --> D3
    end

    subgraph Phase5["Phase 5: Remediation"]
        direction TB
        E1["Classify findings"]
        E2["Draft Jira tickets"]
        E3["Implement fixes + PRs"]
        E1 --> E2 --> E3
    end

    Phase1 --> Phase2 --> Phase3 --> Phase4 --> Phase5

    style Phase5 stroke-dasharray: 5 5
```

> Phase 5 (dashed) only runs when `--fix` is specified.

### Phase 1: Self-Refinement

Each specialist reviews the code independently in full isolation. No specialist sees another's output. Each agent self-refines through 2-3 iterations with convergence detection.

```mermaid
flowchart TB
    subgraph Isolation["Isolated Agent Contexts"]
        direction LR
        SEC["SEC\nSecurity\nAuditor"]
        PERF["PERF\nPerformance\nAnalyst"]
        QUAL["QUAL\nCode Quality\nReviewer"]
        CORR["CORR\nCorrectness\nVerifier"]
        ARCH["ARCH\nArchitecture\nReviewer"]
    end

    CODE["Code Under Review"] --> |"delimited input\n(generate-delimiters.sh)"| Isolation

    SEC --> V1["validate-output.sh"]
    PERF --> V2["validate-output.sh"]
    QUAL --> V3["validate-output.sh"]
    CORR --> V4["validate-output.sh"]
    ARCH --> V5["validate-output.sh"]

    V1 & V2 & V3 & V4 & V5 --> CONV["detect-convergence.sh"]
    CONV --> |"converged"| NEXT["Phase 2"]
    CONV --> |"not converged"| Isolation

    BUDGET["track-budget.sh"] -.-> |"monitors"| Isolation

    style Isolation fill:#f0f4ff,stroke:#4a6fa5
    style BUDGET stroke-dasharray: 5 5
```

### Phase 2: Challenge Round

```mermaid
flowchart LR
    subgraph Orchestrator["Orchestrator (mediates all communication)"]
        direction TB
        SANITIZE["Sanitize findings\n(strip raw output)"]
        ROUTE["Route challenges\nto relevant specialists"]
        COLLECT["Collect defenses"]
    end

    SPEC_A["Specialist A\nfindings"] --> SANITIZE
    SANITIZE --> ROUTE
    ROUTE --> SPEC_B["Specialist B\nchallenges"]
    SPEC_B --> COLLECT
    COLLECT --> SPEC_A

    style Orchestrator fill:#fff4e6,stroke:#d4a843
```

Agents never see each other's raw output. The orchestrator strips provenance markers, validates structure, and mediates every exchange.

**Single-specialist mode:** When only 1 specialist is active, a devil's advocate agent challenges the findings instead.

### Phase 3: Resolution

The orchestrator synthesizes challenges and defenses, applies consensus rules, deduplicates findings via `deduplicate.sh`, and produces the final validated finding set.

### Phase 4: Report

Generates a structured report with 9 sections: executive summary, validated findings by severity (Critical/Important/Minor/Style), dismissed findings with rationale, challenge round highlights, co-located findings, and a remediation roadmap.

### Phase 5: Remediation (optional, `--fix`)

```mermaid
flowchart LR
    CLASSIFY["Classify findings"] --> |"jira / chore / blocked"| GATE1{{"User confirms\nclassification"}}
    GATE1 --> DRAFT["Draft Jira tickets"]
    DRAFT --> GATE2{{"User confirms\ntickets"}}
    GATE2 --> WORKTREE["Create worktree\nbranches"]
    WORKTREE --> IMPLEMENT["Implement fixes"]
    IMPLEMENT --> GATE3{{"User confirms\nPRs"}}

    style GATE1 fill:#ffe6e6,stroke:#cc4444
    style GATE2 fill:#ffe6e6,stroke:#cc4444
    style GATE3 fill:#ffe6e6,stroke:#cc4444
```

Every step requires explicit user confirmation. The orchestrator never pushes, force-pushes, or targets main/master directly.

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

From inside a Claude Code session, run:

```
# One-time marketplace registration
/plugin marketplace add ugiordan/adversarial-review

# Install globally (works in every project)
/plugin install adversarial-review@ugiordan-adversarial-review
```

After installation, start a new session. The skill activates automatically when relevant, or invoke directly via `/adversarial-review`.

To update later:
```
/plugin update adversarial-review
```

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

```mermaid
block-beta
    columns 4
    space:1 CC["Claude Code"] CU["Cursor (.mdc)"] AG["AGENTS.md"]
    ISO["Agent isolation"]:1 CC_ISO["Enforced"]:1 CU_ISO["Not available"]:1 AG_ISO["Depends on tool"]:1
    MED["Mediated comms"]:1 CC_MED["Enforced"]:1 CU_MED["Advisory only"]:1 AG_MED["Advisory only"]:1
    VAL["Output validation"]:1 CC_VAL["Programmatic"]:1 CU_VAL["Agent compliance"]:1 AG_VAL["Agent compliance"]:1
    INP["Input isolation"]:1 CC_INP["Orchestrator"]:1 CU_INP["Advisory only"]:1 AG_INP["Advisory only"]:1
    PRV["Provenance markers"]:1 CC_PRV["Verified"]:1 CU_PRV["Not enforced"]:1 AG_PRV["Not enforced"]:1
    INJ["Injection detection"]:1 CC_INJ["Enforced"]:1 CU_INJ["Advisory only"]:1 AG_INJ["Advisory only"]:1

    style CC_ISO fill:#d4edda,stroke:#28a745
    style CC_MED fill:#d4edda,stroke:#28a745
    style CC_VAL fill:#d4edda,stroke:#28a745
    style CC_INP fill:#d4edda,stroke:#28a745
    style CC_PRV fill:#d4edda,stroke:#28a745
    style CC_INJ fill:#d4edda,stroke:#28a745
    style CU_ISO fill:#f8d7da,stroke:#dc3545
    style CU_MED fill:#fff3cd,stroke:#ffc107
    style CU_VAL fill:#fff3cd,stroke:#ffc107
    style CU_INP fill:#fff3cd,stroke:#ffc107
    style CU_PRV fill:#f8d7da,stroke:#dc3545
    style CU_INJ fill:#fff3cd,stroke:#ffc107
    style AG_ISO fill:#cce5ff,stroke:#004085
    style AG_MED fill:#fff3cd,stroke:#ffc107
    style AG_VAL fill:#fff3cd,stroke:#ffc107
    style AG_INP fill:#fff3cd,stroke:#ffc107
    style AG_PRV fill:#f8d7da,stroke:#dc3545
    style AG_INJ fill:#fff3cd,stroke:#ffc107
```

The full multi-agent architecture with enforced isolation is only available in Claude Code.

## Repository Structure

```mermaid
graph TD
    ROOT["adversarial-review/"] --> MP[".claude-plugin/marketplace.json"]
    ROOT --> PLUGIN["adversarial-review/"]
    ROOT --> AGENTS["AGENTS.md"]
    ROOT --> CURSOR[".cursor/rules/adversarial-review.mdc"]
    ROOT --> CI[".github/workflows/test.yml"]

    PLUGIN --> PP[".claude-plugin/plugin.json"]
    PLUGIN --> CMD["commands/adversarial-review.md"]
    PLUGIN --> SKILL["skills/adversarial-review/"]

    SKILL --> SKILLMD["SKILL.md"]
    SKILL --> AG["agents/ (6 specialists)"]
    SKILL --> PH["phases/ (5 procedures)"]
    SKILL --> PR["protocols/ (6 definitions)"]
    SKILL --> SC["scripts/ (5 validators)"]
    SKILL --> TM["templates/ (6 formats)"]
    SKILL --> TS["tests/ (5 scripts + 14 fixtures)"]

    style ROOT fill:#f0f4ff,stroke:#4a6fa5
    style SKILL fill:#e8f5e9,stroke:#2e7d32
    style PLUGIN fill:#fff8e1,stroke:#f9a825
```

## Programmatic Validation

All agent outputs are validated through bash scripts -- not just LLM judgment:

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
