#!/usr/bin/env bash
# Normalize external review comments into JSON lines format.
# Usage: parse-comments.sh <source_type> <input_file>
# Thin wrapper around parse_comments.py for backward compatibility.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/parse_comments.py" "$@"
