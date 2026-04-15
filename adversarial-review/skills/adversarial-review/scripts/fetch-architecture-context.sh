#!/usr/bin/env bash
set -euo pipefail

# fetch-architecture-context.sh
# Fetches architecture context from a git repo and makes it available as ephemeral reference modules.

# Default values
DEFAULT_REPO="https://github.com/opendatahub-io/architecture-context.git"
DEFAULT_OUTPUT=".context/architecture-context"
REPO=""
OUTPUT=""
STRATEGIES_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    --strategies)
      STRATEGIES_FILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--repo <url_or_path>] [--output <dir>] [--strategies <file_list>]" >&2
      exit 1
      ;;
  esac
done

# Set defaults if not provided
REPO="${REPO:-$DEFAULT_REPO}"
OUTPUT="${OUTPUT:-$DEFAULT_OUTPUT}"

# Check if git is available
if ! command -v git &> /dev/null; then
  echo '{"error": "git command not found", "docs": [], "matched_components": []}' >&2
  exit 1
fi

# Determine if REPO is a URL or local path
IS_LOCAL=false
if [[ -d "$REPO" ]]; then
  IS_LOCAL=true
  REPO_PATH="$REPO"
elif [[ "$REPO" =~ ^/ ]] || [[ "$REPO" =~ ^\. ]]; then
  # Looks like a path but doesn't exist
  echo "{\"error\": \"Local path does not exist: $REPO\", \"docs\": [], \"matched_components\": []}" >&2
  exit 1
else
  # Treat as URL
  REPO_PATH="$OUTPUT"
fi

# If remote repo, clone or update
if [[ "$IS_LOCAL" == false ]]; then
  mkdir -p "$(dirname "$OUTPUT")"

  if [[ -d "$OUTPUT/.git" ]]; then
    # Repo already exists, update it
    if ! git -C "$OUTPUT" pull --quiet 2>/dev/null; then
      echo "{\"error\": \"Failed to update repository at $OUTPUT\", \"docs\": [], \"matched_components\": []}" >&2
      exit 1
    fi
  else
    # Clone the repo
    if ! git clone --quiet "$REPO" "$OUTPUT" 2>/dev/null; then
      echo "{\"error\": \"Failed to clone repository from $REPO\", \"docs\": [], \"matched_components\": []}" >&2
      exit 1
    fi
  fi
fi

# Convert REPO_PATH to absolute path
if [[ ! "$REPO_PATH" =~ ^/ ]]; then
  REPO_PATH="$(cd "$REPO_PATH" && pwd)"
fi

# Find architecture docs
DOCS=()
MATCHED_COMPONENTS=()

# Look for architecture/rhoai-*/ directories
if [[ -d "$REPO_PATH/architecture" ]]; then
  for rhoai_dir in "$REPO_PATH/architecture"/rhoai-*/; do
    if [[ ! -d "$rhoai_dir" ]]; then
      continue
    fi

    # Check for PLATFORM.md
    if [[ -f "$rhoai_dir/PLATFORM.md" ]]; then
      DOCS+=("{\"component\": \"PLATFORM\", \"path\": \"$rhoai_dir/PLATFORM.md\"}")
    fi

    # Find all .md files except PLATFORM.md
    while IFS= read -r -d '' md_file; do
      component_name="$(basename "$md_file" .md)"
      DOCS+=("{\"component\": \"$component_name\", \"path\": \"$md_file\"}")
    done < <(find "$rhoai_dir" -maxdepth 1 -name "*.md" ! -name "PLATFORM.md" -print0)
  done
fi

# If --strategies is provided, match components
if [[ -n "$STRATEGIES_FILE" && -f "$STRATEGIES_FILE" ]]; then
  # Read strategy files and extract component names
  while IFS= read -r strategy_path; do
    if [[ -f "$strategy_path" ]]; then
      # Extract component names mentioned in the strategy
      # Look for patterns like component names in the docs
      while IFS= read -r doc_entry; do
        component=$(echo "$doc_entry" | grep -o '"component": "[^"]*"' | cut -d'"' -f4)

        # Simple grep match: check if component name appears in strategy file
        if grep -q -i "$component" "$strategy_path" 2>/dev/null; then
          # Add to matched components if not already there
          if [[ ! " ${MATCHED_COMPONENTS[*]} " =~ " ${component} " ]]; then
            MATCHED_COMPONENTS+=("$component")
          fi
        fi
      done <<< "$(printf '%s\n' "${DOCS[@]}")"
    fi
  done < "$STRATEGIES_FILE"
fi

# Build JSON output
DOCS_JSON="["
for i in "${!DOCS[@]}"; do
  if [[ $i -gt 0 ]]; then
    DOCS_JSON+=","
  fi
  DOCS_JSON+="${DOCS[$i]}"
done
DOCS_JSON+="]"

MATCHED_JSON="["
for i in "${!MATCHED_COMPONENTS[@]}"; do
  if [[ $i -gt 0 ]]; then
    MATCHED_JSON+=","
  fi
  MATCHED_JSON+="\"${MATCHED_COMPONENTS[$i]}\""
done
MATCHED_JSON+="]"

# Output JSON
cat <<EOF
{
  "source": "$REPO",
  "docs": $DOCS_JSON,
  "matched_components": $MATCHED_JSON
}
EOF
