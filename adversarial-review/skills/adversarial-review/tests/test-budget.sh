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

# Test: estimate includes estimated_cost_usd
echo "--- Test: estimate includes cost ---"
RESULT=$("$BUDGET_SCRIPT" estimate 5 10000 3 0 0 0)
cost_ok=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print('yes' if d.get('estimated_cost_usd',0) > 0 else 'no')")
cost=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('estimated_cost_usd', 0))")
assert_check "estimated_cost_usd present and > 0 (\$$cost)" "[[ '$cost_ok' == 'yes' ]]"

# Test: init includes budget_cost_usd
echo "--- Test: init includes budget cost ---"
INIT_TMP=$(mktemp "${TMPDIR:-/tmp}/test-budget-cost-XXXXXX")
RESULT=$(TMPDIR="$(dirname "$INIT_TMP")" "$BUDGET_SCRIPT" init 500000)
cost_ok=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print('yes' if d.get('budget_cost_usd',0) > 0 else 'no')")
budget_cost=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('budget_cost_usd', 0))")
assert_check "budget_cost_usd present and > 0 (\$$budget_cost)" "[[ '$cost_ok' == 'yes' ]]"
state_file=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['state_file'])")
rm -f "$state_file"

# Test: status includes consumed_cost_usd
echo "--- Test: status includes consumed cost ---"
INIT_RESULT=$("$BUDGET_SCRIPT" init 500000)
BUDGET_STATE_FILE=$(echo "$INIT_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['state_file'])")
export BUDGET_STATE_FILE
"$BUDGET_SCRIPT" add 40000 --agent SEC --per-agent-cap 200000 >/dev/null 2>&1
STATUS=$("$BUDGET_SCRIPT" status)
cost_ok=$(echo "$STATUS" | python3 -c "import json,sys; d=json.load(sys.stdin); print('yes' if 'consumed_cost_usd' in d else 'no')")
consumed_cost=$(echo "$STATUS" | python3 -c "import json,sys; print(json.load(sys.stdin).get('consumed_cost_usd', -1))")
assert_check "consumed_cost_usd present (\$$consumed_cost)" "[[ '$cost_ok' == 'yes' ]]"

# Test: rebalance with 2 agents (one high, one low activity)
echo "--- Test: rebalance redistributes budget ---"
# Need SEC usage > 75% of fair_share and QUAL usage < 50% of fair_share
# fair_share = 500000/2 = 250000. SEC needs > 187500, QUAL needs < 125000
# SEC already has 10000 (from 40000 chars / 4), add more
"$BUDGET_SCRIPT" add 800000 --agent SEC --per-agent-cap 999999 >/dev/null 2>&1   # SEC: 200000+ tokens
"$BUDGET_SCRIPT" add 4000 --agent QUAL --per-agent-cap 999999 >/dev/null 2>&1    # QUAL: 1000 tokens
REBAL=$("$BUDGET_SCRIPT" rebalance)
rebalanced=$(echo "$REBAL" | python3 -c "import json,sys; print(json.load(sys.stdin).get('rebalanced', False))")
assert_check "rebalance executed ($rebalanced)" "[[ '$rebalanced' == 'True' ]]"

if [[ "$rebalanced" == "True" ]]; then
    high=$(echo "$REBAL" | python3 -c "import json,sys; print(json.load(sys.stdin)['high_agents'])")
    low=$(echo "$REBAL" | python3 -c "import json,sys; print(json.load(sys.stdin)['low_agents'])")
    assert_check "SEC is high-activity agent" "echo '$high' | grep -q SEC"
    assert_check "QUAL is low-activity agent" "echo '$low' | grep -q QUAL"
    pool=$(echo "$REBAL" | python3 -c "import json,sys; print(json.load(sys.stdin)['pool_tokens'])")
    assert_check "pool_tokens > 0 ($pool)" "[[ $pool -gt 0 ]]"
fi

rm -f "$BUDGET_STATE_FILE"
unset BUDGET_STATE_FILE

# Test: rebalance with single agent returns no-op
echo "--- Test: rebalance no-op with single agent ---"
INIT_RESULT=$("$BUDGET_SCRIPT" init 500000)
BUDGET_STATE_FILE=$(echo "$INIT_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['state_file'])")
export BUDGET_STATE_FILE
"$BUDGET_SCRIPT" add 40000 --agent SEC --per-agent-cap 500000 >/dev/null 2>&1
REBAL=$("$BUDGET_SCRIPT" rebalance)
rebalanced=$(echo "$REBAL" | python3 -c "import json,sys; print(json.load(sys.stdin).get('rebalanced', False))")
assert_check "rebalance is no-op with 1 agent ($rebalanced)" "[[ '$rebalanced' == 'False' ]]"
rm -f "$BUDGET_STATE_FILE"
unset BUDGET_STATE_FILE

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit "$FAIL"
