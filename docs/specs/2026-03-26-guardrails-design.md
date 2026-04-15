# Guardrails Protocol Design Spec

**Date:** 2026-03-26
**Status:** Draft
**Motivation:** The adversarial-review tool is growing in capability (`--fix`, `--triage`, reference modules, auto-update) and preparing for wider adoption. This spec defines enforceable guardrails across agent behavior, cost control, safety, output quality, and observability.

**Principle:** Guardrails should be enforceable (checked programmatically), not advisory. Where enforcement isn't possible (e.g., single-agent degraded mode), guardrails degrade to documented warnings.

---

## A. Agent Behavior Guardrails

### A.1 Scope Confinement

**Problem:** An agent may report findings on files outside the review target, producing noise or hallucinated references.

**Design:**

- `validate-output.sh` gains a `--scope <file-list>` flag.
- `<file-list>` is a newline-delimited file of repo-relative paths that constitute the review target.
- When `--scope` is provided, every finding's `File:` field is checked against the list.
- Findings referencing files not in scope are flagged with `SCOPE_VIOLATION` in the validation output.
- The orchestrator decides how to handle scope violations:
  - **Default:** Demote to `Minor` severity and append `[out-of-scope]` to the title.
  - **Strict mode (`--strict-scope`):** Reject the finding entirely.

**Scope file generation:** The orchestrator generates the scope file during Step 2 (Scope Resolution) by writing one repo-relative path per line for all files in the review target. In `--diff` mode, the scope includes only the changed files — impact graph files remain out of scope (they are context-only, as defined in SKILL.md).

**Validation output schema change:** `validate-output.sh`'s JSON output gains a `"warnings"` array alongside the existing `"errors"` array. Warnings do not cause exit code 1.

```json
{"valid": true, "errors": [], "warnings": ["SCOPE_VIOLATION: File 'src/unrelated.ts' not in review scope"], "finding_count": 5}
```

**Backward compatibility:** Existing callers that only check `valid` and `errors` are unaffected. The `warnings` array is additive — absent from output when no warnings exist.

### A.2 Iteration Hard Cap

**Problem:** Convergence detection relies on finding-set stability. A pathological agent could oscillate between two states indefinitely.

**Design:**

- The existing iteration limits (3 default, 3 thorough, 2 quick) defined in `self-refinement.md` and SKILL.md remain the *target* iteration count for convergence detection.
- `MAX_ITERATIONS` is a *safety cap* above those targets: default=4, thorough=4, quick=2.
- After `MAX_ITERATIONS` iterations without convergence, force-stop the agent.
- Use the output from the final iteration as the agent's finding set.
- Emit a `FORCED_CONVERGENCE` warning to the guardrail trip log (see E.2).

**Enforcement:** The orchestrator checks `iteration_count >= MAX_ITERATIONS` before dispatching another iteration. This is a hard stop — no override flag. The existing convergence detection still runs at each iteration; the hard cap only fires if convergence detection fails to stabilize.

### A.3 Agent Output Size Limit

**Problem:** An agent could produce an extremely large output that consumes disproportionate budget.

**Design:**

- `validate-output.sh` gains a `--max-findings <N>` flag (default: 50).
- If an agent produces more than `N` findings in a single iteration, validation fails with `MAX_FINDINGS_EXCEEDED`.
- `MAX_FINDINGS_EXCEEDED` is treated as a validation failure under the existing retry model in `self-refinement.md` Step 4 (max 2 retries, fresh agent on retry). The re-prompt includes instructions to prioritize and reduce to the top `N` findings by severity.
- If the agent exceeds the limit after all retries, take the first `N` findings sorted by severity (Critical > Important > Minor) and proceed.

---

## B. Cost / Runaway Protection

### B.1 Hard Budget Enforcement

**Problem:** `track-budget.sh` tracks consumption and reports `exceeded: true`, but nothing acts on it. The orchestrator continues dispatching iterations.

**Design:**

- The orchestrator checks budget status after every agent iteration via `track-budget.sh status`.
- If `exceeded: true`:
  - **During self-refinement:** Skip remaining iterations for this agent. Use current findings.
  - **During challenge round:** Complete the current challenge exchange but skip subsequent rounds.
  - **During remediation:** Stop after current fix. Do not start new fixes.
- Emit `BUDGET_EXCEEDED` to the guardrail trip log with `consumed` and `total` values.
- The `--budget` flag already allows overriding the default. No additional override needed — if the user sets a budget, it's enforced.

### B.2 Agent-Level Budget Cap

**Problem:** One runaway agent could consume the entire budget, starving other specialists.

**Design:**

- Each agent is allocated a per-agent budget: `ceil(total_budget / num_agents * 1.5)`.
- The 1.5x multiplier provides headroom — not all agents will use their full share.
- Per-agent caps are computed once at review start using the initial agent count and are **not** recalculated if agents are excluded due to validation failures.
- `track-budget.sh` gains a `--per-agent-cap <tokens>` flag and a `--agent <name>` parameter on the `add` action.
- The script maintains per-agent consumption in the budget state file (keyed by agent name).
- When `track-budget.sh add <char_count> --agent SEC` is called, it checks both the global budget and the per-agent cap for `SEC`.
- If the per-agent cap is exceeded, the response includes `agent_exceeded: true`.
- The orchestrator skips remaining iterations for that agent.
- Emit `AGENT_BUDGET_EXCEEDED` to the guardrail trip log.

**Formula:**

```
per_agent_cap = ceil(total_budget / num_active_agents * 1.5)
```

**Example:** 500K budget, 5 agents → 150K per agent cap.

### B.3 Pre-flight Budget Estimate Gate

**Problem:** The user starts a review that will obviously exceed budget (e.g., 1000 files with `--thorough`).

**Design:**

- Before starting Phase 1, run `track-budget.sh estimate <num_agents> <estimated_code_tokens> <configured_iterations> [num_work_items] [impact_graph_tokens] [reference_tokens]`.
- `estimated_code_tokens` is derived from the review scope: `wc -c <scope_files> | tail -1` divided by 4 (chars-to-tokens approximation).
- If the estimate exceeds 90% of the budget, warn the user:
  ```
  Estimated token usage: ~620K (budget: 500K). Proceed anyway? [y/N]
  ```
- If the estimate exceeds 150% of the budget, recommend `--quick` or a narrower scope.
- The `--force` flag skips only the file count ceiling (existing behavior). The pre-flight budget estimate gate has no bypass — users who want to exceed their budget should set a higher `--budget` value explicitly. This avoids conflating two independent safety checks.

---

## C. Safety / Scope Guardrails

### C.1 Remediation Dry-Run (`--fix --dry-run`)

**Problem:** `--fix` modifies code, creates branches, and can draft Jira tickets. Users want to preview before committing.

**Design:**

- `--fix --dry-run` runs the full remediation pipeline but writes nothing:
  - Classification: computed and displayed, not persisted.
  - Jira tickets: drafted and displayed, not created.
  - Code patches: generated and displayed as unified diffs, not applied.
  - Branches/PRs: described but not created.
- Output format: standard report with an additional `## Remediation Preview` section containing the above.
- No user confirmation gates fire in dry-run (nothing to confirm).
- Audit log entries in dry-run mode are prefixed with `[DRY-RUN]` and included in the Remediation Preview section rather than the Audit Log section.

### C.2 Remediation Scope Lock

**Problem:** A fix for a finding in `src/auth.ts` could generate a patch that also modifies `src/database.ts`, expanding beyond the review scope.

**Design:**

- During `--fix`, the orchestrator provides the agent with the review scope (same file list as A.1).
- Code patches are validated: every file in the patch must be in the review scope.
- If a patch touches out-of-scope files:
  - Warn the user: `Patch for SEC-001 modifies out-of-scope file src/database.ts. Apply anyway? [y/N]`
  - The user can approve per-patch or skip.
- The `--strict-scope` flag auto-rejects out-of-scope patches without prompting.

### C.3 External Action Audit Log

**Problem:** `--fix` and `--triage` can interact with GitHub and Jira. There's no record of what was done.

**Design:**

- Create `protocols/audit-log.md` defining the log format.
- Every external action is appended to the review's audit trail:
  ```
  [2026-03-26T14:32:00Z] ACTION: github.create_branch branch=fix/SEC-001 base=main
  [2026-03-26T14:32:15Z] ACTION: github.create_pr title="Fix SEC-001: SQL injection" branch=fix/SEC-001
  [2026-03-26T14:33:00Z] ACTION: jira.create_issue project=RHOAI type=Bug summary="SQL injection in auth handler"
  ```
- The audit trail is included in the final report under `## Audit Log`.
- When `--save` is used, the audit log is also written to `docs/reviews/.audit-log` (append mode).
- In degraded single-agent mode, audit logging is advisory (the agent is instructed to log but enforcement isn't possible).

### C.4 Destructive Action Blocklist

**Problem:** An agent generating a fix could produce destructive commands (rm -rf, DROP TABLE, force-push).

**Design:**

- Destructive pattern checking runs at two points:
  1. `validate-output.sh --check-fixes` scans the `Recommended fix:` field in findings during Phase 1/2 output validation.
  2. During Phase 5 (remediation), the orchestrator scans generated code diffs/patches against the same pattern list before applying.
- Patterns checked:
  - Shell: `rm -rf`, `rm -r /`, `> /dev/`, `mkfs`, `dd if=`
  - Git: `push --force`, `push -f`, `reset --hard`, `clean -fd`
  - SQL: `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, `DELETE FROM` (without WHERE)
- Pattern list stored in `protocols/destructive-patterns.txt` (one regex per line, easy to extend).
- Matches trigger `DESTRUCTIVE_PATTERN` warning. The orchestrator flags to the user before applying.
- This is a heuristic check, not a security boundary. It catches obvious cases.

---

## D. Output Quality Guardrails

### D.1 Minimum Evidence Threshold

**Problem:** Findings with trivial evidence ("this looks wrong") provide no value and waste challenge round time.

**Design:**

- `validate-output.sh` checks the `Evidence:` field length.
- If evidence < 100 characters and severity is Critical or Important:
  - Validation passes but emits `WEAK_EVIDENCE` warning.
  - The orchestrator auto-demotes the finding to Minor.
  - Emit `EVIDENCE_DEMOTED` to the guardrail trip log.
- Threshold: 100 non-whitespace characters (not raw length — prevents padding with spaces/newlines). A file path + function name + brief explanation is ~80 chars minimum for meaningful evidence.
- Known limitation: a pasted code snippet with no prose analysis can pass the length check. This is accepted as a tradeoff — the code-path verification gate already requires traced execution paths, which is a stronger quality signal.
- This check runs after code-path verification, so it catches findings that passed verification but have minimal substance.

### D.2 Severity Inflation Detection

**Problem:** A specialist that marks 80% of findings as Critical is either reviewing catastrophically broken code or inflating severity.

**Design:**

- After each specialist completes self-refinement, the orchestrator calculates the severity distribution.
- If > 50% of findings from any single specialist are Critical:
  - Emit `SEVERITY_INFLATION` warning to the guardrail trip log.
  - Include the warning in the specialist's challenge round context so other specialists can scrutinize severity.
- This is informational, not enforcement. The challenge round is the natural correction mechanism.
- Thresholds (OR conditions — either triggers the warning):
  - `SEVERITY_INFLATION_CRITICAL_THRESHOLD`: > 50% of findings are Critical
  - `SEVERITY_INFLATION_COMBINED_THRESHOLD`: > 80% of findings are Critical + Important combined (at least some findings should be Minor)

### D.3 Challenge Dismissal Metrics

**Problem:** No visibility into how many findings survive the challenge round vs. how many are dismissed.

**Design:**

- The resolution phase already tracks which findings survive. Add metrics to the report:
  ```
  ## Review Metrics
  - Findings raised: 23
  - Findings surviving challenge: 14 (61%)
  - Findings dismissed: 9 (39%)
  - Consensus rate: 85% (findings where all challengers agreed)
  - Forced convergence: 0 agents
  ```
- No enforcement action — this is observability for the user to calibrate trust.

---

## E. Audit & Observability

### E.1 Review Configuration Block

**Problem:** Reports don't record what parameters were used, making it hard to reproduce or compare reviews.

**Note:** The existing report template has a machine-readable metadata block (HTML comment with timestamp, commit_sha, content_hash) for integrity verification. This new section is a human-readable summary of review parameters, distinct from the existing integrity metadata.

**Design:**

- Add a configuration block to the report template (after executive summary, before findings):
  ```markdown
  ## Review Configuration
  - **Date:** 2026-03-26T14:30:00Z
  - **Scope:** src/auth/, src/middleware/ (12 files, 2,847 lines)
  - **Specialists:** SEC, PERF, QUAL, CORR, ARCH
  - **Mode flags:** --thorough --diff --save
  - **Iterations:** SEC: 3, PERF: 2, QUAL: 2, CORR: 3, ARCH: 2
  - **Budget:** 412K / 800K consumed (51%)
  - **Reference modules:** 4 loaded (owasp-top10-2025, agentic-ai-security, asvs-5-highlights, k8s-security)
  ```
- The orchestrator populates this from `track-budget.sh` data and its own state.

### E.2 Guardrail Trip Log

**Problem:** When guardrails fire, the evidence is scattered across stderr and orchestrator state. No unified record.

**Design:**

- The orchestrator maintains a guardrail trip log as an in-memory list during the review.
- Each entry:
  ```
  {timestamp, guardrail_id, agent (optional), details}
  ```
- Guardrail IDs: `SCOPE_VIOLATION`, `FORCED_CONVERGENCE`, `MAX_FINDINGS_EXCEEDED`, `BUDGET_EXCEEDED`, `AGENT_BUDGET_EXCEEDED`, `DESTRUCTIVE_PATTERN`, `WEAK_EVIDENCE`, `EVIDENCE_DEMOTED`, `SEVERITY_INFLATION`
- At report generation, the log is rendered as a `## Guardrails Triggered` section:
  ```markdown
  ## Guardrails Triggered
  - `FORCED_CONVERGENCE` — PERF agent did not converge after 4 iterations
  - `EVIDENCE_DEMOTED` — SEC-007 demoted from Important to Minor (evidence: 62 non-whitespace chars)
  - `SEVERITY_INFLATION` — SEC agent: 6/8 findings (75%) marked Critical
  ```
- If no guardrails fired: `## Guardrails Triggered\n\nNone.`

---

## F. Implementation Surface

### F.1 Modified Files

| File | Changes |
|------|---------|
| `scripts/validate-output.sh` | Add `--scope`, `--max-findings`, `--check-fixes` flags |
| `scripts/track-budget.sh` | Add `--per-agent-cap` flag, hard enforcement return codes |
| `templates/report-template.md` | Add Review Configuration (after Section 1), Review Metrics + Guardrails Triggered + Audit Log (after Section 9, before metadata block) |
| `SKILL.md` | Add iteration hard cap, budget enforcement checks, guardrail log collection, pre-flight gate |
| `phases/self-refinement.md` | Reference MAX_ITERATIONS hard cap alongside existing iteration targets |
| `phases/challenge-round.md` | Reference budget enforcement check between exchanges |
| `phases/remediation.md` | Add dry-run mode, scope lock, audit logging, destructive pattern check |
| `protocols/guardrails.md` | New — guardrail definitions, thresholds, behavior |
| `protocols/audit-log.md` | New — audit log format for external actions |
| `protocols/destructive-patterns.txt` | New — regex patterns for destructive command detection |

### F.2 New Flags

| Flag | Scope | Effect |
|------|-------|--------|
| `--strict-scope` | Review | Reject (not demote) out-of-scope findings and patches |
| `--fix --dry-run` | Remediation | Preview remediation without writing anything |

### F.3 Constants

| Constant | Default | `--quick` | `--thorough` |
|----------|---------|-----------|--------------|
| `MAX_ITERATIONS` | 4 | 2 | 4 |
| `MAX_FINDINGS_PER_AGENT` | 50 | 50 | 50 |
| `MIN_EVIDENCE_CHARS` | 100 | 100 | 100 |
| `SEVERITY_INFLATION_CRITICAL_THRESHOLD` | 50% | 50% | 50% |
| `SEVERITY_INFLATION_COMBINED_THRESHOLD` | 80% | 80% | 80% |
| `AGENT_BUDGET_MULTIPLIER` | 1.5 | 1.5 | 1.5 |
| `PRE_FLIGHT_WARN_THRESHOLD` | 90% | 90% | 90% |
| `PRE_FLIGHT_RECOMMEND_THRESHOLD` | 150% | 150% | 150% |

### F.4 Degraded Mode Behavior

In single-agent (Cursor/AGENTS.md) mode. Shell availability is determined by whether the platform supports shell execution (e.g., Bash tool in Claude Code, terminal access in Cursor). Scripts that require shell are enforced when available, advisory otherwise.

| Guardrail | Behavior |
|-----------|----------|
| Scope confinement | Advisory — agent instructed to stay in scope |
| Iteration hard cap | Enforced if shell available, advisory otherwise |
| Budget enforcement | Enforced if shell available, advisory otherwise |
| Agent-level budget cap | N/A (single agent) |
| Output size limit | Enforced if shell available |
| Remediation scope lock | Advisory |
| Audit log | Advisory — agent instructed to log actions |
| Destructive pattern check | Enforced if shell available |
| Evidence threshold | Enforced if shell available |
| Severity inflation | Advisory |
