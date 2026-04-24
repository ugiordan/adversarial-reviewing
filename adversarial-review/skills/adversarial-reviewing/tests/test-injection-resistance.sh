#!/usr/bin/env bash
# Integration test: injection resistance
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$SCRIPT_DIR/scripts"
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

echo "=== Injection resistance integration test ==="

# Test 1: generate-delimiters works on injection-laden code
result=$("$SCRIPTS/generate-delimiters.sh" "$FIXTURES/sample-code-with-injection.py")
assert_exit "generate-delimiters.sh works on injection code" "0" "$?"

# Test 2: Generated hex doesn't match the fake delimiter in the code
hex=$(echo "$result" | grep '"hex"' | sed 's/.*: *"//;s/".*//')
if [[ "$hex" != "deadbeef01234567" ]]; then
    echo "  PASS: Generated hex differs from fake delimiter"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Generated hex should not match fake delimiter"
    FAIL=$((FAIL + 1))
fi

# Test 3: Injection finding is rejected by validation
"$SCRIPTS/validate-output.sh" "$FIXTURES/injection-finding.txt" SEC >/dev/null 2>&1
inject_exit=$?
assert_exit "validate-output.sh rejects injection finding" "1" "$inject_exit"

# Test 4: Valid finding still passes despite injection code existing
"$SCRIPTS/validate-output.sh" "$FIXTURES/valid-finding.txt" SEC >/dev/null 2>&1
assert_exit "validate-output.sh still accepts valid finding" "0" "$?"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
