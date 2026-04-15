#!/usr/bin/env bash
# Deduplicate findings by file + overlapping line range + same specialist category.
# Usage: deduplicate.sh <findings_file> [--cross-specialist]
# Thin wrapper around deduplicate.py for backward compatibility.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/deduplicate.py" "$@"
