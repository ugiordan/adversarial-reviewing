# Guardrails Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add enforceable guardrails for agent behavior, cost control, safety, output quality, and observability across the adversarial-review tool.

**Architecture:** Guardrails are layered onto existing scripts (`validate-output.sh`, `track-budget.sh`) via new flags, plus new protocol documents and report template sections. The orchestrator (SKILL.md) gains enforcement logic that checks guardrail state after every agent iteration.

**Tech Stack:** Bash (scripts), Python 3 (embedded for JSON), Markdown (protocols, templates, phase docs)

**Spec:** `docs/specs/2026-03-26-guardrails-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `protocols/guardrails.md` | Guardrail definitions, constants, thresholds, orchestrator behavior |
| `protocols/audit-log.md` | External action audit log format |
| `protocols/destructive-patterns.txt` | Regex patterns for destructive command detection |
| `tests/test-guardrails.sh` | Tests for all guardrail features (scope, evidence, budget, destructive) |

### Modified Files

| File | Change |
|------|--------|
| `scripts/validate-output.sh` | Add `--scope`, `--max-findings`, `--check-fixes` flags; add `warnings` to JSON output |
| `scripts/track-budget.sh` | Add `--agent <name>` and `--per-agent-cap <tokens>` to `add` action; per-agent state |
| `templates/report-template.md` | Add Review Configuration, Review Metrics, Guardrails Triggered, Audit Log sections |
| `phases/self-refinement.md` | Reference MAX_ITERATIONS hard cap |
| `phases/challenge-round.md` | Reference budget enforcement check between exchanges |
| `phases/remediation.md` | Add dry-run mode, scope lock, audit logging, destructive pattern check |
| `SKILL.md` | Add iteration hard cap, budget enforcement, guardrail log collection, pre-flight gate, new flags |

---

### Task 1: Create guardrails protocol document

**Files:**
- Create: `protocols/guardrails.md`

- [ ] **Step 1: Write the guardrails protocol**

```markdown
# Guardrails Protocol

## Purpose

Defines enforceable guardrails that the orchestrator checks programmatically during review execution. Each guardrail has a unique ID, threshold, enforcement behavior, and degraded-mode fallback.

## Constants

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

## Guardrail Definitions

### SCOPE_VIOLATION

- **Trigger:** Finding references a file not in the review scope file.
- **Check:** `validate-output.sh --scope <file-list>`
- **Default action:** Demote to Minor severity, append `[out-of-scope]` to title.
- **Strict mode (`--strict-scope`):** Reject the finding entirely.
- **Scope file:** Generated during Step 2 (Scope Resolution). One repo-relative path per line. In `--diff` mode, includes only changed files — impact graph files remain out of scope.

### FORCED_CONVERGENCE

- **Trigger:** Agent reaches `MAX_ITERATIONS` without converging.
- **Check:** Orchestrator checks `iteration_count >= MAX_ITERATIONS` before dispatching.
- **Action:** Force-stop, use last iteration's output.

### MAX_FINDINGS_EXCEEDED

- **Trigger:** Agent output contains more than `MAX_FINDINGS_PER_AGENT` findings.
- **Check:** `validate-output.sh --max-findings <N>`
- **Action:** Treated as validation failure (existing retry model, max 2 retries). After all retries, take first N findings sorted by severity.

### BUDGET_EXCEEDED

- **Trigger:** Global budget exhausted.
- **Check:** `track-budget.sh status` after every iteration.
- **Action:** Skip remaining iterations (self-refinement), complete current exchange (challenge), stop after current fix (remediation).

### AGENT_BUDGET_EXCEEDED

- **Trigger:** Single agent exceeds per-agent cap.
- **Check:** `track-budget.sh add <chars> --agent <name>` returns `agent_exceeded: true`.
- **Action:** Skip remaining iterations for that agent.
- **Formula:** `per_agent_cap = ceil(total_budget / num_active_agents * 1.5)`

### WEAK_EVIDENCE / EVIDENCE_DEMOTED

- **Trigger:** Evidence field has < `MIN_EVIDENCE_CHARS` non-whitespace characters AND severity is Critical or Important.
- **Check:** `validate-output.sh` (always checked).
- **Action:** Warning emitted. Orchestrator auto-demotes to Minor.

### SEVERITY_INFLATION

- **Trigger:** > 50% of a specialist's findings are Critical, OR > 80% are Critical + Important.
- **Check:** Orchestrator calculates after self-refinement completes.
- **Action:** Informational warning. Included in challenge round context.

### DESTRUCTIVE_PATTERN

- **Trigger:** Recommended fix or generated patch matches a destructive command pattern.
- **Check:** `validate-output.sh --check-fixes` (Phase 1/2) + orchestrator patch scan (Phase 5).
- **Action:** Warning. Orchestrator flags to user before applying.

## Guardrail Trip Log

The orchestrator maintains a list of guardrail events during the review. Each entry:

```
{timestamp, guardrail_id, agent (optional), details}
```

Rendered in the report as `## Guardrails Triggered`. If no guardrails fired: "None."

## Degraded Mode

In single-agent mode (Cursor/AGENTS.md), shell-dependent guardrails are enforced when shell is available, advisory otherwise. Shell availability = platform supports shell execution (Bash tool, terminal access).

| Guardrail | Multi-agent | Single-agent |
|-----------|------------|--------------|
| Scope confinement | Enforced | Advisory |
| Iteration hard cap | Enforced | Enforced if shell |
| Budget enforcement | Enforced | Enforced if shell |
| Agent-level budget cap | Enforced | N/A |
| Output size limit | Enforced | Enforced if shell |
| Remediation scope lock | Enforced | Advisory |
| Audit log | Enforced | Advisory |
| Destructive pattern check | Enforced | Enforced if shell |
| Evidence threshold | Enforced | Enforced if shell |
| Severity inflation | Informational | Advisory |
```

- [ ] **Step 2: Commit**

```bash
git add protocols/guardrails.md
git commit -m "docs: add guardrails protocol with constants and definitions"
```

---

### Task 2: Create audit log protocol and destructive patterns file

**Files:**
- Create: `protocols/audit-log.md`
- Create: `protocols/destructive-patterns.txt`

- [ ] **Step 1: Write audit log protocol**

```markdown
# Audit Log Protocol

## Purpose

Records all external actions taken during `--fix` and `--triage` modes for accountability and reproducibility.

## Format

Each entry is a single line:

```
[<ISO-8601-timestamp>] ACTION: <service>.<operation> <key=value pairs>
```

### Services and Operations

| Service | Operations |
|---------|-----------|
| `github` | `create_branch`, `create_pr`, `push`, `add_comment`, `close_pr` |
| `jira` | `create_issue`, `update_issue`, `add_comment`, `transition` |
| `git` | `checkout`, `commit`, `worktree_add`, `worktree_remove` |

### Example

```
[2026-03-26T14:32:00Z] ACTION: github.create_branch branch=fix/SEC-001 base=main
[2026-03-26T14:32:15Z] ACTION: github.create_pr title="Fix SEC-001" branch=fix/SEC-001
[2026-03-26T14:33:00Z] ACTION: jira.create_issue project=RHOAI type=Bug summary="SQL injection"
```

## Dry-Run Mode

When `--fix --dry-run` is active, entries are prefixed with `[DRY-RUN]`:

```
[DRY-RUN] [2026-03-26T14:32:00Z] ACTION: github.create_branch branch=fix/SEC-001 base=main
```

Dry-run entries appear in the `## Remediation Preview` section, not `## Audit Log`.

## Persistence

- Always included in the final report under `## Audit Log`.
- When `--save` is used, also appended to `docs/reviews/.audit-log`.
```

- [ ] **Step 2: Write destructive patterns file**

```
# Destructive command patterns (one regex per line)
# Used by validate-output.sh --check-fixes and orchestrator patch scanning
# Lines starting with # are comments

# Shell destructive commands
rm\s+-rf\b
rm\s+-r\s+/
>\s*/dev/
\bmkfs\b
\bdd\s+if=

# Git destructive commands
push\s+--force\b
push\s+-f\b
reset\s+--hard\b
clean\s+-fd\b

# SQL destructive commands
# Note: patterns are matched case-insensitively via grep -iE
DROP\s+TABLE\b
DROP\s+DATABASE\b
TRUNCATE\s+
DELETE\s+FROM\s+\w+\s*$
```

- [ ] **Step 3: Commit**

```bash
git add protocols/audit-log.md protocols/destructive-patterns.txt
git commit -m "docs: add audit log protocol and destructive patterns blocklist"
```

---

### Task 3: Add warnings array and --scope flag to validate-output.sh

**Files:**
- Modify: `scripts/validate-output.sh`
- Test: `tests/test-guardrails.sh`

- [ ] **Step 1: Write failing tests for scope validation and warnings**

Create `tests/test-guardrails.sh`:

```bash
#!/usr/bin/env bash
# Tests for guardrail features in validate-output.sh and track-budget.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0; FAIL=0
AR_HOME="$SCRIPT_DIR/.."

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
check() { if eval "$2"; then pass "$1"; else fail "$1"; fi; }

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Create a valid finding for scope tests
cat > "$TMPDIR/in-scope-finding.txt" << 'EOF'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/auth.ts
Lines: 10-20
Title: SQL injection in login handler
Evidence: The function at src/auth.ts:10 directly concatenates user input into a SQL query string without parameterization. The request.body.username value flows from the Express handler through buildQuery() at src/auth.ts:15 into db.execute() at src/auth.ts:20 without any sanitization.
Recommended fix: Use parameterized queries instead of string concatenation.
EOF

cat > "$TMPDIR/out-of-scope-finding.txt" << 'EOF'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/unrelated.ts
Lines: 10-20
Title: SQL injection in unrelated handler
Evidence: The function at src/unrelated.ts:10 directly concatenates user input into a SQL query string without parameterization. The request.body.username value flows from the Express handler through buildQuery() at src/unrelated.ts:15 into db.execute() at src/unrelated.ts:20 without any sanitization.
Recommended fix: Use parameterized queries.
EOF

# Scope file
echo "src/auth.ts" > "$TMPDIR/scope.txt"
echo "src/middleware.ts" >> "$TMPDIR/scope.txt"

echo "=== Guardrail tests: scope validation ==="

echo "Test 1: In-scope finding passes with no warnings"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/in-scope-finding.txt" SEC --scope "$TMPDIR/scope.txt" 2>&1)
check "Valid finding with scope passes" "echo "$result" | python3 -c \"import json,sys; d=json.load(sys.stdin); exit(0 if d['valid'] else 1)\""
check "No warnings for in-scope finding" "echo "$result" | python3 -c \"import json,sys; d=json.load(sys.stdin); exit(0 if len(d.get('warnings',[])) == 0 else 1)\""

echo ""
echo "Test 2: Out-of-scope finding gets SCOPE_VIOLATION warning"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/out-of-scope-finding.txt" SEC --scope "$TMPDIR/scope.txt" 2>&1)
check "Out-of-scope finding still valid (warning not error)" "echo "$result" | python3 -c \"import json,sys; d=json.load(sys.stdin); exit(0 if d['valid'] else 1)\""
check "SCOPE_VIOLATION warning present" "echo "$result" | grep -q 'SCOPE_VIOLATION'"

echo ""
echo "Test 3: No --scope flag = no scope checking (backward compat)"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/out-of-scope-finding.txt" SEC 2>&1)
check "No scope flag passes without warnings" "echo "$result" | python3 -c \"import json,sys; d=json.load(sys.stdin); exit(0 if d['valid'] else 1)\""

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [[ $FAIL -gt 0 ]]; then exit 1; fi
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bash tests/test-guardrails.sh`
Expected: FAIL — `--scope` flag not yet supported.

- [ ] **Step 3: Add --scope flag, warnings array, and --max-findings to validate-output.sh**

Modify `scripts/validate-output.sh`:

1. After the `ROLE_PREFIX` parsing (line 16), add argument parsing for `--scope`, `--max-findings`, and `--check-fixes`:

```bash
SCOPE_FILE=""
MAX_FINDINGS=0
CHECK_FIXES=false

# Parse optional flags after required positional args
shift 2  # past OUTPUT_FILE and ROLE_PREFIX
while [[ $# -gt 0 ]]; do
    case "$1" in
        --scope) SCOPE_FILE="${2:?--scope requires a file path}"; shift 2 ;;
        --max-findings) MAX_FINDINGS="${2:?--max-findings requires a number}"; shift 2 ;;
        --check-fixes) CHECK_FIXES=true; shift ;;
        *) echo "{\"error\": \"Unknown flag: $1\"}" >&2; exit 2 ;;
    esac
done
```

2. Add a `WARNINGS=()` array alongside `ERRORS=()`.

3. After the finding loop, if `SCOPE_FILE` is set, check each finding's `File:` field:

```bash
if [[ -n "$SCOPE_FILE" && -f "$SCOPE_FILE" ]]; then
    while IFS= read -r fid; do
        [[ -z "$fid" ]] && continue
        block=$(awk -v target="Finding ID: $fid" '
            index($0, target) == 1 && length($0) == length(target) {found=1; print; next}
            index($0, target) == 1 && substr($0, length(target)+1, 1) !~ /[0-9]/ {found=1; print; next}
            found && /^Finding ID: [A-Z]+-[0-9]+/ {exit}
            found {print}
        ' <<< "$content" | head -50)
        file_val=$(extract_field "File:" "$block")
        if [[ -n "$file_val" ]] && ! grep -qxF "$file_val" "$SCOPE_FILE"; then
            WARNINGS+=("SCOPE_VIOLATION: File '$file_val' not in review scope (finding $fid)")
        fi
    done <<< "$finding_ids"
fi
```

4. Add evidence length check (non-whitespace chars):

```bash
while IFS= read -r fid; do
    [[ -z "$fid" ]] && continue
    # ... existing block extraction ...
    evidence_nows=$(echo "$evidence" | tr -d '[:space:]')
    severity=$(extract_field "Severity:" "$block")
    if [[ ${#evidence_nows} -lt 100 ]] && [[ "$severity" == "Critical" || "$severity" == "Important" ]]; then
        WARNINGS+=("WEAK_EVIDENCE: Finding $fid has ${#evidence_nows} non-whitespace chars in evidence (min 100 for $severity)")
    fi
done <<< "$finding_ids"
```

5. Add `--max-findings` check after counting:

```bash
if [[ $MAX_FINDINGS -gt 0 && $FINDING_COUNT -gt $MAX_FINDINGS ]]; then
    ERRORS+=("MAX_FINDINGS_EXCEEDED: $FINDING_COUNT findings exceed limit of $MAX_FINDINGS")
fi
```

6. Add `--check-fixes` destructive pattern scanning:

```bash
if [[ "$CHECK_FIXES" == "true" && -f "$SCRIPT_DIR_VALIDATE/../protocols/destructive-patterns.txt" ]]; then
    patterns_file="$SCRIPT_DIR_VALIDATE/../protocols/destructive-patterns.txt"
    while IFS= read -r fid; do
        [[ -z "$fid" ]] && continue
        block=$(...)  # same extraction
        fix=$(awk '/^Recommended [Ff]ix:/,/^$|^Finding ID:/' <<< "$block" | tail -n +2)
        while IFS= read -r pattern; do
            [[ "$pattern" =~ ^# ]] && continue
            [[ -z "$pattern" ]] && continue
            if echo "$fix" | grep -qiE "$pattern"; then
                WARNINGS+=("DESTRUCTIVE_PATTERN: Finding $fid recommended fix matches pattern '$pattern'")
            fi
        done < "$patterns_file"
    done <<< "$finding_ids"
fi
```

7. Update JSON output to include warnings (use stdin-based passing for safety, consistent with existing error output pattern):

```bash
if [[ ${#ERRORS[@]} -eq 0 ]]; then
    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        python3 -c "
import json, sys
warnings = sys.stdin.read().splitlines()
print(json.dumps({'valid': True, 'errors': [], 'warnings': warnings, 'finding_count': int(sys.argv[1])}))
" "$FINDING_COUNT" < <(printf '%s\n' "${WARNINGS[@]}")
    else
        python3 -c "import json; print(json.dumps({'valid': True, 'errors': [], 'finding_count': int('$FINDING_COUNT')}))"
    fi
    exit 0
else
    # Include warnings alongside errors if any exist
    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        combined=$(printf '%s\n' "${ERRORS[@]}" "---SEPARATOR---" "${WARNINGS[@]}")
        python3 -c "
import json, sys
lines = sys.stdin.read().split('\n')
sep = lines.index('---SEPARATOR---')
errors, warnings = lines[:sep], lines[sep+1:]
print(json.dumps({'valid': False, 'errors': errors, 'warnings': warnings, 'finding_count': int(sys.argv[1])}))
" "$FINDING_COUNT" <<< "$combined"
    else
        errors_json=\$(python3 -c "
import json, sys
errors = sys.stdin.read().splitlines()
print(json.dumps(errors))
" < <(printf '%s\n' "\${ERRORS[@]}"))
        echo "{\"valid\": false, \"errors\": \$errors_json, \"finding_count\": \$FINDING_COUNT}"
    fi
    exit 1
fi
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bash tests/test-guardrails.sh`
Expected: PASS

The test file also includes tests for max-findings, evidence threshold, and destructive patterns (Tests 4-7). These are all implemented in Step 3 above.

```bash
echo ""
echo "=== Guardrail tests: max findings ==="

# Create output with 3 findings
cat > "$TMPDIR/many-findings.txt" << 'EOF'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/auth.ts
Lines: 10-20
Title: Issue one
Evidence: The function at src/auth.ts:10 concatenates user input into SQL without parameterization flowing through buildQuery at line 15.
Recommended fix: Use parameterized queries.

Finding ID: SEC-002
Specialist: Security Auditor
Severity: Important
Confidence: Medium
File: src/auth.ts
Lines: 30-40
Title: Issue two
Evidence: The session token at src/auth.ts:30 is generated using Math.random which is not cryptographically secure per ECMA-262 specification.
Recommended fix: Use crypto.randomBytes.

Finding ID: SEC-003
Specialist: Security Auditor
Severity: Minor
Confidence: Low
File: src/auth.ts
Lines: 50-60
Title: Issue three
Evidence: The error handler at src/auth.ts:50 logs the full stack trace to the response body which can leak internal paths to attackers.
Recommended fix: Return generic error message.
EOF

echo "Test 4: --max-findings 2 rejects output with 3 findings"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/many-findings.txt" SEC --max-findings 2 2>&1)
exit_code=$?
check "Exit code 1 for max findings exceeded" "[[ $exit_code -eq 1 ]]"
check "MAX_FINDINGS_EXCEEDED in errors" "echo \"$result\" | grep -q 'MAX_FINDINGS_EXCEEDED'"

echo "Test 5: --max-findings 5 accepts output with 3 findings"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/many-findings.txt" SEC --max-findings 5 2>&1)
exit_code=$?
check "Exit code 0 for within limit" "[[ $exit_code -eq 0 ]]"

echo ""
echo "=== Guardrail tests: evidence threshold ==="

cat > "$TMPDIR/weak-evidence.txt" << 'EOF'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/auth.ts
Lines: 10-20
Title: SQL injection
Evidence: Looks wrong.
Recommended fix: Fix it.
EOF

echo "Test 6: Critical finding with short evidence gets WEAK_EVIDENCE warning"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/weak-evidence.txt" SEC 2>&1)
check "Validation passes (warning not error)" "echo \"$result\" | python3 -c \"import json,sys; d=json.load(sys.stdin); exit(0 if d['valid'] else 1)\""
check "WEAK_EVIDENCE warning present" "echo \"$result\" | grep -q 'WEAK_EVIDENCE'"

echo ""
echo "=== Guardrail tests: destructive patterns ==="

cat > "$TMPDIR/destructive-fix.txt" << 'EOF'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/auth.ts
Lines: 10-20
Title: Leftover temp files
Evidence: The build process at src/auth.ts:10 creates temporary files in /tmp that are never cleaned up, verified by tracing the createTempFile call at line 15.
Recommended fix: rm -rf /tmp/build-* after each build cycle to clean up temporary artifacts.
EOF

echo "Test 7: --check-fixes detects destructive patterns"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/destructive-fix.txt" SEC --check-fixes 2>&1)
check "DESTRUCTIVE_PATTERN warning present" "echo \"$result\" | grep -q 'DESTRUCTIVE_PATTERN'"
```

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `bash tests/run-all-tests.sh`
Expected: All existing tests + new guardrail tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/validate-output.sh tests/test-guardrails.sh
git commit -m "feat: add --scope, --max-findings, --check-fixes to validate-output.sh

Adds warnings array to JSON output (backward compatible).
Implements scope confinement (A.1), output size limit (A.3),
evidence threshold (D.1), and destructive pattern check (C.4)."
```

---

### Task 4: Add per-agent budget tracking to track-budget.sh

**Files:**
- Modify: `scripts/track-budget.sh`
- Modify: `tests/test-guardrails.sh`

- [ ] **Step 1: Write failing tests for per-agent budget tracking**

Append to `tests/test-guardrails.sh`:

```bash
echo ""
echo "=== Guardrail tests: per-agent budget ==="

echo "Test 8: track-budget.sh add with --agent tracks per-agent consumption"
export BUDGET_STATE_FILE="$TMPDIR/budget-agent.json"
bash "$AR_HOME/scripts/track-budget.sh" init 500000 > /dev/null
result=$(bash "$AR_HOME/scripts/track-budget.sh" add 100000 --agent SEC --per-agent-cap 50000 2>&1)
check "Per-agent add succeeds" "echo \"$result\" | python3 -c \"import json,sys; d=json.load(sys.stdin); exit(0 if not d.get('agent_exceeded', False) else 1)\""

echo "Test 9: Agent exceeding per-agent cap reports agent_exceeded"
# SEC already has 25K tokens (100K chars / 4). Adding 200K chars = 50K tokens. Total = 75K > 50K cap.
result=$(bash "$AR_HOME/scripts/track-budget.sh" add 200000 --agent SEC --per-agent-cap 50000 2>&1)
check "Agent exceeded reported" "echo \"$result\" | python3 -c \"import json,sys; d=json.load(sys.stdin); exit(0 if d.get('agent_exceeded', False) else 1)\""

echo "Test 10: Different agents tracked independently"
result=$(bash "$AR_HOME/scripts/track-budget.sh" add 50000 --agent PERF --per-agent-cap 50000 2>&1)
check "PERF agent not exceeded" "echo \"$result\" | python3 -c \"import json,sys; d=json.load(sys.stdin); exit(0 if not d.get('agent_exceeded', False) else 1)\""
unset BUDGET_STATE_FILE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bash tests/test-guardrails.sh`
Expected: Tests 8-10 FAIL — `--agent` flag not supported.

- [ ] **Step 3: Add --agent and --per-agent-cap to track-budget.sh add action**

In the `add)` case (line 66), after the existing positional arg parsing:

1. Parse `--agent <name>` and `--per-agent-cap <tokens>` from remaining args.
2. When `--agent` is provided:
   - Read per-agent state from the state file (JSON key `agents.<name>.consumed`, default 0).
   - Add tokens to both global consumed and per-agent consumed.
   - Write updated per-agent state back.
   - If per-agent consumed > per-agent-cap, set `agent_exceeded: true` in output.
3. The state file JSON structure becomes:
   ```json
   {"limit": 500000, "consumed": 150000, "agents": {"SEC": {"consumed": 100000}, "PERF": {"consumed": 50000}}}
   ```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bash tests/test-guardrails.sh`
Expected: All PASS

- [ ] **Step 5: Run full test suite for regressions**

Run: `bash tests/run-all-tests.sh`
Expected: All pass — existing track-budget tests still work (no --agent = old behavior).

- [ ] **Step 6: Commit**

```bash
git add scripts/track-budget.sh tests/test-guardrails.sh
git commit -m "feat: add per-agent budget tracking to track-budget.sh

--agent <name> and --per-agent-cap <tokens> flags on add action.
Per-agent consumption tracked in state file, agent_exceeded flag in output."
```

---

### Task 5: Update report template with new sections

**Files:**
- Modify: `templates/report-template.md`

- [ ] **Step 1: Add Review Configuration section after Section 1**

After the Executive Summary section, add:

```markdown
## Section 1.5: Review Configuration

Human-readable summary of review parameters. Distinct from the machine-readable metadata block at the end of the report.

```
## Review Configuration
- **Date:** YYYY-MM-DDTHH:MM:SSZ
- **Scope:** [directories/files] ([N] files, [N] lines)
- **Specialists:** [list of active specialist tags]
- **Mode flags:** [flags used]
- **Iterations:** [TAG: N, TAG: N, ...]
- **Budget:** [used]K / [total]K consumed ([N]%)
- **Reference modules:** [N] loaded ([list])
```

- [ ] **Step 2: Add Review Metrics, Guardrails Triggered, and Audit Log after Section 9**

Before the Metadata Block section, add:

```markdown
## Section 10b: Review Metrics

Challenge round statistics for calibrating trust in results.

```
## Review Metrics
- Findings raised: [N]
- Findings surviving challenge: [N] ([N]%)
- Findings dismissed: [N] ([N]%)
- Consensus rate: [N]% (findings where all challengers agreed)
- Forced convergence: [N] agents
```

## Section 10c: Guardrails Triggered

Record of all guardrails that activated during the review. If none: "None."

```
## Guardrails Triggered
- `GUARDRAIL_ID` — [agent] [details]
```

## Section 10d: Audit Log

External actions taken during --fix and --triage. If no external actions: "No external actions taken." See `protocols/audit-log.md` for format.

```
## Audit Log
[timestamp] ACTION: service.operation key=value
```
```

- [ ] **Step 3: Update section count and metadata block note**

Update line 5: "The final report contains 9 sections" → "The final report contains up to 13 sections" and note that Section 10 (Change Impact) and Sections 10b-10d are conditional.

- [ ] **Step 4: Commit**

```bash
git add templates/report-template.md
git commit -m "docs: add Review Configuration, Metrics, Guardrails, Audit Log to report template"
```

---

### Task 6: Update self-refinement.md with hard cap reference

**Files:**
- Modify: `phases/self-refinement.md`

- [ ] **Step 1: Add MAX_ITERATIONS hard cap to Step 6**

In the iteration rules table (line 112), add a row after "Maximum iterations":

```markdown
| Safety hard cap | `MAX_ITERATIONS` (default 4, quick 2, thorough 4) — absolute ceiling. If convergence detection fails to stabilize within this many iterations, force-stop and emit `FORCED_CONVERGENCE` guardrail. See `protocols/guardrails.md`. |
```

- [ ] **Step 2: Add guardrails.md to References**

Add to the References list at the bottom:

```markdown
- `protocols/guardrails.md` — guardrail definitions, constants, enforcement behavior
```

- [ ] **Step 3: Commit**

```bash
git add phases/self-refinement.md
git commit -m "docs: reference MAX_ITERATIONS hard cap in self-refinement phase"
```

---

### Task 7: Update challenge-round.md with budget enforcement

**Files:**
- Modify: `phases/challenge-round.md`

- [ ] **Step 1: Add budget check between exchanges**

After Step 4 (Broadcast and Collect Responses), add:

```markdown
### Step 4.5: Budget Enforcement Check

After each challenge exchange, check budget status:

```bash
scripts/track-budget.sh status
```

If `exceeded: true`, complete the current exchange but skip subsequent rounds. Emit `BUDGET_EXCEEDED` to the guardrail trip log. Proceed to Phase 3 with findings as-is.
```

- [ ] **Step 2: Add guardrails.md to References**

- [ ] **Step 3: Commit**

```bash
git add phases/challenge-round.md
git commit -m "docs: add budget enforcement check to challenge round"
```

---

### Task 8: Update remediation.md with dry-run, scope lock, audit, destructive check

**Files:**
- Modify: `phases/remediation.md`

- [ ] **Step 1: Read the full remediation.md**

Read the file to understand the current structure.

- [ ] **Step 2: Add dry-run mode section**

After the Prerequisites section, add:

```markdown
## Dry-Run Mode (`--fix --dry-run`)

When `--dry-run` is specified alongside `--fix`, the full remediation pipeline runs but writes nothing:

- Classification: computed and displayed, not persisted.
- Jira tickets: drafted and displayed, not created.
- Code patches: generated and displayed as unified diffs, not applied.
- Branches/PRs: described but not created.
- No user confirmation gates fire (nothing to confirm).
- Audit log entries are prefixed with `[DRY-RUN]` (see `protocols/audit-log.md`).

Output appears in the `## Remediation Preview` report section.
```

- [ ] **Step 3: Add scope lock and destructive check to fix implementation steps**

In the step where patches are applied, add:

```markdown
**Scope Lock:** Before applying any patch, verify all files in the patch are in the review scope (same file list used for `validate-output.sh --scope`). If a patch touches out-of-scope files:
- Default: warn user per-patch. User can approve or skip.
- `--strict-scope`: auto-reject out-of-scope patches.

**Destructive Pattern Check:** Before applying any patch, scan the diff against `protocols/destructive-patterns.txt`. If matched, flag `DESTRUCTIVE_PATTERN` to user before applying.
```

- [ ] **Step 4: Add audit logging note**

Add note to each step that performs an external action:

```markdown
> **Audit:** Log this action to the audit trail. See `protocols/audit-log.md`.
```

- [ ] **Step 5: Commit**

```bash
git add phases/remediation.md
git commit -m "docs: add dry-run, scope lock, audit logging, destructive check to remediation"
```

---

### Task 9: Update SKILL.md with guardrail enforcement

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Read current SKILL.md**

- [ ] **Step 2: Add --strict-scope and --fix --dry-run to flags table**

In the Mode Flags table, add:

```markdown
| `--strict-scope` | Reject (not demote) out-of-scope findings and patches |
| `--fix --dry-run` | Preview remediation without writing anything |
```

**Note:** `--strict-scope` is an orchestrator-level flag, not a `validate-output.sh` flag. The validation script always emits scope violations as warnings; the orchestrator decides whether to demote or reject based on `--strict-scope`.

- [ ] **Step 3: Add pre-flight budget gate**

In the orchestrator procedure, after scope resolution and before Phase 1 dispatch, add:

```markdown
### Pre-flight Budget Gate

Run `scripts/track-budget.sh estimate <num_agents> <estimated_code_tokens> <configured_iterations>`. Capture the `estimated_tokens` value from the JSON output. Compare against the budget:

- If `estimated_tokens > budget * 0.9`: warn the user with the estimate and budget values. Ask to proceed.
- If `estimated_tokens > budget * 1.5`: recommend `--quick` or a narrower scope.
- Users who want to proceed should set a higher `--budget` value. There is no bypass flag for this gate.
```

- [ ] **Step 4: Add iteration hard cap and budget enforcement to agent dispatch**

In the self-refinement dispatch loop, add:

```markdown
Before dispatching each iteration, check:
1. `iteration_count < MAX_ITERATIONS` (see `protocols/guardrails.md` for values by profile)
2. Budget not exceeded via `track-budget.sh status`
3. Agent-level budget not exceeded

If any check fails, stop iterating for this agent and use last output.
```

- [ ] **Step 5: Add guardrail trip log collection**

Add instruction for the orchestrator to maintain an in-memory guardrail trip log and render it in the report.

- [ ] **Step 6: Add severity inflation check**

After all specialists complete self-refinement, add:

```markdown
### Severity Inflation Check

For each specialist, compute the severity distribution. If > 50% Critical or > 80% Critical + Important, emit `SEVERITY_INFLATION` to the guardrail trip log. Include the warning in the specialist's challenge round context.
```

- [ ] **Step 7: Add scope file generation**

In Step 2 (Scope Resolution), add:

```markdown
Write the list of in-scope files (one repo-relative path per line) to a temporary file. Pass this file to `validate-output.sh --scope <file>` during validation. In `--diff` mode, only changed files are in scope — impact graph files are context-only.
```

- [ ] **Step 8: Commit**

```bash
git add SKILL.md
git commit -m "feat: add guardrail enforcement to SKILL.md orchestrator

Pre-flight budget gate, iteration hard cap, per-agent budget cap,
severity inflation check, scope file generation, guardrail trip log."
```

---

### Task 10: Update README.md, AGENTS.md, and cursor rules

**Note:** This task operates from the **repo root** (`adversarial-review/`), not the skill root. All paths here are repo-relative.

**Files:**
- Modify: `README.md` (repo root)
- Modify: `AGENTS.md` (repo root)
- Modify: `.cursor/rules/adversarial-review.mdc`

- [ ] **Step 1: Add guardrails section to README.md**

After the Reference Modules section, add:

```markdown
## Guardrails

The review enforces programmatic guardrails across agent behavior, cost, safety, and output quality:

| Guardrail | Effect |
|-----------|--------|
| Scope confinement | Findings on files outside the review target are demoted or rejected |
| Iteration hard cap | Agents force-stopped after MAX_ITERATIONS (prevents infinite loops) |
| Budget enforcement | Review stops when token budget is exhausted |
| Per-agent budget cap | No single agent can consume > 150% of its fair share |
| Evidence threshold | Findings with < 100 chars of evidence auto-demoted to Minor |
| Destructive pattern check | Recommended fixes scanned for rm -rf, DROP TABLE, force-push, etc. |
| Severity inflation detection | Warning when > 50% of an agent's findings are Critical |

Use `--strict-scope` to reject (not demote) out-of-scope findings.
Use `--fix --dry-run` to preview remediation without writing anything.

See `protocols/guardrails.md` for full definitions and constants.
```

- [ ] **Step 2: Add --strict-scope and --fix --dry-run to flags in README, AGENTS, cursor rules**

Add the two new flags to the mode flags tables in all three files.

- [ ] **Step 3: Commit**

```bash
git add README.md AGENTS.md .cursor/rules/adversarial-review.mdc
git commit -m "docs: add guardrails section and new flags to README, AGENTS, cursor rules"
```

---

### Task 11: Run full test suite and final verification

**Files:**
- No new files

- [ ] **Step 1: Run full test suite**

```bash
cd adversarial-review/skills/adversarial-review && bash tests/run-all-tests.sh
```

Expected: All tests pass including new guardrail tests.

- [ ] **Step 2: Verify existing tests still pass**

Confirm 169+ existing tests plus new guardrail tests all pass.

- [ ] **Step 3: Verify all new files exist**

```bash
ls -la protocols/guardrails.md protocols/audit-log.md protocols/destructive-patterns.txt
```

- [ ] **Step 4: Verify git log shows clean commit history**

```bash
git log --oneline -15
```

- [ ] **Step 5: Done**
