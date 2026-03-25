#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
FIXTURES_DIR="$SCRIPT_DIR/tests/fixtures"
BUILD_IMPACT="$SCRIPTS_DIR/build-impact-graph.sh"

PASS=0
FAIL=0

assert_contains() {
    local output="$1" expected="$2" desc="$3"
    if echo "$output" | grep -q "$expected"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (expected to find '$expected')"
        FAIL=$((FAIL + 1))
    fi
}

assert_equals() {
    local actual="$1" expected="$2" desc="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (expected $expected, got $actual)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== build-impact-graph.sh tests ==="

# Test 1: Produces output with SYMBOL section
echo "Test 1: Produces output with SYMBOL section"
output=$("$BUILD_IMPACT" \
    --diff-file "$FIXTURES_DIR/sample-diff.patch" \
    --search-dir "$FIXTURES_DIR/sample-go-callers")
assert_contains "$output" "SYMBOL:" "Should contain SYMBOL: section"

# Test 2: Contains ReconcileComponent
echo "Test 2: Contains ReconcileComponent"
output=$("$BUILD_IMPACT" \
    --diff-file "$FIXTURES_DIR/sample-diff.patch" \
    --search-dir "$FIXTURES_DIR/sample-go-callers")
assert_contains "$output" "ReconcileComponent" "Should contain ReconcileComponent"

# Test 3: Finds callers
echo "Test 3: Finds callers"
output=$("$BUILD_IMPACT" \
    --diff-file "$FIXTURES_DIR/sample-diff.patch" \
    --search-dir "$FIXTURES_DIR/sample-go-callers")
assert_contains "$output" "reconcileLoop" "Should find caller reconcileLoop"
assert_contains "$output" "processComponent" "Should find caller processComponent"

# Test 4: Identifies callees
echo "Test 4: Identifies callees"
output=$("$BUILD_IMPACT" \
    --diff-file "$FIXTURES_DIR/sample-diff.patch" \
    --search-dir "$FIXTURES_DIR/sample-go-callers")
assert_contains "$output" "SetCondition" "Should find callee SetCondition"
assert_contains "$output" "ResetBaseline" "Should find callee ResetBaseline"

# Test 5: Contains IMPACT_GRAPH delimiter
echo "Test 5: Contains IMPACT_GRAPH delimiter"
output=$("$BUILD_IMPACT" \
    --diff-file "$FIXTURES_DIR/sample-diff.patch" \
    --search-dir "$FIXTURES_DIR/sample-go-callers")
assert_contains "$output" "IMPACT_GRAPH" "Should contain IMPACT_GRAPH delimiter"

# Test 6: Contains advisory disclaimer
echo "Test 6: Contains advisory disclaimer"
output=$("$BUILD_IMPACT" \
    --diff-file "$FIXTURES_DIR/sample-diff.patch" \
    --search-dir "$FIXTURES_DIR/sample-go-callers")
assert_contains "$output" "may be INCOMPLETE" "Should contain advisory disclaimer"

# Test 7: Empty diff returns exit code 2
echo "Test 7: Empty diff returns exit code 2"
empty_diff="$FIXTURES_DIR/empty.patch"
echo "" > "$empty_diff"
exit_code=0
"$BUILD_IMPACT" \
    --diff-file "$empty_diff" \
    --search-dir "$FIXTURES_DIR/sample-go-callers" > /dev/null 2>&1 || exit_code=$?
rm -f "$empty_diff"
assert_equals "$exit_code" "2" "Empty diff should return exit code 2"

# Test 8: Missing diff file returns exit code 1
echo "Test 8: Missing diff file returns exit code 1"
exit_code=0
"$BUILD_IMPACT" \
    --diff-file "$FIXTURES_DIR/nonexistent.patch" \
    --search-dir "$FIXTURES_DIR/sample-go-callers" > /dev/null 2>&1 || exit_code=$?
assert_equals "$exit_code" "1" "Missing diff file should return exit code 1"

# Test 9: --max-symbols limits output
echo "Test 9: --max-symbols limits output"
output=$("$BUILD_IMPACT" \
    --diff-file "$FIXTURES_DIR/sample-diff.patch" \
    --search-dir "$FIXTURES_DIR/sample-go-callers" \
    --max-symbols 1)
symbol_count=$(echo "$output" | grep -c "^SYMBOL:" || true)
assert_equals "$symbol_count" "1" "Should limit to 1 symbol when --max-symbols 1"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
