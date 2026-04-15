#!/usr/bin/env bash
# Tests for detect-convergence.sh --triage mode
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONVERGE="$SCRIPT_DIR/scripts/detect-convergence.sh"
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

echo "=== detect-convergence.sh --triage tests ==="

iter1=$(mktemp)
iter2_same=$(mktemp)
iter2_diff=$(mktemp)

cat > "$iter1" << 'EOF'
Triage ID: TRIAGE-CORR-001
External Comment ID: EXT-001
Verdict: Fix

Triage ID: TRIAGE-CORR-002
External Comment ID: EXT-002
Verdict: No-Fix
EOF

cat > "$iter2_same" << 'EOF'
Triage ID: TRIAGE-CORR-001
External Comment ID: EXT-001
Verdict: Fix

Triage ID: TRIAGE-CORR-002
External Comment ID: EXT-002
Verdict: No-Fix
EOF

cat > "$iter2_diff" << 'EOF'
Triage ID: TRIAGE-CORR-001
External Comment ID: EXT-001
Verdict: Fix

Triage ID: TRIAGE-CORR-002
External Comment ID: EXT-002
Verdict: Investigate
EOF

# Test 1: Converged triage verdicts
bash "$CONVERGE" --triage "$iter2_same" "$iter1" >/dev/null 2>&1
assert_exit "Same verdicts converge" "0" "$?"

# Test 2: Changed verdict does not converge
bash "$CONVERGE" --triage "$iter2_diff" "$iter1" >/dev/null 2>&1
assert_exit "Changed verdict does not converge" "1" "$?"

# Test 3: JSON output for converged
result=$(bash "$CONVERGE" --triage "$iter2_same" "$iter1" 2>&1)
if echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['converged'] == True" 2>/dev/null; then
    echo "  PASS: Converged JSON output correct"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Should output converged=true"
    FAIL=$((FAIL + 1))
fi

# Test 4: JSON output for not converged
result=$(bash "$CONVERGE" --triage "$iter2_diff" "$iter1" 2>&1)
if echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['converged'] == False" 2>/dev/null; then
    echo "  PASS: Not converged JSON output correct"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Should output converged=false"
    FAIL=$((FAIL + 1))
fi

# Test 5: Standard mode still works (regression check)
bash "$CONVERGE" "$SCRIPT_DIR/tests/fixtures/valid-finding.txt" "$SCRIPT_DIR/tests/fixtures/valid-finding.txt" >/dev/null 2>&1
assert_exit "Standard mode still works" "0" "$?"

rm -f "$iter1" "$iter2_same" "$iter2_diff"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
