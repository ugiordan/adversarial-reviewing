#!/usr/bin/env bash
set -euo pipefail

# Generic context fetcher
# Accepts git repos, local directories, or single files as context sources
# Note: --output is only used for git repos and single files.
# For directory sources, the source directory is used directly (no copy).

label=""
source=""
output=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --label)
      label="$2"
      shift 2
      ;;
    --source)
      source="$2"
      shift 2
      ;;
    --output)
      output="$2"
      shift 2
      ;;
    *)
      echo "{\"error\": \"Unknown argument: $1\"}" >&2
      exit 1
      ;;
  esac
done

# Validate required arguments
if [[ -z "$label" ]]; then
  echo "{\"error\": \"Missing required argument: --label\"}" >&2
  exit 1
fi

if [[ -z "$source" ]]; then
  echo "{\"error\": \"Missing required argument: --source\"}" >&2
  exit 1
fi

# Set default output directory
if [[ -z "$output" ]]; then
  output=".context/${label}"
fi

# Determine source type and handle accordingly
if [[ "$source" == *"://"* ]] || [[ "$source" == *".git" ]]; then
  # Git repository - whitelist safe URL schemes (block ext::, fd::, etc.)
  if [[ ! "$source" =~ ^(https?|git|ssh|file):// ]] && [[ ! "$source" =~ ^git@ ]]; then
    echo "{\"error\": \"Unsupported git URL scheme. Only https, http, git, ssh, and file are allowed.\"}" >&2
    exit 1
  fi
  if [[ -d "$output" ]]; then
    # Pull if exists
    git -C "$output" pull --quiet
  else
    # Clone if doesn't exist
    git clone --quiet "$source" "$output"
  fi
elif [[ -d "$source" ]]; then
  # Local directory - use directly
  output="$source"
elif [[ -f "$source" ]]; then
  # Single file - copy to output directory
  mkdir -p "$output"
  cp "$source" "$output/"
else
  # Source doesn't exist
  echo "{\"error\": \"Source path does not exist: $source\"}" >&2
  exit 1
fi

# Find all .md files (excluding README.md and .git/)
files=()
while IFS= read -r -d '' file; do
  basename=$(basename "$file")
  if [[ "$basename" != "README.md" ]]; then
    files+=("$file")
  fi
done < <(find "$output" -type f -name "*.md" -not -path "*/.git/*" -print0)

# Build JSON output
file_count=${#files[@]}
files_json="["
for i in "${!files[@]}"; do
  files_json+="\"${files[$i]}\""
  if [[ $i -lt $((file_count - 1)) ]]; then
    files_json+=","
  fi
done
files_json+="]"

# Output JSON
echo "{\"label\": \"$label\", \"source\": \"$source\", \"output\": \"$output\", \"files\": $files_json, \"file_count\": $file_count}"
