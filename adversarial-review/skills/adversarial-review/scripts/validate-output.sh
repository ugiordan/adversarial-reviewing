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

ERRORS=()
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

    fix=$(awk '/^Recommended [Ff]ix:/,/^$|^Finding ID:/' <<< "$block" | tail -n +2)
    if [[ ${#fix} -gt 1000 ]]; then
        ERRORS+=("Finding $fid: Recommended fix exceeds 1000 chars (${#fix})")
    fi

    # Injection heuristic — check ALL free-text fields (Title, Evidence, Recommended fix)
    freetext="$title $evidence $fix"
    freetext_lower=$(echo "$freetext" | tr '[:upper:]' '[:lower:]')

    # Two-tier injection detection: high-confidence patterns always flag,
    # context-sensitive patterns require 2+ matches to flag
    injection_patterns_high=(
        "ignore all previous" "ignore all instructions" "disregard previous"
        "disregard all" "system prompt" "discard previous" "new instructions"
        "real task" "you are now" "forget your" "ignore the above"
    )
    injection_patterns_context=(
        "you must" "you should" "override" "set aside" "supersede"
        "abandon" "authoritative" "ignore all" "disregard"
    )

    for pattern in "${injection_patterns_high[@]}"; do
        if grep -qF "$pattern" <<< "$freetext_lower"; then
            ERRORS+=("Finding $fid: injection pattern detected: '$pattern'")
        fi
    done

    # Context-sensitive: require 2+ matches to reduce false positives
    context_hits=0
    context_matched=()
    for pattern in "${injection_patterns_context[@]}"; do
        if grep -qF "$pattern" <<< "$freetext_lower"; then
            context_hits=$((context_hits + 1))
            context_matched+=("$pattern")
        fi
    done
    if (( context_hits >= 2 )); then
        ERRORS+=("Finding $fid: multiple injection patterns detected: ${context_matched[*]}")
    fi

    # Check for provenance marker patterns
    if grep -qF "[PROVENANCE::" <<< "$freetext"; then
        ERRORS+=("Finding $fid: contains provenance marker pattern in field content")
    fi

    # Check for field isolation marker patterns
    if grep -qF "[FIELD_DATA_" <<< "$freetext"; then
        ERRORS+=("Finding $fid: contains field isolation marker pattern in field content")
    fi

done <<< "$finding_ids"

# Build JSON output with proper escaping via python3
if [[ ${#ERRORS[@]} -eq 0 ]]; then
    python3 -c "import json; print(json.dumps({'valid': True, 'errors': [], 'finding_count': int('$FINDING_COUNT')}))"
    exit 0
else
    errors_json=$(python3 -c "
import json, sys
errors = sys.stdin.read().splitlines()
print(json.dumps(errors))
" < <(printf '%s\n' "${ERRORS[@]}"))
    echo "{\"valid\": false, \"errors\": $errors_json, \"finding_count\": $FINDING_COUNT}"
    exit 1
fi
