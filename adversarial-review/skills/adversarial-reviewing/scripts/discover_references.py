#!/usr/bin/env python3
"""discover_references.py - Discover and filter reference modules for specialists.

Usage:
    discover_references.py <specialist>  [--check-staleness] [--token-count]
    discover_references.py --list-all    [--check-staleness] [--token-count]

Directories can be overridden with: --builtin-dir, --user-dir, --project-dir, --extra-dir
Exit codes: 0 success, 1 error
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
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

    # Dynamically discover specialist subdirectories (excludes 'all', handled separately)
    specialist_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d != 'all']

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


def matches_finding_categories(module: Dict, finding_categories: list[str]) -> bool:
    """Check if a module is relevant to the given finding categories.

    Matches against the module's 'categories' frontmatter field (comma-separated)
    and the module's 'description' field. Case-insensitive substring matching.
    """
    if not finding_categories:
        return True  # No filter, everything matches

    # Check categories frontmatter field
    mod_categories = module.get('_categories', '')
    if mod_categories:
        mod_cats = [c.strip().lower() for c in mod_categories.split(',')]
        for fc in finding_categories:
            if any(fc in mc for mc in mod_cats):
                return True

    # Check description field (substring match)
    description = module.get('description', '').lower()
    for fc in finding_categories:
        if fc in description:
            return True

    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover and filter reference modules for specialists",
        prog="discover_references.py",
    )
    parser.add_argument(
        "specialist",
        nargs="?",
        default="",
        help="Specialist name (required unless --list-all is used)",
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        default=False,
        help="List modules for all specialists",
    )
    parser.add_argument(
        "--check-staleness",
        action="store_true",
        default=False,
        help="Check and warn about stale modules (>90 days)",
    )
    parser.add_argument(
        "--token-count",
        action="store_true",
        default=False,
        help="Include token count estimates in output",
    )
    parser.add_argument(
        "--builtin-dir",
        default=None,
        help="Override builtin references directory",
    )
    parser.add_argument(
        "--user-dir",
        default=None,
        help="Override user references directory",
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Override project references directory",
    )
    parser.add_argument(
        "--budget-check",
        type=int,
        metavar="TOTAL",
        default=None,
        help="Enable budget warnings with total token budget",
    )
    parser.add_argument(
        "--truncate-budget",
        nargs=2,
        type=int,
        metavar=("PER_ITER", "IMPACT_TOKENS"),
        default=None,
        help="Enable truncation with per-iteration budget and impact graph tokens",
    )
    parser.add_argument(
        "--extra-dir",
        default="",
        help="Additional references directory (highest priority)",
    )
    parser.add_argument(
        "--finding-categories",
        default="",
        help="Comma-separated finding categories from Phase 1 (e.g. 'injection,auth,crypto'). "
             "Used with --truncate-budget to prioritize relevant modules during truncation.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Validate: specialist is required unless --list-all
    if not args.list_all and not args.specialist:
        print("Error: Specialist required (or use --list-all)", file=sys.stderr)
        print("Usage: discover_references.py <specialist> [--check-staleness] [--token-count]", file=sys.stderr)
        print("       discover_references.py --list-all [--check-staleness] [--token-count]", file=sys.stderr)
        sys.exit(1)

    # Resolve default directories relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_dir = os.path.dirname(script_dir)

    builtin_dir = args.builtin_dir if args.builtin_dir else os.path.join(skill_dir, "references")
    user_dir = args.user_dir if args.user_dir else os.path.join(os.path.expanduser("~"), ".adversarial-review", "references")
    project_dir = args.project_dir if args.project_dir else ".adversarial-review/references"

    specialist = args.specialist
    list_all = args.list_all
    check_staleness = args.check_staleness
    token_count = args.token_count

    budget_check = args.budget_check is not None
    total_budget = args.budget_check if budget_check else 0

    truncate_budget = args.truncate_budget is not None
    per_iteration_budget = args.truncate_budget[0] if truncate_budget else 0
    impact_graph_tokens = args.truncate_budget[1] if truncate_budget else 0

    extra_dir = args.extra_dir
    finding_categories = [c.strip().lower() for c in args.finding_categories.split(',') if c.strip()] if args.finding_categories else []

    # Discover modules from all layers
    all_modules = []

    # Layer 1: Builtin (priority 1)
    all_modules.extend(discover_modules_in_dir(builtin_dir, specialist, list_all, 1))

    # Layer 2: User (priority 2)
    all_modules.extend(discover_modules_in_dir(user_dir, specialist, list_all, 2))

    # Layer 3: Project (priority 3)
    all_modules.extend(discover_modules_in_dir(project_dir, specialist, list_all, 3))

    # Layer 4: Extra dir (priority 4, highest, overrides all)
    if extra_dir:
        all_modules.extend(discover_modules_in_dir(extra_dir, specialist, list_all, 4))

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

        if 'categories' in metadata:
            module['_categories'] = metadata['categories']

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

    # Deduplicate by (name, specialist) - higher layer priority wins
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
    # When --finding-categories is provided, non-matching modules are truncated first.
    if truncate_budget and per_iteration_budget > 0:
        total_ref_tokens = sum(len(m.get('_body', '')) // 4 for m in final_modules)
        threshold_80pct = per_iteration_budget * 0.80
        combined = total_ref_tokens + impact_graph_tokens

        if combined > threshold_80pct:
            available = max(0, int(threshold_80pct - impact_graph_tokens))

            # Sort: non-matching modules first (truncated first), then by size descending
            def truncation_key(m):
                relevant = matches_finding_categories(m, finding_categories) if finding_categories else True
                return (relevant, -len(m.get('_body', '')))

            sorted_mods = sorted(final_modules, key=truncation_key)
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
