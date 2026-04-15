#!/usr/bin/env bash
# Integration test: discover-references.sh
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

assert_contains() {
    local desc="$1" haystack="$2" needle="$3"
    if echo "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (output does not contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local desc="$1" haystack="$2" needle="$3"
    if ! echo "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (output should not contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== discover-references.sh integration test ==="

# Test 1: Discovers valid module from single directory
echo "Test 1: Discovers valid module from single directory"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
result=$("$SCRIPTS/discover-references.sh" security --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "discover-references.sh exits 0 for valid module" "0" "$exit_code"
assert_contains "Output contains module name" "$result" '"name": "test-module"'
assert_contains "Output contains specialist" "$result" '"specialist": "security"'
assert_contains "Output contains enabled true" "$result" '"enabled": true'
rm -rf "$TEMP_DIR"

# Test 2: Filters by specialist correctly
echo ""
echo "Test 2: Filters by specialist correctly"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security" "$TEMP_DIR/performance"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
cat > "$TEMP_DIR/performance/perf-module.md" <<'EOF'
---
name: perf-test
specialist: performance
version: "1.0.0"
enabled: true
---
# Performance module
EOF
result=$("$SCRIPTS/discover-references.sh" security --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
assert_contains "Security specialist includes security module" "$result" '"name": "test-module"'
assert_not_contains "Security specialist excludes performance module" "$result" '"name": "perf-test"'
rm -rf "$TEMP_DIR"

# Test 3: Skips enabled: false modules
echo ""
echo "Test 3: Skips enabled: false modules"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-disabled.md" "$TEMP_DIR/security/"
result=$("$SCRIPTS/discover-references.sh" security --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
assert_not_contains "Disabled module not in output" "$result" '"name": "disabled-module"'
rm -rf "$TEMP_DIR"

# Test 4: Skips malformed frontmatter with warning to stderr
echo ""
echo "Test 4: Skips malformed frontmatter with warning to stderr"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-malformed.md" "$TEMP_DIR/security/"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
result=$("$SCRIPTS/discover-references.sh" security --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent 2>&1)
exit_code=$?
assert_exit "Script exits 0 despite malformed file" "0" "$exit_code"
assert_contains "Valid module still discovered" "$result" '"name": "test-module"'
assert_not_contains "Malformed module not in output" "$result" '"name": "broken-module"'
rm -rf "$TEMP_DIR"

# Test 4b: Skips module with valid YAML but missing required field
echo ""
echo "Test 4b: Skips module with missing required field"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-missing-field.md" "$TEMP_DIR/security/"
stderr=$(mktemp)
result=$("$SCRIPTS/discover-references.sh" security --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent 2>"$stderr")
exit_code=$?
stderr_output=$(cat "$stderr")
assert_exit "Script exits 0 despite missing field" "0" "$exit_code"
assert_not_contains "Module with missing field not in output" "$result" '"name": "missing-specialist"'
assert_contains "Warning emitted to stderr" "$stderr_output" "missing 'specialist' field"
rm -f "$stderr"
rm -rf "$TEMP_DIR"

# Test 5: Deduplication - project overrides builtin
echo ""
echo "Test 5: Deduplication - project overrides builtin"
TEMP_DIR_BUILTIN=$(mktemp -d)
TEMP_DIR_PROJECT=$(mktemp -d)
mkdir -p "$TEMP_DIR_BUILTIN/security" "$TEMP_DIR_PROJECT/security"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR_BUILTIN/security/"
cat > "$TEMP_DIR_PROJECT/security/test-module.md" <<'EOF'
---
name: test-module
specialist: security
version: "2.0.0"
enabled: true
description: "Project override version"
---
# Project version
EOF
result=$("$SCRIPTS/discover-references.sh" security --builtin-dir "$TEMP_DIR_BUILTIN" --user-dir /nonexistent --project-dir "$TEMP_DIR_PROJECT")
assert_contains "Project version overrides builtin" "$result" '"version": "2.0.0"'
assert_contains "Project description present" "$result" '"description": "Project override version"'
# Count occurrences - should only have one module
count=$(echo "$result" | grep -c '"name": "test-module"' || true)
if [[ "$count" == "1" ]]; then
    echo "  PASS: Only one test-module in output (deduplication works)"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Found $count instances of test-module (expected 1)"
    FAIL=$((FAIL + 1))
fi
rm -rf "$TEMP_DIR_BUILTIN" "$TEMP_DIR_PROJECT"

# Test 6: Same name + different specialist = two distinct modules
echo ""
echo "Test 6: Same name + different specialist = two distinct modules"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security" "$TEMP_DIR/performance"
cat > "$TEMP_DIR/security/common-checks.md" <<'EOF'
---
name: common-checks
specialist: security
version: "1.0.0"
enabled: true
---
# Security checks
EOF
cat > "$TEMP_DIR/performance/common-checks.md" <<'EOF'
---
name: common-checks
specialist: performance
version: "1.0.0"
enabled: true
---
# Performance checks
EOF
result=$("$SCRIPTS/discover-references.sh" --list-all --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
count=$(echo "$result" | grep -c '"name": "common-checks"' || true)
if [[ "$count" == "2" ]]; then
    echo "  PASS: Two distinct modules with same name but different specialist"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Found $count instances of common-checks (expected 2)"
    FAIL=$((FAIL + 1))
fi
assert_contains "Security specialist present" "$result" '"specialist": "security"'
assert_contains "Performance specialist present" "$result" '"specialist": "performance"'
rm -rf "$TEMP_DIR"

# Test 7: --check-staleness emits warning for stale modules
echo ""
echo "Test 7: --check-staleness emits warning for stale modules"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-stale.md" "$TEMP_DIR/security/"
stderr=$(mktemp)
result=$("$SCRIPTS/discover-references.sh" security --check-staleness --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent 2>"$stderr")
exit_code=$?
stderr_output=$(cat "$stderr")
assert_exit "Script exits 0 with stale module" "0" "$exit_code"
assert_contains "Module discovered despite being stale" "$result" '"name": "stale-module"'
assert_contains "Stale field is true" "$result" '"stale": true'
assert_contains "Warning emitted to stderr" "$stderr_output" "is stale"
rm -f "$stderr"
rm -rf "$TEMP_DIR"

# Test 8: --check-staleness no warning for fresh modules
echo ""
echo "Test 8: --check-staleness no warning for fresh modules"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
stderr=$(mktemp)
result=$("$SCRIPTS/discover-references.sh" security --check-staleness --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent 2>"$stderr")
exit_code=$?
stderr_output=$(cat "$stderr")
assert_exit "Script exits 0 with fresh module" "0" "$exit_code"
assert_contains "Fresh module discovered" "$result" '"name": "test-module"'
assert_contains "Stale field is false" "$result" '"stale": false'
assert_not_contains "No staleness warning for fresh module" "$stderr_output" "is stale"
rm -f "$stderr"
rm -rf "$TEMP_DIR"

# Test 9: --token-count returns token estimate
echo ""
echo "Test 9: --token-count returns token estimate"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
result=$("$SCRIPTS/discover-references.sh" security --token-count --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0 with token counting" "0" "$exit_code"
assert_contains "Tokens field present in output" "$result" '"tokens":'
# Verify it's a number greater than 0
if echo "$result" | grep -q '"tokens": [1-9][0-9]*'; then
    echo "  PASS: Token count is a positive number"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Token count not a positive number"
    FAIL=$((FAIL + 1))
fi
rm -rf "$TEMP_DIR"

# Test 10: --list-all shows modules across all specialists
echo ""
echo "Test 10: --list-all shows modules across all specialists"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security" "$TEMP_DIR/performance" "$TEMP_DIR/quality"
cat > "$TEMP_DIR/security/sec-mod.md" <<'EOF'
---
name: sec-mod
specialist: security
version: "1.0.0"
enabled: true
---
# Security
EOF
cat > "$TEMP_DIR/performance/perf-mod.md" <<'EOF'
---
name: perf-mod
specialist: performance
version: "1.0.0"
enabled: true
---
# Performance
EOF
cat > "$TEMP_DIR/quality/qual-mod.md" <<'EOF'
---
name: qual-mod
specialist: quality
version: "1.0.0"
enabled: true
---
# Quality
EOF
result=$("$SCRIPTS/discover-references.sh" --list-all --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0 with --list-all" "0" "$exit_code"
assert_contains "Security module in list-all" "$result" '"name": "sec-mod"'
assert_contains "Performance module in list-all" "$result" '"name": "perf-mod"'
assert_contains "Quality module in list-all" "$result" '"name": "qual-mod"'
rm -rf "$TEMP_DIR"

# Test 11: specialist: all modules included for every specialist
echo ""
echo "Test 11: specialist: all modules included for every specialist"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security" "$TEMP_DIR/all"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
cat > "$TEMP_DIR/all/universal-checks.md" <<'EOF'
---
name: universal-checks
specialist: all
version: "1.0.0"
enabled: true
---
# Universal checks
EOF
# Also test root-level specialist: all
cat > "$TEMP_DIR/root-checks.md" <<'EOF'
---
name: root-checks
specialist: all
version: "1.0.0"
enabled: true
---
# Root-level all checks
EOF
result=$("$SCRIPTS/discover-references.sh" security --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0" "0" "$exit_code"
assert_contains "Security specialist module present" "$result" '"name": "test-module"'
assert_contains "Universal module included for security specialist" "$result" '"name": "universal-checks"'
assert_contains "Root-level all module included" "$result" '"name": "root-checks"'

# Test with performance specialist
result_perf=$("$SCRIPTS/discover-references.sh" performance --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
assert_contains "Universal module included for performance specialist" "$result_perf" '"name": "universal-checks"'
assert_contains "Root-level all module included for performance" "$result_perf" '"name": "root-checks"'
assert_not_contains "Security module not included for performance" "$result_perf" '"name": "test-module"'
rm -rf "$TEMP_DIR"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
