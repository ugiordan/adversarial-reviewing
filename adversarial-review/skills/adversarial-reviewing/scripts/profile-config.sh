#!/usr/bin/env bash
set -euo pipefail

# profile-config.sh
# Reads profile configuration from config.yml
#
# Usage: profile-config.sh <profile_dir> <key>
#
# Examples:
#   profile-config.sh profiles/strat evidence_format
#   profile-config.sh profiles/strat quick_specialists
#   profile-config.sh profiles/strat agents

if [ $# -ne 2 ]; then
    echo "Usage: $0 <profile_dir> <key>" >&2
    exit 1
fi

PROFILE_DIR="$1"
KEY="$2"

# Resolve to absolute path if relative
if [[ "$PROFILE_DIR" != /* ]]; then
    PROFILE_DIR="$(pwd)/$PROFILE_DIR"
fi

CONFIG_FILE="$PROFILE_DIR/config.yml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: config.yml not found at $CONFIG_FILE" >&2
    exit 2
fi

# Use python3 to parse YAML (simple parser for our flat config structure)
python3 - "$CONFIG_FILE" "$KEY" <<'PYTHON'
import sys
import json
import re

def parse_simple_yaml(content):
    """Parse a simple YAML file without requiring PyYAML."""
    data = {}
    current_list_key = None
    current_list = []
    current_dict_key = None
    current_dict_list = []
    indent_stack = []

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            i += 1
            continue

        indent = len(line) - len(stripped)

        # Check if this is a key-value pair
        if ':' in stripped and not stripped.startswith('-'):
            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip()

            # Check if next line is indented (start of nested structure)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_stripped = next_line.lstrip()
                next_indent = len(next_line) - len(next_stripped)

                if next_stripped and next_indent > indent:
                    # This is a nested structure
                    if next_stripped.startswith('-'):
                        # It's a list
                        current_list_key = key
                        current_list = []

                        # Check if it's a list of dicts or simple values
                        i += 1
                        first_item_line = lines[i]
                        first_item_stripped = first_item_line.lstrip()
                        first_item_indent = len(first_item_line) - len(first_item_stripped)

                        # Parse list items
                        while i < len(lines):
                            line = lines[i]
                            stripped = line.lstrip()
                            indent_level = len(line) - len(stripped)

                            if not stripped or indent_level < first_item_indent:
                                break

                            if stripped.startswith('-'):
                                # Check if it's a dict item
                                rest = stripped[1:].strip()
                                if not rest:
                                    # Next lines contain the dict
                                    dict_item = {}
                                    i += 1
                                    dict_indent = None

                                    while i < len(lines):
                                        dict_line = lines[i]
                                        dict_stripped = dict_line.lstrip()
                                        dict_line_indent = len(dict_line) - len(dict_stripped)

                                        if not dict_stripped:
                                            i += 1
                                            continue

                                        if dict_indent is None:
                                            dict_indent = dict_line_indent
                                        elif dict_line_indent < dict_indent:
                                            break
                                        elif dict_stripped.startswith('-'):
                                            # New list item
                                            break

                                        if ':' in dict_stripped:
                                            k, _, v = dict_stripped.partition(':')
                                            dict_item[k.strip()] = v.strip()
                                            i += 1
                                        else:
                                            break

                                    current_list.append(dict_item)
                                    continue
                                else:
                                    # Simple value
                                    current_list.append(rest)
                                    i += 1
                            else:
                                i += 1

                        data[current_list_key] = current_list
                        current_list_key = None
                        continue
                    else:
                        # It's a nested dict (like templates)
                        nested_dict = {}
                        i += 1
                        base_indent = None

                        while i < len(lines):
                            line = lines[i]
                            stripped = line.lstrip()
                            line_indent = len(line) - len(stripped)

                            if not stripped:
                                i += 1
                                continue

                            if base_indent is None:
                                base_indent = line_indent
                            elif line_indent < base_indent:
                                break

                            if ':' in stripped:
                                k, _, v = stripped.partition(':')
                                nested_dict[k.strip()] = v.strip()
                                i += 1
                            else:
                                break

                        data[key] = nested_dict
                        continue

            # Simple key-value pair
            if value:
                # Parse boolean/number/string
                if value.lower() in ('true', 'false'):
                    data[key] = value.lower() == 'true'
                elif value.isdigit():
                    data[key] = int(value)
                elif value.startswith('[') and value.endswith(']'):
                    # Inline list
                    items = value[1:-1].split(',')
                    data[key] = [item.strip() for item in items if item.strip()]
                else:
                    data[key] = value

        i += 1

    return data

def get_nested_value(data, key):
    """Get a value from nested dict using dotted key."""
    parts = key.split('.')
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current

def main():
    config_file = sys.argv[1]
    key = sys.argv[2]

    with open(config_file, 'r') as f:
        content = f.read()

    data = parse_simple_yaml(content)
    value = get_nested_value(data, key)

    if value is None:
        print(f"Error: key '{key}' not found in config", file=sys.stderr)
        sys.exit(1)

    # Output based on type
    if isinstance(value, list):
        # Check if it's a list of dicts (agents)
        if value and isinstance(value[0], dict):
            print(json.dumps(value))
        else:
            # Simple list
            for item in value:
                print(item)
    elif isinstance(value, dict):
        print(json.dumps(value))
    elif isinstance(value, bool):
        print('true' if value else 'false')
    else:
        print(value)

if __name__ == '__main__':
    main()
PYTHON
