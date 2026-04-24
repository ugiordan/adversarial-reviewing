#!/usr/bin/env bash
# Verify that all files changed in the current worktree are within review scope.
# Usage: check-scope-lock.sh <scope_file> [--strict]
# Output: JSON {"in_scope": bool, "out_of_scope_files": [...], "diff_method": "..."}
# Exit: 0 if all in scope, 1 if out-of-scope files found (always, not just --strict)
# Note: Callers should parse the JSON for details. Exit code indicates scope status.

set -euo pipefail

SCOPE_FILE="${1:?Usage: check-scope-lock.sh <scope_file> [--strict]}"
STRICT=false

shift
while [[ $# -gt 0 ]]; do
    case "$1" in
        --strict) STRICT=true; shift ;;
        *) echo "{\"error\": \"Unknown flag: $1\"}" >&2; exit 2 ;;
    esac
done

if [[ ! -f "$SCOPE_FILE" ]]; then
    python3 -c "import json; print(json.dumps({'error': 'Scope file not found: ' + '$SCOPE_FILE'}))"
    exit 2
fi

# Get changed files from git. Try committed changes first, then staged.
DIFF_METHOD=""
if git rev-parse HEAD~1 &>/dev/null; then
    CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD 2>/dev/null)
    DIFF_METHOD="committed (HEAD~1..HEAD)"
elif git rev-parse HEAD &>/dev/null; then
    CHANGED_FILES=$(git diff --name-only --cached 2>/dev/null)
    DIFF_METHOD="staged (--cached)"
else
    echo '{"error": "No git history available. Cannot determine changed files."}'
    exit 2
fi

if [[ -z "$CHANGED_FILES" ]]; then
    python3 -c "import json; print(json.dumps({'in_scope': True, 'out_of_scope_files': [], 'diff_method': '$DIFF_METHOD'}))"
    exit 0
fi

# Compare changed files against scope
OUT_OF_SCOPE=()
while IFS= read -r changed; do
    [[ -z "$changed" ]] && continue
    if ! grep -qxF "$changed" "$SCOPE_FILE"; then
        OUT_OF_SCOPE+=("$changed")
    fi
done <<< "$CHANGED_FILES"

if [[ ${#OUT_OF_SCOPE[@]} -eq 0 ]]; then
    python3 -c "import json; print(json.dumps({'in_scope': True, 'out_of_scope_files': [], 'diff_method': '$DIFF_METHOD'}))"
    exit 0
fi

# Out-of-scope files found
python3 -c "
import json, sys
oos = json.loads(sys.argv[1])
print(json.dumps({'in_scope': False, 'out_of_scope_files': oos, 'diff_method': sys.argv[2], 'strict': sys.argv[3] == 'true'}))
" "$(printf '%s\n' "${OUT_OF_SCOPE[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")" "$DIFF_METHOD" "$STRICT"

# Exit 1 when out-of-scope files found (regardless of strict mode)
# Strict mode is informational in JSON for the caller to decide enforcement
exit 1
