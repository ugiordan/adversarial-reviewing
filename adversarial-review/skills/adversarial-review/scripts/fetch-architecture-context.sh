#!/usr/bin/env bash
set -euo pipefail

# DEPRECATED: Use fetch-context.sh --label architecture --source <url_or_path>
# This wrapper exists for backward compatibility only.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REPO=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --repo) REPO="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --strategies) shift 2 ;; # ignored in new version
    *) shift ;;
  esac
done

REPO="${REPO:-https://github.com/opendatahub-io/architecture-context.git}"
OUTPUT="${OUTPUT:-.context/architecture-context}"

exec "$SCRIPT_DIR/fetch-context.sh" --label architecture --source "$REPO" --output "$OUTPUT"
