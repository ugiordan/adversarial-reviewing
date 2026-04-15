#!/usr/bin/env bash
# Validate agent output against finding template schema.
# Usage: validate-output.sh <output_file> <expected_role_prefix>
# Output: JSON with valid (bool), errors (array), finding_count (int)
# Exit 0 if valid, exit 1 if invalid.

set -euo pipefail

# Require python3 upfront (used for unicode normalization and JSON serialization)
if ! command -v python3 &>/dev/null; then
    echo '{"error": "python3 is required but not found"}' >&2
    exit 2
fi

OUTPUT_FILE="${1:?Usage: validate-output.sh <output_file> <expected_role_prefix>}"
ROLE_PREFIX="${2:?Usage: validate-output.sh <output_file> <expected_role_prefix>}"

SCOPE_FILE=""
MAX_FINDINGS=0
CHECK_FIXES=false

# Parse optional flags after required positional args
shift 2  # past OUTPUT_FILE and ROLE_PREFIX
while [[ $# -gt 0 ]]; do
    case "$1" in
        --scope) SCOPE_FILE="${2:?--scope requires a file path}"; shift 2 ;;
        --max-findings) MAX_FINDINGS="${2:?--max-findings requires a number}"; shift 2 ;;
        --check-fixes) CHECK_FIXES=true; shift ;;
        *) echo "{\"error\": \"Unknown flag: $1\"}" >&2; exit 2 ;;
    esac
done

ERRORS=()
WARNINGS=()
FINDING_COUNT=0

content=$(cat "$OUTPUT_FILE")

# Normalize unicode (NFKC)
content=$(python3 -c "
import unicodedata, sys
sys.stdout.write(unicodedata.normalize('NFKC', sys.stdin.read()))
" <<< "$content")

# Portable helper: extract field value after label
extract_field() {
    local label="$1"
    local text="$2"
    echo "$text" | sed -n "s/^${label} *//p" | head -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# Source shared injection detection (once, outside the loop)
SCRIPT_DIR_VALIDATE="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR_VALIDATE/_injection-check.sh"

# Check for NO_FINDINGS_REPORTED marker (valid zero-finding output)
if grep -qF "NO_FINDINGS_REPORTED" <<< "$content"; then
    echo '{"valid": true, "errors": [], "finding_count": 0, "zero_findings": true}'
    exit 0
fi

# Extract finding IDs
finding_ids=$(echo "$content" | sed -n 's/^Finding ID: \([A-Z]*-[0-9]*\).*/\1/p')

if [[ -z "$finding_ids" ]]; then
    ERRORS+=("No findings found matching pattern 'Finding ID: [A-Z]+-NNN'")
fi

while IFS= read -r fid; do
    [[ -z "$fid" ]] && continue
    FINDING_COUNT=$((FINDING_COUNT + 1))

    # Validate finding ID format strictly (defense against injection)
    if ! [[ "$fid" =~ ^[A-Z]+-[0-9]+$ ]]; then
        ERRORS+=("Finding ID '$fid' contains invalid characters")
        continue
    fi

    # Check role prefix
    prefix=$(echo "$fid" | sed 's/-.*//')
    if [[ "$prefix" != "$ROLE_PREFIX" ]]; then
        ERRORS+=("Finding $fid: prefix '$prefix' does not match expected '$ROLE_PREFIX'")
    fi

    # Extract the finding block using AWK with literal index() match (prevents SEC-1 matching SEC-10)
    block=$(awk -v target="Finding ID: $fid" '
        index($0, target) == 1 && length($0) == length(target) {found=1; print; next}
        index($0, target) == 1 && substr($0, length(target)+1, 1) !~ /[0-9]/ {found=1; print; next}
        found && /^Finding ID: [A-Z]+-[0-9]+/ {exit}
        found {print}
    ' <<< "$content" | head -50)

    # Check required fields
    for field in "Specialist:" "Severity:" "Confidence:" "File:" "Lines:" "Title:" "Evidence:"; do
        if ! grep -qF "$field" <<< "$block"; then
            ERRORS+=("Finding $fid: missing required field '$field'")
        fi
    done
    # Recommended fix: accept either casing of "fix"/"Fix"
    if ! grep -qF "Recommended fix:" <<< "$block" && ! grep -qF "Recommended Fix:" <<< "$block"; then
        ERRORS+=("Finding $fid: missing required field 'Recommended fix:'")
    fi

    # Check severity enum
    severity=$(extract_field "Severity:" "$block")
    if [[ -n "$severity" ]] && [[ "$severity" != "Critical" && "$severity" != "Important" && "$severity" != "Minor" ]]; then
        ERRORS+=("Finding $fid: invalid severity '$severity' (must be Critical|Important|Minor)")
    fi

    # Check confidence enum
    confidence=$(extract_field "Confidence:" "$block")
    if [[ -n "$confidence" ]] && [[ "$confidence" != "High" && "$confidence" != "Medium" && "$confidence" != "Low" ]]; then
        ERRORS+=("Finding $fid: invalid confidence '$confidence' (must be High|Medium|Low)")
    fi

    # Check Lines format
    lines_val=$(extract_field "Lines:" "$block")
    if [[ -n "$lines_val" ]] && ! [[ "$lines_val" =~ ^[0-9]+(-[0-9]+)?$ ]]; then
        ERRORS+=("Finding $fid: invalid Lines format '$lines_val' (must be NNN or NNN-NNN)")
    fi

    # Check length caps
    title=$(extract_field "Title:" "$block")
    if [[ ${#title} -gt 200 ]]; then
        ERRORS+=("Finding $fid: Title exceeds 200 chars (${#title})")
    fi

    evidence=$(awk '/^Evidence:/{found=1; next} /^Recommended [Ff]ix:/{exit} found{print}' <<< "$block")
    if [[ ${#evidence} -gt 2000 ]]; then
        ERRORS+=("Finding $fid: Evidence exceeds 2000 chars (${#evidence})")
    fi

    # Evidence threshold check for high-severity findings
    evidence_nows=$(echo "$evidence" | tr -d '[:space:]')
    if [[ ${#evidence_nows} -lt 100 ]] && [[ "$severity" == "Critical" || "$severity" == "Important" ]]; then
        WARNINGS+=("WEAK_EVIDENCE: Finding $fid has ${#evidence_nows} non-whitespace chars in evidence (min 100 for $severity)")
    fi

    fix=$(awk '/^Recommended [Ff]ix:/,/^$|^Finding ID:/' <<< "$block" | tail -n +2)
    if [[ ${#fix} -gt 1000 ]]; then
        ERRORS+=("Finding $fid: Recommended fix exceeds 1000 chars (${#fix})")
    fi

    # Injection heuristic — check ALL free-text fields (Title, Evidence, Recommended fix)
    freetext="$title $evidence $fix"
    check_injection "$freetext" "$fid"

done <<< "$finding_ids"

# Scope confinement check
if [[ -n "$SCOPE_FILE" && -f "$SCOPE_FILE" ]]; then
    while IFS= read -r fid; do
        [[ -z "$fid" ]] && continue
        block=$(awk -v target="Finding ID: $fid" '
            index($0, target) == 1 && length($0) == length(target) {found=1; print; next}
            index($0, target) == 1 && substr($0, length(target)+1, 1) !~ /[0-9]/ {found=1; print; next}
            found && /^Finding ID: [A-Z]+-[0-9]+/ {exit}
            found {print}
        ' <<< "$content" | head -50)
        file_val=$(extract_field "File:" "$block")
        if [[ -n "$file_val" ]] && ! grep -qxF "$file_val" "$SCOPE_FILE"; then
            WARNINGS+=("SCOPE_VIOLATION: File '$file_val' not in review scope (finding $fid)")
        fi
    done <<< "$finding_ids"
fi

# Max findings check
if [[ $MAX_FINDINGS -gt 0 && $FINDING_COUNT -gt $MAX_FINDINGS ]]; then
    ERRORS+=("MAX_FINDINGS_EXCEEDED: $FINDING_COUNT findings exceed limit of $MAX_FINDINGS")
fi

# Destructive pattern check
if [[ "$CHECK_FIXES" == "true" && -f "$SCRIPT_DIR_VALIDATE/../protocols/destructive-patterns.txt" ]]; then
    patterns_file="$SCRIPT_DIR_VALIDATE/../protocols/destructive-patterns.txt"
    while IFS= read -r fid; do
        [[ -z "$fid" ]] && continue
        block=$(awk -v target="Finding ID: $fid" '
            index($0, target) == 1 && length($0) == length(target) {found=1; print; next}
            index($0, target) == 1 && substr($0, length(target)+1, 1) !~ /[0-9]/ {found=1; print; next}
            found && /^Finding ID: [A-Z]+-[0-9]+/ {exit}
            found {print}
        ' <<< "$content" | head -50)
        fix_firstline=$(extract_field "Recommended fix:" "$block")
        [[ -z "$fix_firstline" ]] && fix_firstline=$(extract_field "Recommended Fix:" "$block")
        fix_rest=$(awk '/^Recommended [Ff]ix:/,/^$|^Finding ID:/' <<< "$block" | tail -n +2)
        fix="${fix_firstline}"$'\n'"${fix_rest}"
        while IFS= read -r pattern; do
            [[ "$pattern" =~ ^# ]] && continue
            [[ -z "$pattern" ]] && continue
            if echo "$fix" | grep -qiE "$pattern"; then
                WARNINGS+=("DESTRUCTIVE_PATTERN: Finding $fid recommended fix matches pattern '$pattern'")
            fi
        done < "$patterns_file"
    done <<< "$finding_ids"
fi

# Build JSON output with proper escaping via python3
if [[ ${#ERRORS[@]} -eq 0 ]]; then
    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        python3 -c "
import json, sys
warnings = sys.stdin.read().splitlines()
print(json.dumps({'valid': True, 'errors': [], 'warnings': warnings, 'finding_count': int(sys.argv[1])}))
" "$FINDING_COUNT" < <(printf '%s\n' "${WARNINGS[@]}")
    else
        python3 -c "import json; print(json.dumps({'valid': True, 'errors': [], 'finding_count': int('$FINDING_COUNT')}))"
    fi
    exit 0
else
    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        combined=$(printf '%s\n' "${ERRORS[@]}" "---SEPARATOR---" "${WARNINGS[@]}")
        python3 -c "
import json, sys
lines = sys.stdin.read().split('\n')
sep = lines.index('---SEPARATOR---')
errors, warnings = lines[:sep], lines[sep+1:]
print(json.dumps({'valid': False, 'errors': errors, 'warnings': warnings, 'finding_count': int(sys.argv[1])}))
" "$FINDING_COUNT" <<< "$combined"
    else
        errors_json=$(python3 -c "
import json, sys
errors = sys.stdin.read().splitlines()
print(json.dumps(errors))
" < <(printf '%s\n' "${ERRORS[@]}"))
        echo "{\"valid\": false, \"errors\": $errors_json, \"finding_count\": $FINDING_COUNT}"
    fi
    exit 1
fi
