#!/usr/bin/env bash
# Run adversarial-review strat profile on all STRAT files in a directory.
#
# Usage:
#   ./scripts/run-strat-reviews.sh [input-dir] [output-dir]
#
# Defaults:
#   input-dir:  test-data/strats/
#   output-dir: test-data/reviews/
#
# Each STRAT file gets reviewed with --profile strat --$REVIEW_MODE --save.
# Results are saved to output-dir/<strat-id>-review.md
#
# Environment variables:
#   REVIEW_MODE   Review depth flag passed to adversarial-review (default: quick)
#   DRY_RUN       If set to 1, print commands without executing (default: 0)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT_DIR="${1:-${REPO_DIR}/test-data/strats}"
OUTPUT_DIR="${2:-${REPO_DIR}/test-data/reviews}"
REVIEW_MODE="${REVIEW_MODE:-quick}"
DRY_RUN="${DRY_RUN:-0}"

# Validate input directory
if [[ ! -d "$INPUT_DIR" ]]; then
  echo "ERROR: input directory does not exist: $INPUT_DIR"
  exit 1
fi

# Create output directory if missing
mkdir -p "$OUTPUT_DIR"

# Collect STRAT files
strat_files=()
while IFS= read -r -d '' f; do
  strat_files+=("$f")
done < <(find "$INPUT_DIR" -maxdepth 1 -name '*.md' -print0 | sort -z)

if [[ ${#strat_files[@]} -eq 0 ]]; then
  echo "No .md files found in $INPUT_DIR"
  exit 0
fi

total=${#strat_files[@]}
completed=0
failed=0

echo "=== STRAT Review Runner ==="
echo "Input dir:    $INPUT_DIR"
echo "Output dir:   $OUTPUT_DIR"
echo "Review mode:  $REVIEW_MODE"
echo "Files found:  $total"
echo ""

for strat_file in "${strat_files[@]}"; do
  filename="$(basename "$strat_file")"
  strat_id="${filename%.md}"

  echo "--- [$((completed + failed + 1))/$total] $filename"

  # The actual invocation goes through the Claude Code skill (adversarial-review),
  # which spawns sub-agents for each reviewer. This script documents the expected
  # command and can be used as a runner scaffold.
  cmd="/adversarial-review \"$strat_file\" --profile strat --${REVIEW_MODE} --save"
  echo "  cmd: $cmd"
  echo "  output: ${OUTPUT_DIR}/${strat_id}-review.md"

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  [dry-run] skipping execution"
    completed=$((completed + 1))
    continue
  fi

  # Run the review via claude CLI if available
  if command -v claude &>/dev/null; then
    if claude -p "$cmd" > "${OUTPUT_DIR}/${strat_id}-review.md" 2>&1; then
      completed=$((completed + 1))
      echo "  [done]"
    else
      failed=$((failed + 1))
      echo "  [failed] see ${OUTPUT_DIR}/${strat_id}-review.md for details"
    fi
  else
    echo "  [skip] claude CLI not found, run manually via Claude Code"
    completed=$((completed + 1))
  fi

  echo ""
done

echo "=== Summary ==="
echo "Total:     $total"
echo "Completed: $completed"
echo "Failed:    $failed"

if [[ $failed -gt 0 ]]; then
  exit 1
fi
