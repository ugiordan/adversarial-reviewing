#!/usr/bin/env bash
# update-references.sh - Fetch and update reference modules with source_url
# Usage: update-references.sh [--check-only] [--test-remote <file>]
# Options:
#   --check-only              Show update summary without modifying files
#   --test-remote <file>      Use local file instead of downloading (for testing)
#   --builtin-dir <path>      Override builtin references directory
#   --user-dir <path>         Override user references directory
#   --project-dir <path>      Override project references directory
# Exit codes: 0 success, 1 error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default directories
BUILTIN_DIR="$SKILL_DIR/references"
USER_DIR="$HOME/.adversarial-review/references"
PROJECT_DIR=".adversarial-review/references"

# Parse arguments
CHECK_ONLY="false"
TEST_REMOTE=""

DIR_OVERRIDES=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --check-only)
            CHECK_ONLY="true"
            shift
            ;;
        --test-remote)
            TEST_REMOTE="${2:?--test-remote requires a file path}"
            shift 2
            ;;
        --builtin-dir)
            BUILTIN_DIR="${2:?--builtin-dir requires a path}"
            DIR_OVERRIDES+=("--builtin-dir" "$BUILTIN_DIR")
            shift 2
            ;;
        --user-dir)
            USER_DIR="${2:?--user-dir requires a path}"
            DIR_OVERRIDES+=("--user-dir" "$USER_DIR")
            shift 2
            ;;
        --project-dir)
            PROJECT_DIR="${2:?--project-dir requires a path}"
            DIR_OVERRIDES+=("--project-dir" "$PROJECT_DIR")
            shift 2
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            echo "Usage: update-references.sh [--check-only] [--test-remote <file>]" >&2
            exit 1
            ;;
        *)
            echo "Error: Unexpected argument: $1" >&2
            echo "Usage: update-references.sh [--check-only] [--test-remote <file>]" >&2
            exit 1
            ;;
    esac
done

# Discover all modules with source_url
DISCOVER_CMD="$SCRIPT_DIR/discover-references.sh"
if [[ ! -x "$DISCOVER_CMD" ]]; then
    echo "Error: discover-references.sh not found or not executable" >&2
    exit 1
fi

# Get all modules (we'll filter by source_url in Python)
modules_json=$("$DISCOVER_CMD" --list-all "${DIR_OVERRIDES[@]}")

# Delegate to Python for version comparison and updates
python3 - "$CHECK_ONLY" "$TEST_REMOTE" "$modules_json" <<'PYTHON_SCRIPT'
import json
import sys
import os
import re
import hashlib
import subprocess
from typing import Dict, Optional, Tuple

def parse_yaml_frontmatter(content: str) -> Optional[Dict]:
    """Parse simple YAML frontmatter (key: value pairs)"""
    if not content.startswith('---'):
        return None

    lines = content.split('\n')
    end_index = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_index = i
            break

    if end_index == -1:
        return None

    frontmatter = {}
    for line in lines[1:end_index]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$', line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()

            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            # Convert boolean strings
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False

            frontmatter[key] = value

    return frontmatter

def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semver versions.
    Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    def parse_semver(v: str) -> Tuple[int, int, int]:
        """Parse semver string into (major, minor, patch)"""
        # Remove 'v' prefix if present
        v = v.lstrip('v')
        parts = v.split('.')
        try:
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)
        except (ValueError, IndexError):
            return (0, 0, 0)

    v1_tuple = parse_semver(v1)
    v2_tuple = parse_semver(v2)

    if v1_tuple < v2_tuple:
        return -1
    elif v1_tuple > v2_tuple:
        return 1
    else:
        return 0

def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

def download_remote(url: str, test_remote: str) -> Optional[str]:
    """Download remote file. Returns content or None on failure."""
    if test_remote:
        # Use test file instead of downloading
        try:
            with open(test_remote, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error: Failed to read test remote file: {e}", file=sys.stderr)
            return None

    # Download with curl
    try:
        result = subprocess.run(
            ['curl', '-f', '-s', '-L', url],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None

def main():
    if len(sys.argv) < 4:
        print("Error: Missing arguments", file=sys.stderr)
        sys.exit(1)

    check_only = sys.argv[1] == "true"
    test_remote = sys.argv[2] if sys.argv[2] else ""
    modules_json_lines = sys.argv[3]

    # Parse modules from JSON lines
    modules = []
    for line in modules_json_lines.strip().split('\n'):
        if not line:
            continue
        try:
            modules.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # Filter modules with source_url
    modules_with_source = [m for m in modules if 'source_url' in m]

    if not modules_with_source:
        print("No modules with source_url found.")
        sys.exit(0)

    # Process each module
    updates = []

    for module in modules_with_source:
        name = module['name']
        local_path = module['path']
        source_url = module['source_url']
        local_version = module.get('version', '0.0.0')

        # Read local content
        try:
            with open(local_path, 'r') as f:
                local_content = f.read()
        except Exception as e:
            print(f"Warning: Failed to read {local_path}: {e}", file=sys.stderr)
            continue

        # Download remote content
        remote_content = download_remote(source_url, test_remote)
        if remote_content is None:
            print(f"Warning: Failed to download {source_url} for module '{name}'", file=sys.stderr)
            continue

        # Parse remote frontmatter
        remote_metadata = parse_yaml_frontmatter(remote_content)
        if not remote_metadata:
            print(f"Warning: Malformed frontmatter in remote {source_url} for module '{name}'", file=sys.stderr)
            continue

        remote_version = remote_metadata.get('version', '0.0.0')

        # Compare versions
        version_cmp = compare_versions(local_version, remote_version)

        # Fallback to content hash if versions are equal
        status = ""
        if version_cmp < 0:
            status = "update_available"
        elif version_cmp > 0:
            status = "local_newer"
        else:
            # Same version - check hash
            local_hash = compute_hash(local_content)
            remote_hash = compute_hash(remote_content)
            if local_hash == remote_hash:
                status = "up_to_date"
            else:
                status = "content_differs"

        updates.append({
            'name': name,
            'path': local_path,
            'local_version': local_version,
            'remote_version': remote_version,
            'status': status,
            'remote_content': remote_content
        })

    # Display summary
    print(f"Found {len(modules_with_source)} module(s) with source_url\n")

    for update in updates:
        name = update['name']
        local_ver = update['local_version']
        remote_ver = update['remote_version']
        status = update['status']

        status_display = {
            'update_available': f'UPDATE AVAILABLE ({local_ver} → {remote_ver})',
            'local_newer': f'LOCAL NEWER ({local_ver} > {remote_ver})',
            'up_to_date': 'UP TO DATE',
            'content_differs': f'CONTENT DIFFERS (same version: {local_ver})'
        }

        print(f"  {name}: {status_display.get(status, status)}")

    # If check-only, exit here
    if check_only:
        print("\n--check-only mode: no files modified")
        sys.exit(0)

    # Interactive update
    print()
    updates_applied = 0
    for update in updates:
        if update['status'] in ['update_available', 'content_differs']:
            name = update['name']
            path = update['path']
            remote_content = update['remote_content']

            # Prompt for confirmation
            try:
                response = input(f"Update {name}? [y/n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                sys.exit(1)

            if response == 'y':
                try:
                    with open(path, 'w') as f:
                        f.write(remote_content)
                    print(f"  Updated {name}")
                    updates_applied += 1
                except Exception as e:
                    print(f"  Error updating {name}: {e}", file=sys.stderr)

    print(f"\nApplied {updates_applied} update(s)")

if __name__ == "__main__":
    main()
PYTHON_SCRIPT
