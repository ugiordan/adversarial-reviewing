#!/usr/bin/env bash
# discover-references.sh - Discover and filter reference modules for specialists
# Usage: discover-references.sh <specialist> [--check-staleness] [--token-count]
#        discover-references.sh --list-all [--check-staleness] [--token-count]
# Directories can be overridden with: --builtin-dir, --user-dir, --project-dir
# Exit codes: 0 success, 1 error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default directories
BUILTIN_DIR="$SKILL_DIR/references"
USER_DIR="$HOME/.adversarial-review/references"
PROJECT_DIR=".adversarial-review/references"

# Parse arguments
SPECIALIST=""
LIST_ALL="false"
CHECK_STALENESS="false"
TOKEN_COUNT="false"
BUDGET_CHECK="false"
TOTAL_BUDGET=0
TRUNCATE_BUDGET="false"
PER_ITERATION_BUDGET=0
IMPACT_GRAPH_TOKENS_ARG=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --list-all)
            LIST_ALL="true"
            shift
            ;;
        --check-staleness)
            CHECK_STALENESS="true"
            shift
            ;;
        --token-count)
            TOKEN_COUNT="true"
            shift
            ;;
        --builtin-dir)
            BUILTIN_DIR="${2:?--builtin-dir requires a path}"
            shift 2
            ;;
        --user-dir)
            USER_DIR="${2:?--user-dir requires a path}"
            shift 2
            ;;
        --project-dir)
            PROJECT_DIR="${2:?--project-dir requires a path}"
            shift 2
            ;;
        --budget-check)
            BUDGET_CHECK="true"
            TOTAL_BUDGET="${2:?--budget-check requires total budget}"
            shift 2
            ;;
        --truncate-budget)
            TRUNCATE_BUDGET="true"
            PER_ITERATION_BUDGET="${2:?--truncate-budget requires per-iteration budget}"
            IMPACT_GRAPH_TOKENS_ARG="${3:?--truncate-budget requires impact_graph_tokens}"
            shift 3
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            echo "Usage: discover-references.sh <specialist> [--check-staleness] [--token-count]" >&2
            echo "       discover-references.sh --list-all [--check-staleness] [--token-count]" >&2
            exit 1
            ;;
        *)
            if [[ -z "$SPECIALIST" ]]; then
                SPECIALIST="$1"
            else
                echo "Error: Unexpected argument: $1" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [[ "$LIST_ALL" == "false" && -z "$SPECIALIST" ]]; then
    echo "Error: Specialist required (or use --list-all)" >&2
    echo "Usage: discover-references.sh <specialist> [--check-staleness] [--token-count]" >&2
    echo "       discover-references.sh --list-all [--check-staleness] [--token-count]" >&2
    exit 1
fi

# Delegate to Python for YAML parsing and JSON output
python3 - "$SPECIALIST" "$LIST_ALL" "$CHECK_STALENESS" "$TOKEN_COUNT" "$BUILTIN_DIR" "$USER_DIR" "$PROJECT_DIR" "$BUDGET_CHECK" "$TOTAL_BUDGET" "$TRUNCATE_BUDGET" "$PER_ITERATION_BUDGET" "$IMPACT_GRAPH_TOKENS_ARG" <<'PYTHON_SCRIPT'
import json
import sys
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def parse_yaml_frontmatter(content: str) -> Optional[Dict]:
    """Parse simple YAML frontmatter (key: value pairs)"""
    # Check for frontmatter delimiters
    if not content.startswith('---'):
        return None

    # Find the closing delimiter
    lines = content.split('\n')
    end_index = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_index = i
            break

    if end_index == -1:
        return None

    # Parse key: value pairs
    frontmatter = {}
    for line in lines[1:end_index]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Simple key: value parsing
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

def is_stale(last_updated: str) -> bool:
    """Check if a module is stale (> 90 days old)"""
    try:
        # Parse ISO date (YYYY-MM-DD)
        update_date = datetime.strptime(last_updated, "%Y-%m-%d")
        age = datetime.now() - update_date
        return age > timedelta(days=90)
    except (ValueError, TypeError):
        return False

def estimate_tokens(content: str) -> int:
    """Estimate token count (chars/4 heuristic)"""
    return len(content) // 4

def discover_modules_in_dir(base_dir: str, specialist: str, list_all: bool, layer_priority: int) -> List[Tuple[Dict, str, int, str]]:
    """
    Discover modules in a directory.
    Returns list of (metadata, file_path, layer_priority, content) tuples.
    layer_priority: 1=builtin, 2=user, 3=project (higher overrides lower)
    """
    modules = []

    if not os.path.isdir(base_dir):
        return modules

    # Specialist subdirectories
    specialist_dirs = ['security', 'performance', 'quality', 'correctness', 'architecture']

    # Discover from specialist subdirectory
    if list_all:
        # Scan all specialist subdirectories
        for subdir in specialist_dirs:
            subdir_path = os.path.join(base_dir, subdir)
            if os.path.isdir(subdir_path):
                modules.extend(scan_directory(subdir_path, layer_priority))
    else:
        # Scan only the specialist subdirectory
        specialist_subdir = os.path.join(base_dir, specialist)
        if os.path.isdir(specialist_subdir):
            modules.extend(scan_directory(specialist_subdir, layer_priority))

    # Discover from 'all' subdirectory (always included)
    all_dir = os.path.join(base_dir, 'all')
    if os.path.isdir(all_dir):
        modules.extend(scan_directory(all_dir, layer_priority))

    # Discover from root-level *.md files (only for specialist: all matching)
    # Root-level files are only discovered if they have specialist: all
    for entry in os.listdir(base_dir):
        if entry.endswith('.md'):
            file_path = os.path.join(base_dir, entry)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()

                    metadata = parse_yaml_frontmatter(content)
                    if metadata and metadata.get('specialist') == 'all':
                        modules.append((metadata, file_path, layer_priority, content))
                except Exception:
                    # Skip files we can't read
                    pass

    return modules

def scan_directory(directory: str, layer_priority: int) -> List[Tuple[Dict, str, int, str]]:
    """Scan a directory for .md files and return (metadata, path, priority, content) tuples"""
    modules = []

    for entry in os.listdir(directory):
        if entry.endswith('.md'):
            file_path = os.path.join(directory, entry)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()

                    metadata = parse_yaml_frontmatter(content)
                    if metadata:
                        modules.append((metadata, file_path, layer_priority, content))
                except Exception:
                    # Skip files we can't read
                    pass

    return modules

def main():
    if len(sys.argv) < 13:
        print("Error: Missing arguments", file=sys.stderr)
        sys.exit(1)

    specialist = sys.argv[1]
    list_all = sys.argv[2] == "true"
    check_staleness = sys.argv[3] == "true"
    token_count = sys.argv[4] == "true"
    builtin_dir = sys.argv[5]
    user_dir = sys.argv[6]
    project_dir = sys.argv[7]
    budget_check = sys.argv[8] == "true"
    total_budget = int(sys.argv[9])
    truncate_budget = sys.argv[10] == "true"
    per_iteration_budget = int(sys.argv[11])
    impact_graph_tokens = int(sys.argv[12])

    # Discover modules from all three layers
    all_modules = []

    # Layer 1: Builtin (priority 1)
    all_modules.extend(discover_modules_in_dir(builtin_dir, specialist, list_all, 1))

    # Layer 2: User (priority 2)
    all_modules.extend(discover_modules_in_dir(user_dir, specialist, list_all, 2))

    # Layer 3: Project (priority 3)
    all_modules.extend(discover_modules_in_dir(project_dir, specialist, list_all, 3))

    # Process and validate modules
    validated_modules = []

    for metadata, file_path, layer_priority, content in all_modules:
        # Check required fields
        name = metadata.get('name')
        module_specialist = metadata.get('specialist')
        enabled = metadata.get('enabled')

        if not name:
            print(f"Warning: Skipping {file_path}: missing 'name' field", file=sys.stderr)
            continue

        if not module_specialist:
            print(f"Warning: Skipping {file_path}: missing 'specialist' field", file=sys.stderr)
            continue

        if enabled is None:
            print(f"Warning: Skipping {file_path}: missing 'enabled' field", file=sys.stderr)
            continue

        # Filter by enabled
        if enabled is not True:
            continue

        # Filter by specialist (unless list_all)
        if not list_all:
            if module_specialist != specialist and module_specialist != 'all':
                continue

        # Build module record
        module = {
            'name': name,
            'specialist': module_specialist,
            'version': metadata.get('version', '0.0.0'),
            'enabled': enabled,
            'path': file_path,
            'layer_priority': layer_priority,
            '_body': content,  # Store for budget calculations
        }

        # Add optional fields
        if 'last_updated' in metadata:
            module['last_updated'] = metadata['last_updated']

        if 'source_url' in metadata:
            module['source_url'] = metadata['source_url']

        if 'description' in metadata:
            module['description'] = metadata['description']

        # Token counting
        if token_count:
            module['tokens'] = estimate_tokens(content)

        # Staleness checking
        stale = False
        if check_staleness and 'last_updated' in metadata:
            if is_stale(metadata['last_updated']):
                stale = True
                print(f"Warning: Module '{name}' is stale (last_updated: {metadata['last_updated']})", file=sys.stderr)

        if check_staleness:
            module['stale'] = stale

        validated_modules.append(module)

    # Deduplicate by (name, specialist) — higher layer priority wins
    deduped = {}
    for module in validated_modules:
        key = (module['name'], module['specialist'])

        if key not in deduped:
            deduped[key] = module
        else:
            # Higher layer priority overwrites
            if module['layer_priority'] > deduped[key]['layer_priority']:
                deduped[key] = module

    # Convert to list and remove layer_priority field (internal only)
    final_modules = []
    for module in deduped.values():
        del module['layer_priority']
        final_modules.append(module)

    # Sort by filename (basename of path)
    final_modules.sort(key=lambda m: os.path.basename(m['path']))

    # Budget warning logic (B.10)
    if budget_check and total_budget > 0:
        specialist_tokens = {}
        for mod in final_modules:
            spec = mod.get('specialist', 'unknown')
            body_tokens = len(mod.get('_body', '')) // 4
            specialist_tokens[spec] = specialist_tokens.get(spec, 0) + body_tokens

        threshold_3pct = total_budget * 0.03
        threshold_10pct = total_budget * 0.10
        total_ref_tokens = sum(specialist_tokens.values())

        for spec, tokens in specialist_tokens.items():
            if tokens > threshold_3pct:
                print(f"Warning: Reference tokens for {spec} ({tokens}) exceed "
                      f"3% of total budget ({int(threshold_3pct)})", file=sys.stderr)

        if total_ref_tokens > threshold_10pct:
            print(f"Warning: Total reference tokens ({total_ref_tokens}) exceed "
                  f"10% of total budget ({int(threshold_10pct)})", file=sys.stderr)

    # Truncation logic (B.8)
    if truncate_budget and per_iteration_budget > 0:
        total_ref_tokens = sum(len(m.get('_body', '')) // 4 for m in final_modules)
        threshold_80pct = per_iteration_budget * 0.80
        combined = total_ref_tokens + impact_graph_tokens

        if combined > threshold_80pct:
            available = max(0, int(threshold_80pct - impact_graph_tokens))
            sorted_mods = sorted(final_modules, key=lambda m: len(m.get('_body', '')), reverse=True)
            running_total = 0
            for mod in sorted_mods:
                body_tokens = len(mod.get('_body', '')) // 4
                if running_total + body_tokens > available:
                    mod['_truncated'] = True
                    mod['_body'] = (f"[Reference truncated due to token budget constraints. "
                                    f"Module: {mod['name']} v{mod.get('version', '0.0.0')} "
                                    f"— {mod.get('description', '')}]")
                else:
                    running_total += body_tokens

    # Output as JSON lines
    for module in final_modules:
        # Build output object (exclude internal fields)
        output = {k: v for k, v in module.items() if not k.startswith('_')}

        # Add truncated flag if present
        if module.get('_truncated'):
            output['truncated'] = True

        print(json.dumps(output))

if __name__ == "__main__":
    main()
PYTHON_SCRIPT
