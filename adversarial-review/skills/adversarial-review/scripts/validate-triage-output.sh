#!/usr/bin/env bash
# Validate triage output against triage verdict schema and discovery findings.
# Usage: validate-triage-output.sh <output_file> <expected_role_prefix>
# Output: JSON with valid (bool), errors (array), triage_count (int), discovery_count (int)
# Exit 0 if valid, exit 1 if invalid.

set -euo pipefail

# Require python3 upfront (used for unicode normalization and JSON serialization)
if ! command -v python3 &>/dev/null; then
    echo '{"error": "python3 is required but not found"}' >&2
    exit 2
fi

OUTPUT_FILE="${1:?Usage: validate-triage-output.sh <output_file> <expected_role_prefix>}"
ROLE_PREFIX="${2:?Usage: validate-triage-output.sh <output_file> <expected_role_prefix>}"

ERRORS=()
TRIAGE_COUNT=0
DISCOVERY_COUNT=0

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

# Check for NO_TRIAGE_EVALUATIONS marker (zero triage verdicts, but discovery findings may follow)
ZERO_TRIAGE=false
if grep -qF "NO_TRIAGE_EVALUATIONS" <<< "$content"; then
    ZERO_TRIAGE=true
fi

if [[ "$ZERO_TRIAGE" == false ]]; then

# Extract triage IDs (TRIAGE-ROLE-NNN format)
triage_ids=$(echo "$content" | sed -n 's/^Triage ID: \(TRIAGE-[A-Z]*-[0-9]*\).*/\1/p')

# Process triage verdicts
while IFS= read -r tid; do
    [[ -z "$tid" ]] && continue
    TRIAGE_COUNT=$((TRIAGE_COUNT + 1))

    # Validate triage ID format strictly
    if ! [[ "$tid" =~ ^TRIAGE-[A-Z]+-[0-9]+$ ]]; then
        ERRORS+=("Triage ID '$tid' contains invalid characters")
        continue
    fi

    # Check role prefix (extract middle part: TRIAGE-ROLE-NNN → ROLE)
    prefix=$(echo "$tid" | sed 's/^TRIAGE-//;s/-[0-9]*$//')
    if [[ "$prefix" != "$ROLE_PREFIX" ]]; then
        ERRORS+=("Triage $tid: prefix '$prefix' does not match expected '$ROLE_PREFIX'")
    fi

    # Extract the triage block
    block=$(awk -v target="Triage ID: $tid" '
        index($0, target) == 1 && length($0) == length(target) {found=1; print; next}
        index($0, target) == 1 && substr($0, length(target)+1, 1) !~ /[0-9]/ {found=1; print; next}
        found && /^(Triage ID:|Finding ID:)/ {exit}
        found {print}
    ' <<< "$content" | head -100)

    # Check required fields
    for field in "External Comment ID:" "Specialist:" "Verdict:" "Confidence:" "Severity-If-Fix:" "File:" "Lines:" "Comment Summary:" "Analysis:" "Recommended Action:"; do
        if ! grep -qF "$field" <<< "$block"; then
            ERRORS+=("Triage $tid: missing required field '$field'")
        fi
    done

    # Validate External Comment ID format (EXT-NNN)
    ext_id=$(extract_field "External Comment ID:" "$block")
    if [[ -n "$ext_id" ]] && ! [[ "$ext_id" =~ ^EXT-[0-9]+$ ]]; then
        ERRORS+=("Triage $tid: invalid External Comment ID '$ext_id' (must be EXT-NNN)")
    fi

    # Validate Verdict enum
    verdict=$(extract_field "Verdict:" "$block")
    if [[ -n "$verdict" ]] && [[ "$verdict" != "Fix" && "$verdict" != "No-Fix" && "$verdict" != "Investigate" ]]; then
        ERRORS+=("Triage $tid: invalid verdict '$verdict' (must be Fix|No-Fix|Investigate)")
    fi

    # Validate Confidence enum
    confidence=$(extract_field "Confidence:" "$block")
    if [[ -n "$confidence" ]] && [[ "$confidence" != "High" && "$confidence" != "Medium" && "$confidence" != "Low" ]]; then
        ERRORS+=("Triage $tid: invalid confidence '$confidence' (must be High|Medium|Low)")
    fi

    # Validate Severity-If-Fix conditional
    severity_if_fix=$(extract_field "Severity-If-Fix:" "$block")
    if [[ "$verdict" == "Fix" ]]; then
        # When verdict is Fix, Severity-If-Fix must be a valid severity
        if [[ "$severity_if_fix" != "Critical" && "$severity_if_fix" != "Important" && "$severity_if_fix" != "Minor" ]]; then
            ERRORS+=("Triage $tid: Verdict=Fix requires Severity-If-Fix to be Critical|Important|Minor, got '$severity_if_fix'")
        fi
    elif [[ "$verdict" == "No-Fix" || "$verdict" == "Investigate" ]]; then
        # When verdict is No-Fix or Investigate, Severity-If-Fix must be N/A
        if [[ "$severity_if_fix" != "N/A" ]]; then
            ERRORS+=("Triage $tid: Verdict=$verdict requires Severity-If-Fix to be N/A, got '$severity_if_fix'")
        fi
    fi

    # Check Lines format (N/A valid for general/file-level comments)
    lines_val=$(extract_field "Lines:" "$block")
    if [[ -n "$lines_val" ]] && ! [[ "$lines_val" =~ ^([0-9]+(-[0-9]+)?|N/A)$ ]]; then
        ERRORS+=("Triage $tid: invalid Lines format '$lines_val' (must be NNN, NNN-NNN, or N/A)")
    fi

    # Check length caps
    comment_summary=$(extract_field "Comment Summary:" "$block")
    if [[ ${#comment_summary} -gt 500 ]]; then
        ERRORS+=("Triage $tid: Comment Summary exceeds 500 chars (${#comment_summary})")
    fi

    # Extract Analysis field (may be inline or multi-line)
    analysis=$(awk '
        /^Analysis:/ {
            found=1
            # Get inline content after "Analysis:"
            sub(/^Analysis:[[:space:]]*/, "")
            if (length($0) > 0) print
            next
        }
        /^Recommended Action:/ {exit}
        found {print}
    ' <<< "$block")
    if [[ ${#analysis} -gt 2000 ]]; then
        ERRORS+=("Triage $tid: Analysis exceeds 2000 chars (${#analysis})")
    fi

    # Extract Recommended Action field (may be inline or multi-line)
    action=$(awk '
        /^Recommended Action:/ {
            found=1
            # Get inline content after "Recommended Action:"
            sub(/^Recommended Action:[[:space:]]*/, "")
            if (length($0) > 0) print
            next
        }
        /^$|^(Triage ID:|Finding ID:)/ {if (found) exit}
        found {print}
    ' <<< "$block")
    if [[ ${#action} -gt 1000 ]]; then
        ERRORS+=("Triage $tid: Recommended Action exceeds 1000 chars (${#action})")
    fi

    # Injection heuristic — check ALL free-text fields
    freetext="$comment_summary $analysis $action"
    check_injection "$freetext" "$tid"

done <<< "$triage_ids"

fi  # end ZERO_TRIAGE check

# Extract and process discovery findings (ROLE-NNN format, not TRIAGE-ROLE-NNN)
finding_ids=$(echo "$content" | sed -n 's/^Finding ID: \([A-Z]*-[0-9]*\).*/\1/p' | grep -v '^TRIAGE-' || true)

while IFS= read -r fid; do
    [[ -z "$fid" ]] && continue
    DISCOVERY_COUNT=$((DISCOVERY_COUNT + 1))

    # Validate finding ID format strictly
    if ! [[ "$fid" =~ ^[A-Z]+-[0-9]+$ ]]; then
        ERRORS+=("Finding ID '$fid' contains invalid characters")
        continue
    fi

    # Check role prefix
    prefix=$(echo "$fid" | sed 's/-.*//')
    if [[ "$prefix" != "$ROLE_PREFIX" ]]; then
        ERRORS+=("Finding $fid: prefix '$prefix' does not match expected '$ROLE_PREFIX'")
    fi

    # Extract the finding block
    block=$(awk -v target="Finding ID: $fid" '
        index($0, target) == 1 && length($0) == length(target) {found=1; print; next}
        index($0, target) == 1 && substr($0, length(target)+1, 1) !~ /[0-9]/ {found=1; print; next}
        found && /^(Finding ID:|Triage ID:)/ {exit}
        found {print}
    ' <<< "$content" | head -100)

    # Check required fields for discovery findings
    for field in "Specialist:" "Severity:" "Confidence:" "File:" "Lines:" "Title:" "Evidence:"; do
        if ! grep -qF "$field" <<< "$block"; then
            ERRORS+=("Finding $fid: missing required field '$field'")
        fi
    done
    if ! grep -qF "Recommended fix:" <<< "$block" && ! grep -qF "Recommended Fix:" <<< "$block"; then
        ERRORS+=("Finding $fid: missing required field 'Recommended fix:'")
    fi

    # Check for Source: Triage-Discovery marker (discovery findings should have this)
    if ! grep -qF "Source: Triage-Discovery" <<< "$block"; then
        ERRORS+=("Finding $fid: missing 'Source: Triage-Discovery' marker")
    fi

    # Check for Related-Comment field
    if ! grep -qF "Related-Comment:" <<< "$block"; then
        ERRORS+=("Finding $fid: missing 'Related-Comment:' field")
    fi

    # Validate severity enum
    severity=$(extract_field "Severity:" "$block")
    if [[ -n "$severity" ]] && [[ "$severity" != "Critical" && "$severity" != "Important" && "$severity" != "Minor" ]]; then
        ERRORS+=("Finding $fid: invalid severity '$severity' (must be Critical|Important|Minor)")
    fi

    # Validate confidence enum
    confidence=$(extract_field "Confidence:" "$block")
    if [[ -n "$confidence" ]] && [[ "$confidence" != "High" && "$confidence" != "Medium" && "$confidence" != "Low" ]]; then
        ERRORS+=("Finding $fid: invalid confidence '$confidence' (must be High|Medium|Low)")
    fi

    # Check Lines format (N/A valid for general/file-level comments)
    lines_val=$(extract_field "Lines:" "$block")
    if [[ -n "$lines_val" ]] && ! [[ "$lines_val" =~ ^([0-9]+(-[0-9]+)?|N/A)$ ]]; then
        ERRORS+=("Finding $fid: invalid Lines format '$lines_val' (must be NNN, NNN-NNN, or N/A)")
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

    fix=$(awk '/^Recommended [Ff]ix:/,/^$|^(Finding ID:|Triage ID:)/' <<< "$block" | tail -n +2)
    if [[ ${#fix} -gt 1000 ]]; then
        ERRORS+=("Finding $fid: Recommended fix exceeds 1000 chars (${#fix})")
    fi

    # Injection heuristic
    freetext="$title $evidence $fix"
    check_injection "$freetext" "$fid"

done <<< "$finding_ids"

# Build JSON output with proper escaping via python3
if [[ ${#ERRORS[@]} -eq 0 ]]; then
    python3 -c "import json; d={'valid': True, 'errors': [], 'triage_count': int('$TRIAGE_COUNT'), 'discovery_count': int('$DISCOVERY_COUNT')}; d.update({'zero_evaluations': True} if '$ZERO_TRIAGE' == 'true' else {}); print(json.dumps(d))"
    exit 0
else
    errors_json=$(python3 -c "
import json, sys
errors = sys.stdin.read().splitlines()
print(json.dumps(errors))
" < <(printf '%s\n' "${ERRORS[@]}"))
    echo "{\"valid\": false, \"errors\": $errors_json, \"triage_count\": $TRIAGE_COUNT, \"discovery_count\": $DISCOVERY_COUNT}"
    exit 1
fi
