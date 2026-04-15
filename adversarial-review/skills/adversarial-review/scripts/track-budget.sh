#!/usr/bin/env bash
# Track token budget consumption.
# Usage: track-budget.sh <action> [args]
#   init <budget_limit>          — initialize budget tracking (prints state_file path in JSON)
#   add <file_or_chars>          — add token consumption (file or char count)
#   estimate <num_agents> <code_tokens> <iterations> [num_work_items] [impact_graph_tokens] [reference_tokens] — estimate total cost
#   status                       — show remaining budget
#   cleanup                      — remove state file
# State stored via mktemp; caller must capture state_file from init output and set BUDGET_STATE_FILE

set -euo pipefail

ACTION="${1:?Usage: track-budget.sh <init|add|estimate|status> [args]}"

if [[ -n "${BUDGET_STATE_FILE:-}" ]]; then
    STATE_FILE="$BUDGET_STATE_FILE"
elif [[ "$ACTION" == "init" ]]; then
    STATE_FILE=$(mktemp /tmp/adversarial-review-budget-XXXXXXXXXX)
elif [[ "$ACTION" == "estimate" ]]; then
    STATE_FILE=""  # estimate is a pure calculation, no state needed
else
    echo '{"error": "BUDGET_STATE_FILE not set. Run init first and set BUDGET_STATE_FILE to the state_file value from init output."}' >&2
    exit 1
fi

# Read a JSON field from the state file safely (no interpolation into code).
read_state_field() {
    local field="$1"
    python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    print(json.load(f)[sys.argv[2]])
" "$STATE_FILE" "$field"
}

# Validate that a value is a non-negative integer.
validate_int() {
    local val="$1" name="$2"
    if ! [[ "$val" =~ ^[0-9]+$ ]]; then
        echo "{\"error\": \"$name must be a non-negative integer\"}" >&2
        exit 1
    fi
}

# Safe JSON output via python3
json_output() {
    python3 -c "
import json, sys
print(json.dumps(json.loads(sys.argv[1])))
" "$1"
}

case "$ACTION" in
    init)
        LIMIT="${2:?Usage: track-budget.sh init <budget_limit>}"
        validate_int "$LIMIT" "budget_limit"
        python3 -c "
import json, sys
limit = int(sys.argv[1])
state_file = sys.argv[2]
with open(state_file, 'w') as f:
    json.dump({'limit': limit, 'consumed': 0}, f)
print(json.dumps({'limit': limit, 'consumed': 0, 'remaining': limit, 'exceeded': False, 'state_file': state_file}))
" "$LIMIT" "$STATE_FILE"
        ;;
    add)
        INPUT="${2:?Usage: track-budget.sh add <file_or_char_count>}"
        if [[ -f "$INPUT" ]]; then
            chars=$(wc -c < "$INPUT" | tr -d '[:space:]')
        else
            chars="$INPUT"
        fi
        validate_int "$chars" "char_count"
        tokens=$((chars / 4))  # char/4 heuristic

        if [[ ! -f "$STATE_FILE" ]]; then
            echo '{"error": "Budget not initialized. Run init first."}' >&2
            exit 1
        fi

        consumed=$(read_state_field "consumed")
        limit=$(read_state_field "limit")
        validate_int "$consumed" "consumed"
        validate_int "$limit" "limit"
        new_consumed=$((consumed + tokens))
        remaining=$((limit - new_consumed))
        exceeded=false
        if (( remaining <= 0 )); then exceeded=true; remaining=0; fi

        python3 -c "
import json, sys
limit, consumed, remaining, added = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
exceeded = sys.argv[5] == 'true'
state_file = sys.argv[6]
with open(state_file, 'w') as f:
    json.dump({'limit': limit, 'consumed': consumed}, f)
print(json.dumps({'limit': limit, 'consumed': consumed, 'remaining': remaining, 'exceeded': exceeded, 'added': added}))
" "$limit" "$new_consumed" "$remaining" "$tokens" "$exceeded" "$STATE_FILE"
        ;;
    estimate)
        # Parse optional --diff flag
        DIFF_MODE=false
        if [[ "${2:-}" == "--diff" ]]; then
            DIFF_MODE=true
            shift
        fi
        NUM_AGENTS="${2:?Usage: track-budget.sh estimate [--diff] <num_agents> <code_tokens> <iterations> [num_work_items] [impact_graph_tokens]}"
        CODE_TOKENS="${3:?}"
        ITERATIONS="${4:?}"
        NUM_WORK_ITEMS="${5:-0}"
        IMPACT_GRAPH_TOKENS="${6:-0}"
        REFERENCE_TOKENS="${7:-0}"
        validate_int "$NUM_AGENTS" "num_agents"
        validate_int "$CODE_TOKENS" "code_tokens"
        validate_int "$ITERATIONS" "iterations"
        validate_int "$NUM_WORK_ITEMS" "num_work_items"
        validate_int "$IMPACT_GRAPH_TOKENS" "impact_graph_tokens"
        validate_int "$REFERENCE_TOKENS" "reference_tokens"
        # Phase 1: agents * ((code + impact_graph) * iterations + reference_tokens * (iterations - 1))
        # References only injected at iteration 2+, so (iterations - 1) factor
        ref_iterations=$((ITERATIONS > 1 ? ITERATIONS - 1 : 0))
        phase1=$((NUM_AGENTS * ((CODE_TOKENS + IMPACT_GRAPH_TOKENS) * ITERATIONS + REFERENCE_TOKENS * ref_iterations)))
        # Phase 2: agents * (agents * avg_findings * finding_size) * iterations
        avg_findings=5
        finding_size=500
        phase2=$((NUM_AGENTS * NUM_AGENTS * avg_findings * finding_size * ITERATIONS))
        # Phase 3 + 4: fixed overhead
        phase34=10000
        # Phase 5: remediation overhead
        phase5=$((NUM_WORK_ITEMS * 15000))
        total=$((phase1 + phase2 + phase34 + phase5))

        python3 -c "
import json, sys
result = {
    'estimated_tokens': int(sys.argv[1]),
    'phase1': int(sys.argv[2]),
    'phase2': int(sys.argv[3]),
    'phase34': int(sys.argv[4]),
    'phase5_remediation': int(sys.argv[5])
}
if sys.argv[6] == 'true':
    result['impact_graph'] = int(sys.argv[7])
if int(sys.argv[8]) > 0:
    result['reference_tokens'] = int(sys.argv[8])
print(json.dumps(result))
" "$total" "$phase1" "$phase2" "$phase34" "$phase5" "$DIFF_MODE" "$IMPACT_GRAPH_TOKENS" "$REFERENCE_TOKENS"
        ;;
    status)
        if [[ ! -f "$STATE_FILE" ]]; then
            echo '{"error": "Budget not initialized"}' >&2
            exit 1
        fi
        consumed=$(read_state_field "consumed")
        limit=$(read_state_field "limit")
        validate_int "$consumed" "consumed"
        validate_int "$limit" "limit"
        remaining=$((limit - consumed))
        exceeded=false
        if (( remaining <= 0 )); then exceeded=true; remaining=0; fi

        python3 -c "
import json, sys
print(json.dumps({
    'limit': int(sys.argv[1]),
    'consumed': int(sys.argv[2]),
    'remaining': int(sys.argv[3]),
    'exceeded': sys.argv[4] == 'true'
}))
" "$limit" "$consumed" "$remaining" "$exceeded"
        ;;
    cleanup)
        if [[ -n "$STATE_FILE" && -f "$STATE_FILE" ]]; then
            rm -f "$STATE_FILE"
            echo '{"cleaned": true}'
        else
            echo '{"cleaned": false, "reason": "no state file found"}'
        fi
        ;;
    *)
        echo "Unknown action: $ACTION" >&2
        exit 1
        ;;
esac
