#!/usr/bin/env bash
# discover-references.sh - Thin shim delegating to discover_references.py
# See discover_references.py for full usage and documentation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/discover_references.py" "$@"
