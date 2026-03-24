#!/usr/bin/env bash
# Extended tests covering convergence, budget exhaustion, dedup, NO_FINDINGS, and marker injection.
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

assert_contains() {
    local desc="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (expected to contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local desc="$1" needle="$2" haystack="$3"
    if ! echo "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (should not contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Extended coverage tests ==="

# --- T2: Convergence detection non-identity ---

echo ""
echo "-- Convergence detection --"

# T2a: Different files should NOT converge
"$SCRIPTS/detect-convergence.sh" "$FIXTURES/valid-finding.txt" "$FIXTURES/changed-finding.txt" >/dev/null 2>&1
assert_exit "Different findings do not converge" "1" "$?"

# T2b: Convergence diff shows added/removed correctly
result=$("$SCRIPTS/detect-convergence.sh" "$FIXTURES/valid-finding.txt" "$FIXTURES/changed-finding.txt" 2>&1 || true)
assert_contains "Non-convergence reports converged=false" '"converged": false' "$result"

# T2c: Same file converges
"$SCRIPTS/detect-convergence.sh" "$FIXTURES/valid-finding.txt" "$FIXTURES/valid-finding.txt" >/dev/null 2>&1
assert_exit "Identical findings converge" "0" "$?"

# T2d: Added findings detected
result=$("$SCRIPTS/detect-convergence.sh" "$FIXTURES/two-findings-nonoverlap.txt" "$FIXTURES/valid-finding.txt" 2>&1 || true)
assert_contains "Added findings detected" '"added"' "$result"
assert_contains "SEC-002 appears as added" 'SEC-002' "$result"

# T2e: Empty vs findings = not converged
empty_file=$(mktemp /tmp/test-empty-XXXXXX)
TEMP_FILES+=("$empty_file")
echo "" > "$empty_file"
"$SCRIPTS/detect-convergence.sh" "$FIXTURES/valid-finding.txt" "$empty_file" >/dev/null 2>&1
assert_exit "Findings vs empty does not converge" "1" "$?"

# --- T3: Budget exhaustion ---

echo ""
echo "-- Budget exhaustion --"

# T3a: Budget exceeded after adding more than limit
export BUDGET_STATE_FILE=$(mktemp /tmp/test-budget-exhaust-XXXXXX)
TEMP_FILES+=("$BUDGET_STATE_FILE")
"$SCRIPTS/track-budget.sh" init 100 >/dev/null 2>&1
result=$("$SCRIPTS/track-budget.sh" add 2000 2>&1)  # 2000 chars = 500 tokens > 100 limit
assert_contains "Budget exceeded after large add" '"exceeded": true' "$result"
assert_contains "Remaining clamped to 0" '"remaining": 0' "$result"

# T3b: Status after exhaustion
result=$("$SCRIPTS/track-budget.sh" status 2>&1)
assert_contains "Status reports exceeded" '"exceeded": true' "$result"

# T3c: Budget at exact limit
export BUDGET_STATE_FILE=$(mktemp /tmp/test-budget-exact-XXXXXX)
TEMP_FILES+=("$BUDGET_STATE_FILE")
"$SCRIPTS/track-budget.sh" init 100 >/dev/null 2>&1
result=$("$SCRIPTS/track-budget.sh" add 400 2>&1)  # 400 chars = 100 tokens = exact limit
assert_contains "Budget at exact limit shows remaining 0" '"remaining": 0' "$result"
assert_contains "Exact limit is exceeded" '"exceeded": true' "$result"

# T3d: Estimate with Phase 5 remediation overhead (no state file needed)
unset BUDGET_STATE_FILE
result=$("$SCRIPTS/track-budget.sh" estimate 3 1000 2 5 2>&1)
assert_exit "Estimate without BUDGET_STATE_FILE succeeds" "0" "$?"
assert_contains "Estimate includes Phase 5" '"phase5_remediation": 75000' "$result"

# T3e: Add/status without init fails
unset BUDGET_STATE_FILE
"$SCRIPTS/track-budget.sh" add 100 >/dev/null 2>&1
assert_exit "Add without init fails" "1" "$?"

# --- T4: Deduplication with overlapping findings ---

echo ""
echo "-- Deduplication --"

# T4a: Overlapping same-specialist findings get merged
result=$("$SCRIPTS/deduplicate.sh" "$FIXTURES/two-findings-overlap.txt" 2>&1)
assert_contains "Merged finding retains SEC-001" "SEC-001" "$result"
assert_contains "Merge annotation present" "MERGED FROM SEC-002" "$result"

# T4b: Non-overlapping findings pass through
result=$("$SCRIPTS/deduplicate.sh" "$FIXTURES/two-findings-nonoverlap.txt" 2>&1)
assert_contains "SEC-001 passes through" "SEC-001" "$result"
assert_contains "SEC-002 passes through" "SEC-002" "$result"
assert_not_contains "No merge on non-overlapping" "MERGED FROM" "$result"

# T4c: NO_FINDINGS_REPORTED handled
result=$("$SCRIPTS/deduplicate.sh" "$FIXTURES/no-findings.txt" 2>&1)
assert_contains "NO_FINDINGS_REPORTED passes through" "NO_FINDINGS_REPORTED" "$result"

# --- T5: NO_FINDINGS_REPORTED validation ---

echo ""
echo "-- NO_FINDINGS_REPORTED --"

# T5a: validate-output.sh accepts NO_FINDINGS_REPORTED
result=$("$SCRIPTS/validate-output.sh" "$FIXTURES/no-findings.txt" SEC 2>&1)
assert_exit "NO_FINDINGS_REPORTED accepted" "0" "$?"
assert_contains "Reports zero findings" '"finding_count": 0' "$result"
assert_contains "Reports zero_findings flag" '"zero_findings": true' "$result"

# --- T6: Provenance and field marker injection ---

echo ""
echo "-- Provenance/field marker injection --"

# T6a: Provenance marker in finding content is rejected
result=$("$SCRIPTS/validate-output.sh" "$FIXTURES/provenance-injection-finding.txt" SEC 2>&1 || true)
assert_contains "Provenance marker detected" "provenance marker" "$result"
assert_contains "Field isolation marker detected" "field isolation marker" "$result"

# --- T7: Partial finding ID matching ---

echo ""
echo "-- Partial finding ID --"

# T7a: Finding SEC-1 should not pick up SEC-10 content
tmpfile=$(mktemp /tmp/test-partial-id-XXXXXX)
TEMP_FILES+=("$tmpfile")
cat > "$tmpfile" << 'EOF'
Finding ID: SEC-1
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/a.py
Lines: 1-5
Title: First finding
Evidence: First evidence
Recommended fix: First fix

Finding ID: SEC-10
Specialist: Security Auditor
Severity: Minor
Confidence: Low
File: src/b.py
Lines: 10-15
Title: Tenth finding
Evidence: Tenth evidence
Recommended fix: Tenth fix
EOF

result=$("$SCRIPTS/validate-output.sh" "$tmpfile" SEC 2>&1 || true)
assert_contains "Both findings validated" '"finding_count": 2' "$result"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
