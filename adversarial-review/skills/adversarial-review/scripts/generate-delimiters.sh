#!/usr/bin/env bash
# Generate cryptographically random delimiters for input isolation.
# Usage: generate-delimiters.sh [--category CATEGORY] <input_file> [extra_files...]
# Output: JSON with start_delimiter, end_delimiter, field_start, field_end
# Exit 0 on success, 1 on error.

set -euo pipefail

if ! command -v python3 &>/dev/null; then
    echo '{"error": "python3 is required but not found"}' >&2
    exit 2
fi

CATEGORY="REVIEW_TARGET"
if [[ "${1:-}" == "--category" ]]; then
    CATEGORY="${2:?Usage: generate-delimiters.sh [--category CATEGORY] <input_file> [extra_files...]}"
    shift 2
fi

INPUT_FILE="${1:?Usage: generate-delimiters.sh [--category CATEGORY] <input_file> [extra_files...]}"
shift || true

if [[ ! -f "$INPUT_FILE" ]]; then
    echo '{"error": "Input file not found"}' >&2
    exit 1
fi

generate_hex() {
    # 32 hex chars = 128 bits of entropy via CSPRNG
    if command -v openssl &>/dev/null; then
        openssl rand -hex 16
    elif [[ -r /dev/urandom ]]; then
        od -An -tx1 -N16 /dev/urandom | tr -d ' \n'
    else
        echo '{"error": "No CSPRNG available"}' >&2
        exit 1
    fi
}

INPUT_CONTENT=$(cat "$INPUT_FILE")
for extra in "$@"; do
    if [[ -f "$extra" ]]; then
        INPUT_CONTENT="$INPUT_CONTENT$(cat "$extra")"
    fi
done

# Generate collision-free hex with retry loop
generate_collision_free_hex() {
    local max_attempts=10
    local hex
    for (( attempt=1; attempt<=max_attempts; attempt++ )); do
        hex=$(generate_hex)
        if ! grep -qF "$hex" <<< "$INPUT_CONTENT"; then
            echo "$hex"
            return 0
        fi
        if (( attempt == max_attempts )); then
            echo '{"error": "Could not generate collision-free delimiter after 10 attempts"}' >&2
            exit 1
        fi
    done
}

# Generate input delimiters with collision detection
HEX=$(generate_collision_free_hex)
START_DELIM="===${CATEGORY}_${HEX}_START==="
END_DELIM="===${CATEGORY}_${HEX}_END==="

# Generate field-level isolation markers with full 128-bit entropy and collision detection
FIELD_HEX=$(generate_collision_free_hex)
FIELD_START="[FIELD_DATA_${FIELD_HEX}_START]"
FIELD_END="[FIELD_DATA_${FIELD_HEX}_END]"

# Use python3 for safe JSON serialization with sys.argv (consistent with other scripts)
python3 - "$START_DELIM" "$END_DELIM" "$FIELD_START" "$FIELD_END" "$HEX" "$FIELD_HEX" << 'PYEOF'
import json, sys
print(json.dumps({
    'start_delimiter': sys.argv[1],
    'end_delimiter': sys.argv[2],
    'field_start': sys.argv[3],
    'field_end': sys.argv[4],
    'hex': sys.argv[5],
    'field_hex': sys.argv[6]
}, indent=4))
PYEOF
