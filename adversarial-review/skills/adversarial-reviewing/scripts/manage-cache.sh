#!/usr/bin/env bash
# Thin shim: delegates all cache management to the Python implementation.
# See manage_cache.py for full documentation.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/manage_cache.py" "$@"
