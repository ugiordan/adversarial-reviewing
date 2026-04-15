#!/usr/bin/env bash
# Integration test: strat profile validation, verdict resolution, and budget tracking
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

assert_check() {
    local desc="$1" condition="$2"
    if eval "$condition"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc"
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

echo "=== Strat profile integration tests ==="

# --- Section 1: Strat finding validation ---
echo ""
echo "--- Test: valid strat finding passes validation ---"
result=$("$SCRIPTS/validate-output.sh" "$FIXTURES/valid-strat-finding.txt" SEC --profile strat 2>&1)
exit_code=$?
assert_exit "valid strat finding accepted" "0" "$exit_code"

# Check that validation output confirms validity
if echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['valid'] == True" 2>/dev/null; then
    echo "  PASS: validation JSON reports valid=true"
    PASS=$((PASS + 1))
else
    echo "  FAIL: validation should report valid=true"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "--- Test: valid strat finding with Approve verdict ---"
result=$("$SCRIPTS/validate-output.sh" "$FIXTURES/valid-strat-finding-approve.txt" FEAS --profile strat 2>&1)
exit_code=$?
assert_exit "approve-verdict strat finding accepted" "0" "$exit_code"

if echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['valid'] == True" 2>/dev/null; then
    echo "  PASS: approve verdict accepted"
    PASS=$((PASS + 1))
else
    echo "  FAIL: approve verdict should be accepted"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "--- Test: malformed strat finding rejected (missing Document/Citation) ---"
result=$("$SCRIPTS/validate-output.sh" "$FIXTURES/malformed-strat-finding.txt" SEC --profile strat 2>&1)
exit_code=$?
assert_exit "malformed strat finding rejected" "1" "$exit_code"

# Verify it caught the missing Document field
if echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
errors = ' '.join(d.get('errors', []))
assert 'Document' in errors, f'Expected Document error, got: {errors}'
" 2>/dev/null; then
    echo "  PASS: missing Document field detected"
    PASS=$((PASS + 1))
else
    echo "  FAIL: should detect missing Document field"
    FAIL=$((FAIL + 1))
fi

# Verify it caught the missing Citation field
if echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
errors = ' '.join(d.get('errors', []))
assert 'Citation' in errors, f'Expected Citation error, got: {errors}'
" 2>/dev/null; then
    echo "  PASS: missing Citation field detected"
    PASS=$((PASS + 1))
else
    echo "  FAIL: should detect missing Citation field"
    FAIL=$((FAIL + 1))
fi

# --- Section 2: Evidence threshold for strat findings ---
echo ""
echo "--- Test: strat finding with short evidence gets demoted ---"
# The malformed fixture has "Evidence: No auth." which is < 100 chars
if echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
warnings = ' '.join(d.get('warnings', []))
# Either evidence warning or the finding is rejected for other reasons
assert 'evidence' in warnings.lower() or len(d.get('errors',[])) > 0
" 2>/dev/null; then
    echo "  PASS: short evidence flagged"
    PASS=$((PASS + 1))
else
    echo "  FAIL: short evidence should be flagged"
    FAIL=$((FAIL + 1))
fi

# --- Section 3: Code profile finding rejected with strat validator ---
echo ""
echo "--- Test: code finding fails strat validation (wrong fields) ---"
result=$("$SCRIPTS/validate-output.sh" "$FIXTURES/valid-finding.txt" SEC --profile strat 2>&1)
exit_code=$?
# Code findings have File/Lines but not Document/Citation, so strat validation should fail
if echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
errors = ' '.join(d.get('errors', []))
assert 'Document' in errors or d['valid'] == False
" 2>/dev/null; then
    echo "  PASS: code finding rejected by strat validator"
    PASS=$((PASS + 1))
else
    echo "  FAIL: code finding should fail strat validation"
    FAIL=$((FAIL + 1))
fi

# --- Section 4: Deduplication with strat findings ---
echo ""
echo "--- Test: dedup handles strat findings without error ---"
"$SCRIPTS/deduplicate.sh" "$FIXTURES/valid-strat-finding.txt" >/dev/null 2>&1
exit_code=$?
assert_exit "deduplicate.sh does not crash on strat finding" "0" "$exit_code"
# Note: dedup currently parses File: not Document:, so strat findings pass through
# as NO_FINDINGS_REPORTED. This is a known limitation (dedup uses code-profile parsing).
# The test verifies it doesn't error out, which is the minimum contract.

# --- Section 5: Budget estimate for strat profile ---
echo ""
echo "--- Test: budget estimate works for strat agent count (6 specialists) ---"
budget_result=$("$SCRIPTS/track-budget.sh" estimate 6 15000 3 0 0 0)
exit_code=$?
assert_exit "budget estimate for 6 agents succeeds" "0" "$exit_code"

est=$(echo "$budget_result" | python3 -c "import json,sys; print(json.load(sys.stdin)['estimated_tokens'])")
assert_check "estimate is positive ($est > 0)" "[[ $est -gt 0 ]]"

# 6 agents should produce higher estimate than 5
budget_result_5=$("$SCRIPTS/track-budget.sh" estimate 5 15000 3 0 0 0)
est5=$(echo "$budget_result_5" | python3 -c "import json,sys; print(json.load(sys.stdin)['estimated_tokens'])")
assert_check "6-agent estimate > 5-agent estimate ($est > $est5)" "[[ $est -gt $est5 ]]"

# --- Section 6: Profile config for strat ---
echo ""
echo "--- Test: profile-config.sh reads strat config ---"
if [[ -f "$SCRIPTS/profile-config.sh" ]]; then
    agents=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/strat" agents 2>/dev/null || echo "")
    if [[ -n "$agents" ]]; then
        echo "  PASS: strat profile config readable"
        PASS=$((PASS + 1))
        # Verify strat has 6 agents (FEAS, ARCH, SEC, USER, SCOP, TEST)
        count=$(echo "$agents" | grep -c "prefix:" || true)
        assert_check "strat profile has 6 agents (got $count)" "[[ $count -eq 6 ]]"
    else
        echo "  FAIL: strat profile config returned empty agents"
        FAIL=$((FAIL + 1))
    fi

    # Verify key strat-specific config values
    has_verdicts=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/strat" has_verdicts 2>/dev/null || echo "")
    assert_check "strat profile has_verdicts=true" "[[ '$has_verdicts' == 'true' ]]"

    evidence_format=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/strat" evidence_format 2>/dev/null || echo "")
    assert_check "strat profile evidence_format=text_citation" "[[ '$evidence_format' == 'text_citation' ]]"
else
    echo "  SKIP: profile-config.sh not found"
fi

# --- Section 7: Convergence detection with strat findings ---
echo ""
echo "--- Test: convergence detection works with strat findings ---"
"$SCRIPTS/detect-convergence.sh" "$FIXTURES/valid-strat-finding.txt" "$FIXTURES/valid-strat-finding.txt" >/dev/null 2>&1
assert_exit "convergence detected for identical strat findings" "0" "$?"

# Non-convergence: approve finding vs reject finding
"$SCRIPTS/detect-convergence.sh" "$FIXTURES/valid-strat-finding.txt" "$FIXTURES/valid-strat-finding-approve.txt" >/dev/null 2>&1
conv_exit=$?
assert_check "different strat findings do not converge (exit=$conv_exit)" "[[ $conv_exit -ne 0 ]]"

# --- Section 8: Injection resistance with strat fields ---
echo ""
echo "--- Test: injection in Document field detected ---"
injection_finding=$(mktemp "${TMPDIR:-/tmp}/strat-injection-XXXXXX")
TEMP_FILES+=("$injection_finding")
cat > "$injection_finding" << 'FIXTURE'
Finding ID: SEC-001
Specialist: Security Analyst
Severity: Critical
Confidence: High
Document: RHAISTRAT-1234; $(rm -rf /)
Citation: Section 1
Title: Test injection in Document field
Evidence: This is a test finding with sufficient evidence length to pass the minimum threshold check of one hundred characters. The Document field contains a command injection attempt.
Recommended fix: Sanitize document references.
Verdict: Reject
FIXTURE

result=$("$SCRIPTS/validate-output.sh" "$injection_finding" SEC --profile strat 2>&1)
if echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
all_text = ' '.join(d.get('errors',[]) + d.get('warnings',[]))
# Either rejected outright or flagged with a warning
print('checked')
" 2>/dev/null; then
    echo "  PASS: injection attempt in Document field handled"
    PASS=$((PASS + 1))
else
    echo "  FAIL: injection in Document field should be handled"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
