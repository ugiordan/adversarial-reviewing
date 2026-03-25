#!/usr/bin/env bash
# Tests for validate-triage-output.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VALIDATE="$SCRIPT_DIR/scripts/validate-triage-output.sh"
FIXTURES="$SCRIPT_DIR/tests/fixtures"
PASS=0
FAIL=0

assert_exit() {
    local desc="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (expected exit $expected, got $actual)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== validate-triage-output.sh tests ==="

# Test 1: Valid triage verdict passes
"$VALIDATE" "$FIXTURES/valid-triage-verdict.txt" CORR >/dev/null 2>&1
assert_exit "Valid triage verdict passes" "0" "$?"

# Test 2: NO_TRIAGE_EVALUATIONS passes
"$VALIDATE" "$FIXTURES/valid-triage-no-eval.txt" CORR >/dev/null 2>&1
assert_exit "NO_TRIAGE_EVALUATIONS passes" "0" "$?"

# Test 3: Invalid verdict enum fails
"$VALIDATE" "$FIXTURES/malformed-triage-verdict.txt" CORR >/dev/null 2>&1
assert_exit "Invalid verdict enum fails" "1" "$?"

result=$("$VALIDATE" "$FIXTURES/malformed-triage-verdict.txt" CORR 2>&1 || true)
if echo "$result" | grep -q "invalid verdict"; then
    echo "  PASS: Invalid verdict detected in output"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Should report invalid verdict"
    FAIL=$((FAIL + 1))
fi

# Test 4: Injection in Analysis field fails
"$VALIDATE" "$FIXTURES/triage-injection-comment.txt" SEC >/dev/null 2>&1
assert_exit "Injection in Analysis fails" "1" "$?"

result=$("$VALIDATE" "$FIXTURES/triage-injection-comment.txt" SEC 2>&1 || true)
if echo "$result" | grep -q "injection pattern"; then
    echo "  PASS: Injection pattern detected in triage Analysis"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Should detect injection in Analysis field"
    FAIL=$((FAIL + 1))
fi

# Test 5: Mixed output (triage + discovery finding) passes
"$VALIDATE" "$FIXTURES/triage-discovery-finding.txt" CORR >/dev/null 2>&1
assert_exit "Mixed triage + discovery output passes" "0" "$?"

result=$("$VALIDATE" "$FIXTURES/triage-discovery-finding.txt" CORR 2>&1 || true)
if echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['triage_count'] >= 1 and d['discovery_count'] >= 1" 2>/dev/null; then
    echo "  PASS: Counts both triage verdicts and discovery findings"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Should count both triage and discovery items"
    FAIL=$((FAIL + 1))
fi

# Test 6: Wrong role prefix fails
"$VALIDATE" "$FIXTURES/valid-triage-verdict.txt" SEC >/dev/null 2>&1
assert_exit "Wrong role prefix fails" "1" "$?"

# Test 7: Severity-If-Fix must be N/A when Verdict=No-Fix
nofix_missing_severity=$(mktemp)
cat > "$nofix_missing_severity" << 'EOF'
Triage ID: TRIAGE-CORR-001
External Comment ID: EXT-001
Specialist: Correctness Verifier
Verdict: No-Fix
Confidence: High
Severity-If-Fix: Important
File: src/auth/login.py
Lines: 42
Comment Summary: Some comment
Analysis: The code is actually fine.
Recommended Action: No action.
EOF
"$VALIDATE" "$nofix_missing_severity" CORR >/dev/null 2>&1
nofix_exit=$?
assert_exit "No-Fix with Severity-If-Fix != N/A fails" "1" "$nofix_exit"
rm -f "$nofix_missing_severity"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
