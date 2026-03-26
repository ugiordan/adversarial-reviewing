#!/usr/bin/env bash
# Tests for guardrail features in validate-output.sh and track-budget.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0; FAIL=0
AR_HOME="$SCRIPT_DIR/.."

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Create a valid finding for scope tests (multiline evidence for threshold check)
cat > "$TMPDIR/in-scope-finding.txt" << 'EOF'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/auth.ts
Lines: 10-20
Title: SQL injection in login handler
Evidence:
The function at src/auth.ts:10 directly concatenates user input into a SQL query string without parameterization. The request.body.username value flows from the Express handler through buildQuery() at src/auth.ts:15 into db.execute() at src/auth.ts:20 without any sanitization or escaping whatsoever.
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
Evidence:
The function at src/unrelated.ts:10 directly concatenates user input into a SQL query string without parameterization. The request.body.username value flows from the Express handler through buildQuery() at src/unrelated.ts:15 into db.execute() at src/unrelated.ts:20 without any sanitization or escaping whatsoever.
Recommended fix: Use parameterized queries.
EOF

# Scope file
echo "src/auth.ts" > "$TMPDIR/scope.txt"
echo "src/middleware.ts" >> "$TMPDIR/scope.txt"

echo "=== Guardrail tests: scope validation ==="

echo "Test 1: In-scope finding passes with no warnings"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/in-scope-finding.txt" SEC --scope "$TMPDIR/scope.txt" 2>&1)
if printf '%s' "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d['valid'] else 1)"; then
    pass "Valid finding with scope passes"
else
    fail "Valid finding with scope passes"
fi
if printf '%s' "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if len(d.get('warnings',[])) == 0 else 1)"; then
    pass "No warnings for in-scope finding"
else
    fail "No warnings for in-scope finding"
fi

echo ""
echo "Test 2: Out-of-scope finding gets SCOPE_VIOLATION warning"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/out-of-scope-finding.txt" SEC --scope "$TMPDIR/scope.txt" 2>&1)
if printf '%s' "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d['valid'] else 1)"; then
    pass "Out-of-scope finding still valid (warning not error)"
else
    fail "Out-of-scope finding still valid (warning not error)"
fi
if printf '%s' "$result" | grep -q 'SCOPE_VIOLATION'; then
    pass "SCOPE_VIOLATION warning present"
else
    fail "SCOPE_VIOLATION warning present"
fi

echo ""
echo "Test 3: No --scope flag = no scope checking (backward compat)"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/out-of-scope-finding.txt" SEC 2>&1)
if printf '%s' "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d['valid'] else 1)"; then
    pass "No scope flag passes without warnings"
else
    fail "No scope flag passes without warnings"
fi

echo ""
echo "=== Guardrail tests: max findings ==="

# Create output with 3 findings (multiline evidence)
cat > "$TMPDIR/many-findings.txt" << 'EOF'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/auth.ts
Lines: 10-20
Title: Issue one
Evidence:
The function at src/auth.ts:10 concatenates user input into SQL without parameterization flowing through buildQuery at line 15 and into the database layer without sanitization or escaping.
Recommended fix: Use parameterized queries.

Finding ID: SEC-002
Specialist: Security Auditor
Severity: Important
Confidence: Medium
File: src/auth.ts
Lines: 30-40
Title: Issue two
Evidence:
The session token at src/auth.ts:30 is generated using Math.random which is not cryptographically secure per ECMA-262 specification and can be predicted by an attacker.
Recommended fix: Use crypto.randomBytes.

Finding ID: SEC-003
Specialist: Security Auditor
Severity: Minor
Confidence: Low
File: src/auth.ts
Lines: 50-60
Title: Issue three
Evidence:
The error handler at src/auth.ts:50 logs the full stack trace to the response body which can leak internal paths to attackers making it easier to exploit the application.
Recommended fix: Return generic error message.
EOF

echo "Test 4: --max-findings 2 rejects output with 3 findings"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/many-findings.txt" SEC --max-findings 2 2>&1)
exit_code=$?
if [[ $exit_code -eq 1 ]]; then pass "Exit code 1 for max findings exceeded"; else fail "Exit code 1 for max findings exceeded"; fi
if printf '%s' "$result" | grep -q 'MAX_FINDINGS_EXCEEDED'; then
    pass "MAX_FINDINGS_EXCEEDED in errors"
else
    fail "MAX_FINDINGS_EXCEEDED in errors"
fi

echo "Test 5: --max-findings 5 accepts output with 3 findings"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/many-findings.txt" SEC --max-findings 5 2>&1)
exit_code=$?
if [[ $exit_code -eq 0 ]]; then pass "Exit code 0 for within limit"; else fail "Exit code 0 for within limit"; fi

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
Evidence:
Looks wrong.
Recommended fix: Fix it.
EOF

echo "Test 6: Critical finding with short evidence gets WEAK_EVIDENCE warning"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/weak-evidence.txt" SEC 2>&1)
if printf '%s' "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d['valid'] else 1)"; then
    pass "Validation passes (warning not error)"
else
    fail "Validation passes (warning not error)"
fi
if printf '%s' "$result" | grep -q 'WEAK_EVIDENCE'; then
    pass "WEAK_EVIDENCE warning present"
else
    fail "WEAK_EVIDENCE warning present"
fi

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
Evidence:
The build process at src/auth.ts:10 creates temporary files in /tmp that are never cleaned up, verified by tracing the createTempFile call at line 15 through the build pipeline execution path.
Recommended fix: rm -rf /tmp/build-* after each build cycle to clean up temporary artifacts.
EOF

echo "Test 7: --check-fixes detects destructive patterns"
result=$(bash "$AR_HOME/scripts/validate-output.sh" "$TMPDIR/destructive-fix.txt" SEC --check-fixes 2>&1)
if printf '%s' "$result" | grep -q 'DESTRUCTIVE_PATTERN'; then
    pass "DESTRUCTIVE_PATTERN warning present"
else
    fail "DESTRUCTIVE_PATTERN warning present"
fi

echo ""
echo "=== Guardrail tests: per-agent budget ==="

echo "Test 8: track-budget.sh add with --agent tracks per-agent consumption"
export BUDGET_STATE_FILE="$TMPDIR/budget-agent.json"
bash "$AR_HOME/scripts/track-budget.sh" init 500000 > /dev/null
result=$(bash "$AR_HOME/scripts/track-budget.sh" add 100000 --agent SEC --per-agent-cap 50000 2>&1)
if printf '%s' "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if not d.get('agent_exceeded', False) else 1)"; then
    pass "Per-agent add succeeds"
else
    fail "Per-agent add succeeds"
fi

echo "Test 9: Agent exceeding per-agent cap reports agent_exceeded"
# SEC already has 25K tokens (100K chars / 4). Adding 200K chars = 50K tokens. Total = 75K > 50K cap.
result=$(bash "$AR_HOME/scripts/track-budget.sh" add 200000 --agent SEC --per-agent-cap 50000 2>&1)
if printf '%s' "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d.get('agent_exceeded', False) else 1)"; then
    pass "Agent exceeded reported"
else
    fail "Agent exceeded reported"
fi

echo "Test 10: Different agents tracked independently"
result=$(bash "$AR_HOME/scripts/track-budget.sh" add 50000 --agent PERF --per-agent-cap 50000 2>&1)
if printf '%s' "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if not d.get('agent_exceeded', False) else 1)"; then
    pass "PERF agent not exceeded"
else
    fail "PERF agent not exceeded"
fi
unset BUDGET_STATE_FILE

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [[ $FAIL -gt 0 ]]; then exit 1; fi
