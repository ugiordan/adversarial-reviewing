#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUDGET_SCRIPT="$SCRIPT_DIR/scripts/track-budget.sh"
PASS=0
FAIL=0

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

echo "=== track-budget.sh tests ==="

# Test: estimate includes prompt_overhead
echo "--- Test: estimate includes prompt_overhead ---"
RESULT=$("$BUDGET_SCRIPT" estimate 5 10000 3 0 0 0)
# Without prompt_overhead: phase1=150000, phase2=187500, phase34=10000, phase5=0 = 347500
# With prompt_overhead: 2825*5*(3*2)=84750 added. Total > 347500
est=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['estimated_tokens'])")
assert_check "estimate includes prompt_overhead ($est > 347500)" "[[ $est -gt 347500 ]]"

prompt_oh=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('prompt_overhead', 0))")
assert_check "prompt_overhead field present ($prompt_oh > 0)" "[[ $prompt_oh -gt 0 ]]"

# Test: TMPDIR is used (not hardcoded /tmp)
echo "--- Test: TMPDIR respected ---"
CUSTOM_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-budget-tmpdir-XXXXXX")
RESULT=$(TMPDIR="$CUSTOM_TMP" "$BUDGET_SCRIPT" init 500000)
state_file=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['state_file'])")
if echo "$state_file" | grep -q "$CUSTOM_TMP"; then
    echo "  PASS: state file created in custom TMPDIR"
    PASS=$((PASS + 1))
else
    echo "  FAIL: state file not in custom TMPDIR ($state_file)"
    FAIL=$((FAIL + 1))
fi
rm -f "$state_file"
rmdir "$CUSTOM_TMP" 2>/dev/null || true

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit "$FAIL"
