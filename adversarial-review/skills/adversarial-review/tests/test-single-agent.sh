#!/usr/bin/env bash
# Integration test: single-agent mode shell script pipeline
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$SCRIPT_DIR/scripts"
FIXTURES="$SCRIPT_DIR/tests/fixtures"
PASS=0
FAIL=0
TEMP_FILES=()

cleanup() {
    for f in "${TEMP_FILES[@]}"; do
        rm -f "$f"
    done
}
trap cleanup EXIT

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

echo "=== Single-agent pipeline integration test ==="

# Test 1: generate-delimiters produces valid JSON
result=$("$SCRIPTS/generate-delimiters.sh" "$FIXTURES/sample-code.py")
exit_code=$?
assert_exit "generate-delimiters.sh produces output" "0" "$exit_code"

# Verify JSON contains required keys
for key in start_delimiter end_delimiter field_start field_end hex field_hex; do
    if echo "$result" | grep -q "\"$key\""; then
        echo "  PASS: JSON contains key '$key'"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: JSON missing key '$key'"
        FAIL=$((FAIL + 1))
    fi
done

# Test 2: validate-output validates correctly
"$SCRIPTS/validate-output.sh" "$FIXTURES/valid-finding.txt" SEC >/dev/null 2>&1
assert_exit "validate-output.sh accepts valid finding" "0" "$?"

# Test 3: convergence detection works
"$SCRIPTS/detect-convergence.sh" "$FIXTURES/valid-finding.txt" "$FIXTURES/valid-finding.txt" >/dev/null 2>&1
assert_exit "detect-convergence.sh detects convergence" "0" "$?"

# Test 4: budget tracking pipeline — capture state_file from init JSON output
init_result=$("$SCRIPTS/track-budget.sh" init 500000 2>&1)
assert_exit "track-budget.sh init succeeds" "0" "$?"
export BUDGET_STATE_FILE=$(echo "$init_result" | python3 -c "import json,sys; print(json.load(sys.stdin)['state_file'])")
TEMP_FILES+=("$BUDGET_STATE_FILE")

budget_result=$("$SCRIPTS/track-budget.sh" add "$FIXTURES/sample-code.py")
assert_exit "track-budget.sh add succeeds" "0" "$?"

if echo "$budget_result" | grep -q '"exceeded": false'; then
    echo "  PASS: Budget not exceeded after small file"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Budget should not be exceeded"
    FAIL=$((FAIL + 1))
fi

unset BUDGET_STATE_FILE

# Test 5: deduplicate passes through single finding unchanged
dedup_result=$("$SCRIPTS/deduplicate.sh" "$FIXTURES/valid-finding.txt")
assert_exit "deduplicate.sh succeeds" "0" "$?"

if echo "$dedup_result" | grep -q "SEC-001"; then
    echo "  PASS: Single finding passes through dedup unchanged"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Finding should pass through dedup"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
