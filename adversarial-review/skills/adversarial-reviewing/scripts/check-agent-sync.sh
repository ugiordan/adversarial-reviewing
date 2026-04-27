#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SECURITY_SECTIONS="inoculation-instructions context-document-safety triage-mode-inoculation"

usage() {
    cat <<EOF
Usage: check-agent-sync.sh [--fix] [--profile <name>] [--yes]

Check agent files for drift against canonical snippet files.

Options:
    --fix           Apply canonical content to drifted agents (interactive)
    --profile NAME  Check only the specified profile (code, strat, rfe)
    --yes           Skip confirmation for non-security sections (--fix only)
    -h, --help      Show this help

Exit codes:
    0  No drift detected
    1  Drift detected
    2  Error
EOF
}

FIX=false
YES=false
PROFILE_FILTER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fix) FIX=true; shift ;;
        --yes) YES=true; shift ;;
        --profile) PROFILE_FILTER="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

EXCEPTIONS_FILE="$SKILL_DIR/.sync-exceptions.yaml"
DRIFT_FOUND=false

is_exception() {
    local profile="$1" agent="$2" section="$3"
    if [[ ! -f "$EXCEPTIONS_FILE" ]]; then
        return 1
    fi
    python3 -c "
import yaml, sys
with open('$EXCEPTIONS_FILE') as f:
    data = yaml.safe_load(f)
exceptions = data.get('exceptions', []) if data else []
for e in exceptions:
    if e.get('profile') == '$profile' and e.get('agent') == '$agent' and e.get('section') == '$section':
        sys.exit(0)
sys.exit(1)
" 2>/dev/null
}

is_security_section() {
    local section="$1"
    for s in $SECURITY_SECTIONS; do
        if [[ "$section" == "$s" ]]; then
            return 0
        fi
    done
    return 1
}

extract_section() {
    local file="$1" heading="$2"
    python3 -c "
import re, sys

with open('$file') as f:
    content = f.read()

heading = '''$heading'''
lines = content.split('\n')
start = None
end = None
heading_level = len(heading.lstrip()) - len(heading.lstrip().lstrip('#'))

for i, line in enumerate(lines):
    if line.strip() == heading.strip():
        start = i
        continue
    if start is not None and i > start:
        stripped = line.lstrip()
        if stripped.startswith('#'):
            level = len(stripped) - len(stripped.lstrip('#'))
            if level <= heading_level:
                end = i
                break

if start is None:
    sys.exit(1)

if end is None:
    end = len(lines)

# Strip trailing blank lines
while end > start and lines[end-1].strip() == '':
    end -= 1

print('\n'.join(lines[start:end]))
"
}

check_section() {
    local profile="$1" agent_file="$2" canonical_file="$3" section_name="$4"
    local agent_name
    agent_name="$(basename "$agent_file" .md)"

    if [[ ! -f "$canonical_file" ]]; then
        echo "ERROR: canonical file not found: $canonical_file" >&2
        return 2
    fi

    local heading
    heading="$(head -1 "$canonical_file")"

    local agent_content canonical_content
    canonical_content="$(cat "$canonical_file")"

    agent_content="$(extract_section "$agent_file" "$heading" 2>/dev/null)" || {
        return 0
    }

    local agent_hash canonical_hash
    agent_hash="$(echo "$agent_content" | shasum -a 256 | cut -d' ' -f1)"
    canonical_hash="$(echo "$canonical_content" | shasum -a 256 | cut -d' ' -f1)"

    if [[ "$agent_hash" == "$canonical_hash" ]]; then
        if is_exception "$profile" "$agent_name" "$section_name"; then
            echo "  NOTICE: $agent_name/$section_name matches canonical but has an exception entry (may be stale)"
        fi
        return 0
    fi

    if is_exception "$profile" "$agent_name" "$section_name"; then
        if is_security_section "$section_name"; then
            echo "  WARNING: $agent_name/$section_name diverges from canonical (intentional, SECURITY-CRITICAL section)"
        else
            echo "  OK: $agent_name/$section_name intentional divergence (exception)"
        fi
        return 0
    fi

    DRIFT_FOUND=true
    echo "  DRIFT: $agent_name/$section_name"
    diff <(echo "$canonical_content") <(echo "$agent_content") || true

    if [[ "$FIX" == true ]]; then
        if is_security_section "$section_name"; then
            echo ""
            echo "  This is a SECURITY-CRITICAL section. Interactive confirmation required."
            read -r -p "  Apply canonical version to $agent_name/$section_name? [y/N] " confirm
            if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
                echo "  Skipped."
                return 0
            fi
        elif [[ "$YES" == true ]]; then
            echo "  Auto-applying fix (--yes)..."
        else
            read -r -p "  Apply canonical version to $agent_name/$section_name? [y/N] " confirm
            if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
                echo "  Skipped."
                return 0
            fi
        fi

        python3 -c "
import sys

with open('$agent_file') as f:
    content = f.read()

heading = '''$heading'''
with open('$canonical_file') as f:
    canonical = f.read().rstrip()

lines = content.split('\n')
start = None
end = None
heading_level = len(heading.lstrip()) - len(heading.lstrip().lstrip('#'))

for i, line in enumerate(lines):
    if line.strip() == heading.strip():
        start = i
        continue
    if start is not None and i > start:
        stripped = line.lstrip()
        if stripped.startswith('#'):
            level = len(stripped) - len(stripped.lstrip('#'))
            if level <= heading_level:
                end = i
                break

if start is None:
    print('ERROR: section not found in agent file', file=sys.stderr)
    sys.exit(1)

if end is None:
    end = len(lines)

while end > start and lines[end-1].strip() == '':
    end -= 1

new_lines = lines[:start] + canonical.split('\n') + lines[end:]
with open('$agent_file', 'w') as f:
    f.write('\n'.join(new_lines))
"
        echo "  Fixed."
    fi
}

check_profile() {
    local profile="$1"
    local canonical_dir="$SKILL_DIR/profiles/$profile/shared/canonical"
    local agents_dir="$SKILL_DIR/profiles/$profile/agents"

    if [[ ! -d "$canonical_dir" ]]; then
        return 0
    fi

    echo "Checking profile: $profile"

    for canonical_file in "$canonical_dir"/*.md; do
        [[ -f "$canonical_file" ]] || continue
        local section_name
        section_name="$(basename "$canonical_file" .md)"

        for agent_file in "$agents_dir"/*.md; do
            [[ -f "$agent_file" ]] || continue
            local agent_name
            agent_name="$(basename "$agent_file" .md)"

            [[ "$agent_name" == "fix-agent" ]] && continue

            check_section "$profile" "$agent_file" "$canonical_file" "$section_name"
        done
    done
}

if [[ -n "$PROFILE_FILTER" ]]; then
    check_profile "$PROFILE_FILTER"
else
    for profile_dir in "$SKILL_DIR"/profiles/*/; do
        profile="$(basename "$profile_dir")"
        check_profile "$profile"
    done
fi

if [[ "$DRIFT_FOUND" == true ]]; then
    echo ""
    echo "Drift detected. Run with --fix to apply canonical versions."
    exit 1
else
    echo ""
    echo "All sections in sync."
    exit 0
fi
