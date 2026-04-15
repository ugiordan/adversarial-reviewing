#!/usr/bin/env bash
# Unit tests for validate-output.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VALIDATE="$SCRIPT_DIR/scripts/validate-output.sh"
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

echo "=== validate-output.sh tests ==="

# Test 1: Valid finding passes
"$VALIDATE" "$FIXTURES/valid-finding.txt" SEC >/dev/null 2>&1
assert_exit "Valid finding passes validation" "0" "$?"

# Test 2: Malformed finding fails (check both exit code and output)
"$VALIDATE" "$FIXTURES/malformed-finding.txt" SEC >/dev/null 2>&1
malformed_exit=$?
assert_exit "Malformed finding exits with code 1" "1" "$malformed_exit"

result=$("$VALIDATE" "$FIXTURES/malformed-finding.txt" SEC 2>&1 || true)
if echo "$result" | grep -q '"valid": false'; then
    echo "  PASS: Malformed finding fails validation"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Malformed finding should fail validation"
    FAIL=$((FAIL + 1))
fi

# Test 3: Injection finding fails (check both exit code and output)
"$VALIDATE" "$FIXTURES/injection-finding.txt" SEC >/dev/null 2>&1
inject_exit=$?
assert_exit "Injection finding exits with code 1" "1" "$inject_exit"

result=$("$VALIDATE" "$FIXTURES/injection-finding.txt" SEC 2>&1 || true)
if echo "$result" | grep -q "injection pattern"; then
    echo "  PASS: Injection patterns detected"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Should detect injection patterns"
    FAIL=$((FAIL + 1))
fi

# Test 4: Wrong role prefix fails (check both exit code and output)
"$VALIDATE" "$FIXTURES/valid-finding.txt" PERF >/dev/null 2>&1
prefix_exit=$?
assert_exit "Wrong prefix exits with code 1" "1" "$prefix_exit"

result=$("$VALIDATE" "$FIXTURES/valid-finding.txt" PERF 2>&1 || true)
if echo "$result" | grep -q "does not match"; then
    echo "  PASS: Wrong role prefix detected"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Should detect wrong role prefix"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
