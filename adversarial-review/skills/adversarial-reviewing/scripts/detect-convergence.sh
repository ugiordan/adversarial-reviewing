#!/usr/bin/env bash
# Compare finding sets between iterations to detect convergence.
# Usage: detect-convergence.sh <iteration_n_file> <iteration_n_minus_1_file>
# Output: JSON with converged (bool), diff summary
# Exit 0 if converged, exit 1 if not converged.

set -euo pipefail

# Parse optional --triage flag
TRIAGE_MODE=false
if [[ "${1:-}" == "--triage" ]]; then
    TRIAGE_MODE=true
    shift
fi

if ! command -v python3 &>/dev/null; then
    echo '{"error": "python3 is required but not found"}' >&2
    exit 2
fi

CURRENT="${1:?Usage: detect-convergence.sh <current_iteration> <previous_iteration>}"
PREVIOUS="${2:?Usage: detect-convergence.sh <current_iteration> <previous_iteration>}"

# Script-level temp file tracking and cleanup
CONVERGENCE_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/convergence_XXXXXXXXXX")
cleanup() { # called via trap
    rm -rf "$CONVERGENCE_TMPDIR"
}
trap cleanup EXIT INT TERM

# Extract Finding ID + Severity pairs, sorted
extract_signature() {
    local file="$1"
    local tmpfile
    tmpfile=$(mktemp "$CONVERGENCE_TMPDIR/ids_XXXXXXXXXX")
    # Portable extraction of Finding IDs (no grep -oP)
    sed -n 's/^Finding ID: \([A-Z][A-Z]*-[0-9][0-9]*\).*/\1/p' "$file" | sort > "$tmpfile" || true
    while IFS= read -r fid; do
        # Validate finding ID format before using in AWK
        if ! [[ "$fid" =~ ^[A-Z]+-[0-9]+$ ]]; then
            continue
        fi
        # Pass fid via -v; use index() for literal match (avoids regex metachar issues with +)
        # Suffix-digit guard prevents SEC-1 from matching SEC-10
        severity=$(awk -v target="Finding ID: $fid" '
            index($0, target) == 1 && length($0) == length(target) {found=1; next}
            index($0, target) == 1 && substr($0, length(target)+1, 1) !~ /[0-9]/ {found=1; next}
            found && /^Finding ID:/ {exit}
            found && /^Severity:/ {print; exit}
        ' "$file" | sed -n 's/^Severity: *\([A-Za-z]*\).*/\1/p' | head -1)
        echo "$fid:$severity"
    done < "$tmpfile" | sort
}

# Extract Triage ID + Verdict pairs for triage mode
extract_triage_signature() {
    local file="$1"
    local tmpfile
    tmpfile=$(mktemp "$CONVERGENCE_TMPDIR/triage_ids_XXXXXXXXXX")
    sed -n 's/^Triage ID: \(TRIAGE-[A-Z]*-[0-9]*\).*/\1/p' "$file" | sort > "$tmpfile"
    while IFS= read -r tid; do
        [[ -z "$tid" ]] && continue
        verdict=$(awk -v target="Triage ID: $tid" '
            index($0, target) == 1 && length($0) == length(target) {found=1; next}
            index($0, target) == 1 && substr($0, length(target)+1, 1) !~ /[0-9]/ {found=1; next}
            found && /^Triage ID:/ {exit}
            found && /^Verdict:/ {print; exit}
        ' "$file" | sed -n 's/^Verdict: *\([A-Za-z-]*\).*/\1/p' | head -1)
        echo "$tid:$verdict"
    done < "$tmpfile" | sort
}

if [[ "$TRIAGE_MODE" == true ]]; then
    CURRENT_SIG=$(extract_triage_signature "$CURRENT")
    PREVIOUS_SIG=$(extract_triage_signature "$PREVIOUS")
else
    CURRENT_SIG=$(extract_signature "$CURRENT")
    PREVIOUS_SIG=$(extract_signature "$PREVIOUS")
fi

if [[ "$CURRENT_SIG" == "$PREVIOUS_SIG" ]]; then
    echo '{"converged": true, "added": [], "removed": []}'
    exit 0
else
    # Handle empty signatures: if either is empty, use /dev/null for comm
    added=$(comm -23 <(if [[ -n "$CURRENT_SIG" ]]; then echo "$CURRENT_SIG"; else cat /dev/null; fi) \
                      <(if [[ -n "$PREVIOUS_SIG" ]]; then echo "$PREVIOUS_SIG"; else cat /dev/null; fi))
    removed=$(comm -13 <(if [[ -n "$CURRENT_SIG" ]]; then echo "$CURRENT_SIG"; else cat /dev/null; fi) \
                        <(if [[ -n "$PREVIOUS_SIG" ]]; then echo "$PREVIOUS_SIG"; else cat /dev/null; fi))
    python3 -c "
import json, sys
added = [x for x in sys.argv[1].splitlines() if x]
removed = [x for x in sys.argv[2].splitlines() if x]
print(json.dumps({'converged': False, 'added': added, 'removed': removed}))
" "$added" "$removed"
    exit 1
fi
