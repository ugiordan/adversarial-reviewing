#!/usr/bin/env bash
# Format and emit an audit log entry per protocols/audit-log.md.
# Usage: write-audit-log.sh <service> <operation> [key=value ...] [--dry-run]
# Output: Formatted entry to stdout

set -euo pipefail

SERVICE="${1:?Usage: write-audit-log.sh <service> <operation> [key=value ...] [--dry-run]}"
OPERATION="${2:?Usage: write-audit-log.sh <service> <operation> [key=value ...] [--dry-run]}"
shift 2

DRY_RUN=false
KV_PAIRS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        *)
            # Reject values containing newlines (log injection)
            if [[ "$1" == *$'\n'* ]]; then
                echo "ERROR: key=value pair contains newline: ${1%%$'\n'*}..." >&2
                exit 1
            fi
            # Validate key=value format
            if [[ "$1" != *=* ]]; then
                echo "ERROR: invalid key=value pair (missing '='): $1" >&2
                exit 1
            fi
            KV_PAIRS+=("$1"); shift ;;
    esac
done

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
KV_STRING="${KV_PAIRS[*]:-}"

# Build the entry, omitting trailing space when no kv pairs
ENTRY="${SERVICE}.${OPERATION}"
if [[ -n "$KV_STRING" ]]; then
    ENTRY="${ENTRY} ${KV_STRING}"
fi

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY-RUN] [$TIMESTAMP] ACTION: ${ENTRY}"
else
    echo "[$TIMESTAMP] ACTION: ${ENTRY}"
fi
