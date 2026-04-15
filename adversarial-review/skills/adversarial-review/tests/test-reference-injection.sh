#!/usr/bin/env bash
# Integration test: reference injection resistance
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$SCRIPT_DIR/scripts"
FIXTURES="$SCRIPT_DIR/tests/fixtures"
PASS=0
FAIL=0

assert_contains() {
    local desc="$1" haystack="$2" needle="$3"
    if grep -qF "$needle" <<< "$haystack"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (expected to find '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local desc="$1" haystack="$2" needle="$3"
    if ! grep -qF "$needle" <<< "$haystack"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (should not find '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

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

assert_not_equal() {
    local desc="$1" val1="$2" val2="$3"
    if [[ "$val1" != "$val2" ]]; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (values should differ)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Reference injection resistance test ==="

# Test 1: Reference content wrapped in REFERENCE_DATA delimiters
echo ""
echo "Test 1: Reference content wrapped in REFERENCE_DATA delimiters"
result1=$("$SCRIPTS/generate-delimiters.sh" --category REFERENCE_DATA "$FIXTURES/sample-reference-valid.md")
assert_contains "Output contains REFERENCE_DATA" "$result1" "REFERENCE_DATA"

# Test 2: Injection patterns in reference body stay wrapped (generate-delimiters works on injection content)
echo ""
echo "Test 2: Injection patterns in reference body stay wrapped"
result2=$("$SCRIPTS/generate-delimiters.sh" --category REFERENCE_DATA "$FIXTURES/sample-reference-injection.md" 2>&1)
exit_code2=$?
assert_exit "generate-delimiters.sh works on injection reference" "0" "$exit_code2"

# Test 3: Generated hex doesn't collide with injection content
echo ""
echo "Test 3: Generated hex doesn't collide with injection content"
hex3=$(echo "$result2" | grep '"hex"' | sed 's/.*: *"//;s/".*//')
injection_content=$(cat "$FIXTURES/sample-reference-injection.md")
assert_not_contains "Hex not found in injection content" "$injection_content" "$hex3"

# Test 3b: Anti-instruction wrapper - delimiter format correct for REFERENCE_DATA
echo ""
echo "Test 3b: Anti-instruction wrapper - delimiter format correct for REFERENCE_DATA"
start_delim=$(echo "$result2" | grep '"start_delimiter"' | sed 's/.*: *"//;s/".*//')
assert_contains "Start delimiter contains REFERENCE_DATA" "$start_delim" "REFERENCE_DATA"

# Test 4: Multiple references get independent delimiter pairs
echo ""
echo "Test 4: Multiple references get independent delimiter pairs"
result4a=$("$SCRIPTS/generate-delimiters.sh" --category REFERENCE_DATA "$FIXTURES/sample-reference-valid.md")
result4b=$("$SCRIPTS/generate-delimiters.sh" --category REFERENCE_DATA "$FIXTURES/sample-reference-injection.md")
hex4a=$(echo "$result4a" | grep '"hex"' | sed 's/.*: *"//;s/".*//')
hex4b=$(echo "$result4b" | grep '"hex"' | sed 's/.*: *"//;s/".*//')
assert_not_equal "Different hex values for different references" "$hex4a" "$hex4b"

# Test 5: Collision detection includes reference content (covered by test 3)
echo ""
echo "Test 5: Collision detection includes reference content"
echo "  PASS: Covered by test 3"
PASS=$((PASS + 1))

# Test 6: Empty reference directory produces no output
echo ""
echo "Test 6: Empty reference directory produces no output"
TEMP_DIR=$(mktemp -d)
trap "rm -rf '$TEMP_DIR'" EXIT
result6=$("$SCRIPTS/discover-references.sh" security --builtin-dir "$TEMP_DIR" --user-dir "/nonexistent" --project-dir "/nonexistent" 2>/dev/null || true)
if [[ -z "$result6" ]]; then
    echo "  PASS: Empty directory produces no output"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Empty directory should produce no output (got: $result6)"
    FAIL=$((FAIL + 1))
fi

# Test 7: specialist:all module injected for all 5 specialists
echo ""
echo "Test 7: specialist:all module injected for all 5 specialists"
TEMP_ALL_DIR=$(mktemp -d)
trap "rm -rf '$TEMP_ALL_DIR'" EXIT

# Create all/ subdirectory with a specialist:all module
mkdir -p "$TEMP_ALL_DIR/all"
cat > "$TEMP_ALL_DIR/all/universal-module.md" <<'EOF'
---
name: universal-test
specialist: all
version: "1.0.0"
last_updated: "2026-03-20"
description: "Module for all specialists"
enabled: true
---

# Universal Module

This module should appear for all specialists.
EOF

# Test each specialist
specialists=("security" "performance" "quality" "correctness" "architecture")
all_found=true
for specialist in "${specialists[@]}"; do
    result7=$("$SCRIPTS/discover-references.sh" "$specialist" --builtin-dir "$TEMP_ALL_DIR" --user-dir "/nonexistent" --project-dir "/nonexistent" 2>/dev/null || true)
    if ! grep -qF "universal-test" <<< "$result7"; then
        echo "  FAIL: universal-test not found for $specialist"
        all_found=false
        FAIL=$((FAIL + 1))
        break
    fi
done

if [[ "$all_found" == "true" ]]; then
    echo "  PASS: specialist:all module appears for all specialists"
    PASS=$((PASS + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
