#!/usr/bin/env bash
# Scan a unified diff for destructive command patterns.
# Usage: check-destructive.sh [diff_file | -]
# Input: Unified diff (file path, or - / omit for stdin)
# Output: JSON {"destructive": bool, "matches": [...]}
# Exit: 0 always (caller interprets JSON)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS_FILE="$SCRIPT_DIR/../protocols/destructive-patterns.txt"

if [[ ! -f "$PATTERNS_FILE" ]]; then
    echo '{"error": "destructive-patterns.txt not found"}'
    exit 0
fi

# Read input: file path argument, - for stdin, or default to stdin
INPUT_FILE="${1:--}"
if [[ "$INPUT_FILE" == "-" ]]; then
    DIFF_CONTENT=$(cat)
else
    if [[ ! -f "$INPUT_FILE" ]]; then
        python3 -c "import json; print(json.dumps({'error': 'Input file not found: ' + '$INPUT_FILE'}))"
        exit 0
    fi
    DIFF_CONTENT=$(cat "$INPUT_FILE")
fi

# Extract only added lines (lines starting with +, excluding +++ header)
ADDED_LINES=$(echo "$DIFF_CONTENT" | grep '^+' | grep -v '^+++' || true)

if [[ -z "$ADDED_LINES" ]]; then
    echo '{"destructive": false, "matches": []}'
    exit 0
fi

# Load patterns (skip comments and blank lines)
PATTERNS=()
while IFS= read -r line; do
    line=$(echo "$line" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
    [[ -z "$line" || "$line" == \#* ]] && continue
    PATTERNS+=("$line")
done < "$PATTERNS_FILE"

if [[ ${#PATTERNS[@]} -eq 0 ]]; then
    echo '{"destructive": false, "matches": []}'
    exit 0
fi

# Delegate all matching to python3 to avoid shell escaping issues
python3 -c "
import json, re, sys

patterns = json.loads(sys.argv[1])
added_lines = sys.stdin.read().splitlines()
matches = []

errors = []
for line_num_0, raw_line in enumerate(added_lines):
    content = raw_line[1:]  # strip leading +
    for pat in patterns:
        try:
            if re.search(pat, content, re.IGNORECASE):
                matches.append({
                    'pattern': pat,
                    'line': content,
                    'match_index': line_num_0 + 1
                })
        except re.error as e:
            errors.append({'pattern': pat, 'error': str(e)})

result = {'destructive': len(matches) > 0, 'matches': matches}
if errors:
    result['pattern_errors'] = errors
print(json.dumps(result))
" "$(printf '%s\n' "${PATTERNS[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")" <<< "$ADDED_LINES"
