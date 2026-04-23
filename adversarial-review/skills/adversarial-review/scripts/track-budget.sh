#!/usr/bin/env bash
# Track token budget consumption.
# Usage: track-budget.sh <action> [args]
#   init <budget_limit>          — initialize budget tracking (prints state_file path in JSON)
#   add <file_or_chars>          — add token consumption (file or char count)
#   estimate <num_agents> <code_tokens> <iterations> [num_work_items] [impact_graph_tokens] [reference_tokens] — estimate total cost
#   update-limit <new_limit>     — change budget limit without resetting consumed (for auto-escalation)
#   status                       — show remaining budget
#   cleanup                      — remove state file
# State stored via mktemp; caller must capture state_file from init output and set BUDGET_STATE_FILE

set -euo pipefail

ACTION="${1:?Usage: track-budget.sh <init|add|estimate|status|rebalance> [args]}"

# Cost per 1M tokens (USD). Default blended rate (~60% input, ~40% output).
# Override via COST_PER_1M_TOKENS environment variable for different models.
COST_PER_1M_TOKENS_BLENDED="${COST_PER_1M_TOKENS:-7.80}"
# Agent budget multiplier (matches guardrails.md AGENT_BUDGET_MULTIPLIER)
AGENT_BUDGET_MULTIPLIER=1.5

if [[ -n "${BUDGET_STATE_FILE:-}" ]]; then
    STATE_FILE="$BUDGET_STATE_FILE"
elif [[ "$ACTION" == "init" ]]; then
    STATE_FILE=$(mktemp "${TMPDIR:-/tmp}/adversarial-review-budget-XXXXXXXXXX")
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
        # limit=0 means unlimited mode (--no-budget)
        python3 -c "
import json, sys
limit = int(sys.argv[1])
state_file = sys.argv[2]
cost_per_1m = float(sys.argv[3])
unlimited = limit == 0
with open(state_file, 'w') as f:
    json.dump({'limit': limit, 'consumed': 0, 'unlimited': unlimited}, f)
result = {
    'limit': limit, 'consumed': 0, 'exceeded': False,
    'unlimited': unlimited,
    'state_file': state_file,
}
if unlimited:
    result['remaining'] = 'unlimited'
else:
    result['remaining'] = limit
    result['budget_cost_usd'] = round(limit / 1_000_000 * cost_per_1m, 2)
print(json.dumps(result))
" "$LIMIT" "$STATE_FILE" "$COST_PER_1M_TOKENS_BLENDED"
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

        # Parse optional --agent and --per-agent-cap flags
        AGENT_NAME=""
        PER_AGENT_CAP=0
        shift 2  # past ACTION and INPUT
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --agent) AGENT_NAME="${2:?--agent requires a name}"; shift 2 ;;
                --per-agent-cap) PER_AGENT_CAP="${2:?--per-agent-cap requires a number}"; shift 2 ;;
                *) echo "{\"error\": \"Unknown flag: $1\"}" >&2; exit 2 ;;
            esac
        done
        if [[ -n "$AGENT_NAME" ]]; then
            validate_int "$PER_AGENT_CAP" "per_agent_cap"
        fi

        if [[ ! -f "$STATE_FILE" ]]; then
            echo '{"error": "Budget not initialized. Run init first."}' >&2
            exit 1
        fi

        consumed=$(read_state_field "consumed")
        limit=$(read_state_field "limit")
        validate_int "$consumed" "consumed"
        validate_int "$limit" "limit"
        new_consumed=$((consumed + tokens))

        # limit=0 means unlimited: never exceeded
        if (( limit == 0 )); then
            exceeded=false
            remaining=-1  # sentinel for unlimited
        else
            remaining=$((limit - new_consumed))
            exceeded=false
            if (( remaining <= 0 )); then exceeded=true; remaining=0; fi
        fi

        python3 -c "
import json, sys
limit, consumed, remaining_raw, added = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
exceeded = sys.argv[5] == 'true'
state_file = sys.argv[6]
agent_name = sys.argv[7]
per_agent_cap = int(sys.argv[8])
unlimited = limit == 0

with open(state_file) as f:
    state = json.load(f)

state['limit'] = limit
state['consumed'] = consumed

agent_exceeded = False
agent_consumed = 0

if agent_name:
    agents = state.setdefault('agents', {})
    agent_state = agents.setdefault(agent_name, {'consumed': 0})
    agent_state['consumed'] += added
    agent_consumed = agent_state['consumed']
    # per-agent caps disabled in unlimited mode
    if not unlimited and per_agent_cap > 0 and agent_consumed > per_agent_cap:
        agent_exceeded = True

with open(state_file, 'w') as f:
    json.dump(state, f)

result = {'limit': limit, 'consumed': consumed, 'exceeded': exceeded, 'added': added, 'unlimited': unlimited}
if unlimited:
    result['remaining'] = 'unlimited'
else:
    result['remaining'] = remaining_raw
if agent_name:
    result['agent_exceeded'] = agent_exceeded
    result['agent_consumed'] = agent_consumed
print(json.dumps(result))
" "$limit" "$new_consumed" "$remaining" "$tokens" "$exceeded" "$STATE_FILE" "$AGENT_NAME" "$PER_AGENT_CAP"
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
        # Prompt overhead: minimal prompt (~2825 tokens) per agent per iteration
        # Covers: role (~1500) + inoculation (~500) + delimiters (~125) + template (~500) + nav (~200)
        PROMPT_TOKENS_PER_AGENT=2825
        prompt_overhead=$((PROMPT_TOKENS_PER_AGENT * NUM_AGENTS * (ITERATIONS + ITERATIONS)))  # phase1 + phase2 iterations
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
        total=$((prompt_overhead + phase1 + phase2 + phase34 + phase5))

        python3 -c "
import json, sys
total = int(sys.argv[1])
cost_per_1m = float(sys.argv[10])
result = {
    'estimated_tokens': total,
    'prompt_overhead': int(sys.argv[2]),
    'phase1': int(sys.argv[3]),
    'phase2': int(sys.argv[4]),
    'phase34': int(sys.argv[5]),
    'phase5_remediation': int(sys.argv[6]),
    'estimated_cost_usd': round(total / 1_000_000 * cost_per_1m, 2)
}
if sys.argv[7] == 'true':
    result['impact_graph'] = int(sys.argv[8])
if int(sys.argv[9]) > 0:
    result['reference_tokens'] = int(sys.argv[9])
print(json.dumps(result))
" "$total" "$prompt_overhead" "$phase1" "$phase2" "$phase34" "$phase5" "$DIFF_MODE" "$IMPACT_GRAPH_TOKENS" "$REFERENCE_TOKENS" "$COST_PER_1M_TOKENS_BLENDED"
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

        if (( limit == 0 )); then
            exceeded=false
            remaining=-1  # sentinel for unlimited
        else
            remaining=$((limit - consumed))
            exceeded=false
            if (( remaining <= 0 )); then exceeded=true; remaining=0; fi
        fi

        python3 -c "
import json, sys
limit = int(sys.argv[1])
consumed = int(sys.argv[2])
remaining_raw = int(sys.argv[3])
exceeded = sys.argv[4] == 'true'
cost_per_1m = float(sys.argv[5])
unlimited = limit == 0
result = {
    'limit': limit,
    'consumed': consumed,
    'exceeded': exceeded,
    'unlimited': unlimited,
    'consumed_cost_usd': round(consumed / 1_000_000 * cost_per_1m, 2),
}
if unlimited:
    result['remaining'] = 'unlimited'
else:
    result['remaining'] = remaining_raw
print(json.dumps(result))
" "$limit" "$consumed" "$remaining" "$exceeded" "$COST_PER_1M_TOKENS_BLENDED"
        ;;
    update-limit)
        # Update the budget limit without resetting consumed tokens.
        # Used by auto-escalation when the pre-flight estimate exceeds the current budget.
        # Usage: track-budget.sh update-limit <new_limit>
        NEW_LIMIT="${2:?Usage: track-budget.sh update-limit <new_limit>}"
        validate_int "$NEW_LIMIT" "new_limit"
        if [[ ! -f "$STATE_FILE" ]]; then
            echo '{"error": "Budget not initialized. Run init first."}' >&2
            exit 1
        fi

        python3 -c "
import json, sys
new_limit = int(sys.argv[1])
state_file = sys.argv[2]
cost_per_1m = float(sys.argv[3])
unlimited = new_limit == 0

with open(state_file) as f:
    state = json.load(f)

old_limit = state['limit']
consumed = state['consumed']
state['limit'] = new_limit
state['unlimited'] = unlimited

with open(state_file, 'w') as f:
    json.dump(state, f)

remaining = 'unlimited' if unlimited else max(0, new_limit - consumed)
exceeded = False if unlimited else (new_limit - consumed) <= 0

result = {
    'old_limit': old_limit,
    'new_limit': new_limit,
    'consumed': consumed,
    'remaining': remaining,
    'exceeded': exceeded,
    'unlimited': unlimited,
}
if not unlimited:
    result['budget_cost_usd'] = round(new_limit / 1_000_000 * cost_per_1m, 2)
print(json.dumps(result))
" "$NEW_LIMIT" "$STATE_FILE" "$COST_PER_1M_TOKENS_BLENDED"
        ;;
    rebalance)
        # Redistribute unused budget from low-activity agents to high-activity ones.
        # Call after Phase 1 completes to give high-finding-count agents more room in Phase 2.
        # Usage: track-budget.sh rebalance
        if [[ ! -f "$STATE_FILE" ]]; then
            echo '{"error": "Budget not initialized"}' >&2
            exit 1
        fi

        python3 -c "
import json, sys, math

state_file = sys.argv[1]
multiplier = float(sys.argv[2])

with open(state_file) as f:
    state = json.load(f)

if state.get('unlimited', False):
    print(json.dumps({'rebalanced': False, 'reason': 'unlimited mode, no caps to rebalance'}))
    sys.exit(0)

agents = state.get('agents', {})
if len(agents) < 2:
    print(json.dumps({'rebalanced': False, 'reason': 'need at least 2 agents'}))
    sys.exit(0)

limit = state['limit']
num_agents = len(agents)
fair_share = math.ceil(limit / num_agents)
original_cap = math.ceil(fair_share * multiplier)

# Calculate usage ratio for each agent
usage = {}
for name, data in agents.items():
    consumed = data.get('consumed', 0)
    usage[name] = consumed / max(fair_share, 1)

# Agents below 50% usage after Phase 1 are 'low-activity'
# Their unused portion (up to 50% of their fair share) is pooled
pool = 0
low_agents = []
high_agents = []
for name, ratio in usage.items():
    if ratio < 0.5:
        low_agents.append(name)
        donatable = int(fair_share * 0.5 * (1 - ratio))
        pool += donatable
    elif ratio > 0.75:
        high_agents.append(name)

if pool == 0 or len(high_agents) == 0:
    print(json.dumps({'rebalanced': False, 'reason': 'no rebalancing needed', 'usage': usage}))
    sys.exit(0)

# Distribute pool evenly to high-activity agents
bonus_per_agent = pool // len(high_agents)
new_caps = {}
for name in agents:
    if name in high_agents:
        new_caps[name] = original_cap + bonus_per_agent
    elif name in low_agents:
        new_caps[name] = max(int(original_cap * 0.75), agents[name].get('consumed', 0) + 1000)
    else:
        new_caps[name] = original_cap

state['agent_caps'] = new_caps
with open(state_file, 'w') as f:
    json.dump(state, f)

print(json.dumps({
    'rebalanced': True,
    'pool_tokens': pool,
    'bonus_per_high_agent': bonus_per_agent,
    'low_agents': low_agents,
    'high_agents': high_agents,
    'new_caps': new_caps
}))
" "$STATE_FILE" "$AGENT_BUDGET_MULTIPLIER"
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
