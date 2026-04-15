#!/usr/bin/env bash
# Thin shim: delegates to the Python implementation.
# Exit codes: 0 success, 1 error, 2 empty diff
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/build_impact_graph.py" "$@"
