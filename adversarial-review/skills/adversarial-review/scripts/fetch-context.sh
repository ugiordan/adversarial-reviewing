#!/usr/bin/env bash
set -euo pipefail

# Generic context fetcher
# Accepts git repos, local directories, or single files as context sources
# Note: --output is only used for git repos and single files.
# For directory sources, the source directory is used directly (no copy).
#
# Supports @ref syntax for git repos: org/repo@tag, org/repo@branch, org/repo@sha
# The @ref suffix checks out the specified ref after cloning/pulling.

label=""
source=""
output=""
ref=""

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
    --ref)
      ref="$2"
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

# Parse @ref from source if not provided via --ref
# Supports: org/repo@ref (shorthand for GitHub), full URLs with @ref suffix
# Refs can contain slashes (e.g., release/v2.15, feature/pipeline)
# Skip parsing for SSH URLs (git@github.com:org/repo.git)
if [[ -z "$ref" && "$source" == *"@"* && ! "$source" =~ ^git@ ]]; then
  ref="${source##*@}"
  source="${source%@*}"
fi

# Expand org/repo shorthand to GitHub HTTPS URL
if [[ "$source" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]]; then
  source="https://github.com/${source}.git"
fi

# Determine source type and handle accordingly
if [[ "$source" == *"://"* ]] || [[ "$source" == *".git" ]]; then
  # Git repository - whitelist safe URL schemes (block ext::, fd::, etc.)
  if [[ ! "$source" =~ ^(https?|git|ssh|file):// ]] && [[ ! "$source" =~ ^git@ ]]; then
    echo "{\"error\": \"Unsupported git URL scheme. Only https, http, git, ssh, and file are allowed.\"}" >&2
    exit 1
  fi
  if [[ -d "$output" ]]; then
    if [[ -n "$ref" ]]; then
      # Fetch all refs when a specific ref is requested (avoids stale local branches)
      git -C "$output" fetch --quiet --all --tags
    else
      # Default branch: just pull latest
      git -C "$output" pull --quiet
    fi
  else
    # Clone if doesn't exist
    git clone --quiet "$source" "$output"
    # Fetch tags for ref checkout (clone doesn't always get all tags)
    if [[ -n "$ref" ]]; then
      git -C "$output" fetch --quiet --tags
    fi
  fi
  # Checkout specific ref if provided (-- prevents option injection from refs starting with -)
  if [[ -n "$ref" ]]; then
    git -C "$output" checkout --quiet -- "$ref"
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

# Find all .md files (excluding README.md and .git/) and produce JSON output
# Uses python3 for safe JSON serialization (handles quotes, backslashes in paths)
# Pass metadata via env vars to avoid shell injection into Python code
find "$output" -type f -name "*.md" -not -path "*/.git/*" -print0 \
  | FETCH_LABEL="$label" FETCH_SOURCE="$source" FETCH_REF="$ref" FETCH_OUTPUT="$output" \
    python3 -c "
import json, sys, os

files = [f for f in sys.stdin.buffer.read().split(b'\x00') if f]
files = [f.decode() for f in files if os.path.basename(f.decode()) != 'README.md']

ref_val = os.environ.get('FETCH_REF') or None
result = {
    'label': os.environ['FETCH_LABEL'],
    'source': os.environ['FETCH_SOURCE'],
    'ref': ref_val,
    'output': os.environ['FETCH_OUTPUT'],
    'files': files,
    'file_count': len(files)
}
print(json.dumps(result))
"
