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

echo "=== Challenge mode tests ==="

# Create a temp finding-ids file
CHALLENGE_IDS=$(mktemp "${TMPDIR:-/tmp}/test-challenge-ids-XXXXXXXXXX")
echo "SEC-001" > "$CHALLENGE_IDS"
echo "SEC-002" >> "$CHALLENGE_IDS"

# Test: Valid challenge response passes
# NOTE: positional args (output_file, role_prefix) must come BEFORE flags
"$VALIDATE" "$FIXTURES/valid-challenge-response.txt" SEC --mode challenge --finding-ids "$CHALLENGE_IDS" >/dev/null 2>&1
assert_exit "Valid challenge response passes" "0" "$?"

# Test: Invalid challenge response fails (bad action, unknown finding ID)
"$VALIDATE" "$FIXTURES/invalid-challenge-response.txt" SEC --mode challenge --finding-ids "$CHALLENGE_IDS" >/dev/null 2>&1
assert_exit "Invalid challenge response fails" "1" "$?"

# Test: Challenge without --finding-ids fails with usage error
"$VALIDATE" "$FIXTURES/valid-challenge-response.txt" SEC --mode challenge >/dev/null 2>&1
assert_exit "Challenge without --finding-ids exits 2" "2" "$?"

rm -f "$CHALLENGE_IDS"

echo "=== Cache path stripping tests ==="

# Create a finding with a cache path instead of repo-relative path
CACHE_PATH_FINDING=$(mktemp)
cat > "$CACHE_PATH_FINDING" <<'FINDING'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: /var/folders/xx/adversarial-review-cache-abcd1234abcd1234abcd1234abcd1234-reponame/code/src/auth/handler.go
Lines: 10-20
Title: RBAC bypass in handler
Evidence: The authentication handler at /var/folders/xx/adversarial-review-cache-abcd1234abcd1234abcd1234abcd1234-reponame/code/src/auth/handler.go:15 allows unauthenticated access through a precedence bug in the RBAC check that skips validation when system:authenticated is the role.
Recommended fix: Fix the RBAC precedence check.
FINDING

RESULT=$("$VALIDATE" "$CACHE_PATH_FINDING" SEC 2>&1) || true
# Should produce a warning about cache path stripping
if echo "$RESULT" | grep -qi "cache.*path\|stripped"; then
    echo "  PASS: cache path stripping warning emitted"
    PASS=$((PASS + 1))
else
    echo "  FAIL: no cache path stripping warning"
    FAIL=$((FAIL + 1))
fi

rm -f "$CACHE_PATH_FINDING"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
