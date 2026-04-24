#!/usr/bin/env bash
# Run a single IR experiment: invoke adversarial-review, extract findings, score.
#
# Usage:
#   run-experiment.sh \
#     --repo <path-to-repo> \
#     --ground-truth <ground-truth.yaml> \
#     --representation <R0|R1|R2|R3|R4|R5> \
#     --model <model-name> \
#     --run-id <identifier> \
#     [--output-dir <dir>] \
#     [--ir-file <path-to-ir>]
#
# For R0 (raw source), no --ir-file is needed.
# For R1-R5, provide the pre-compiled IR via --ir-file.
#
# Output: <output-dir>/<run-id>/
#   findings.json    - raw findings from adversarial-review
#   scores.json      - metrics from score.py
#   metadata.json    - run metadata (model, representation, timestamps)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AR_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
OUTPUT_DIR="$SCRIPT_DIR/results"
REPO=""
GROUND_TRUTH=""
REPRESENTATION="R0"
MODEL=""
RUN_ID=""
IR_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo) REPO="$2"; shift 2 ;;
        --ground-truth) GROUND_TRUTH="$2"; shift 2 ;;
        --representation) REPRESENTATION="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --run-id) RUN_ID="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --ir-file) IR_FILE="$2"; shift 2 ;;
        *) echo "Unknown flag: $1" >&2; exit 1 ;;
    esac
done

# Validate required args
if [[ -z "$REPO" || -z "$GROUND_TRUTH" || -z "$RUN_ID" ]]; then
    echo "Usage: run-experiment.sh --repo <path> --ground-truth <yaml> --run-id <id> [options]" >&2
    exit 1
fi

if [[ ! -d "$REPO" ]]; then
    echo "Error: repo not found: $REPO" >&2
    exit 1
fi

if [[ ! -f "$GROUND_TRUTH" ]]; then
    echo "Error: ground truth not found: $GROUND_TRUTH" >&2
    exit 1
fi

# Create output directory
RUN_DIR="$OUTPUT_DIR/$RUN_ID"
mkdir -p "$RUN_DIR"

# Record start time
START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_EPOCH=$(date +%s)

echo "========================================"
echo "IR Experiment: $RUN_ID"
echo "  Representation: $REPRESENTATION"
echo "  Model: ${MODEL:-default}"
echo "  Repo: $REPO"
echo "  Output: $RUN_DIR"
echo "========================================"

# --- Step 1: Determine input based on representation ---

case "$REPRESENTATION" in
    R0)
        # Raw source: adversarial-review reads files directly
        echo "[Step 1] Using raw source (R0)"
        INPUT_MODE="files"
        ;;
    R1|R2|R3|R4|R5)
        # IR-based: check for pre-compiled IR file
        if [[ -z "$IR_FILE" || ! -f "$IR_FILE" ]]; then
            echo "Error: representation $REPRESENTATION requires --ir-file" >&2
            exit 1
        fi
        echo "[Step 1] Using IR file: $IR_FILE ($REPRESENTATION)"
        INPUT_MODE="ir"
        # Copy IR to run dir for provenance
        cp "$IR_FILE" "$RUN_DIR/input-ir.txt"
        ;;
    *)
        echo "Error: unknown representation: $REPRESENTATION" >&2
        exit 1
        ;;
esac

# --- Step 2: Run adversarial-review ---

echo "[Step 2] Running adversarial-review (--security --quick)"

# For R0: run against the repo directly
# For R1+: run with the IR file as context
# NOTE: this step is manual for now. The script captures the findings
# output from a completed review. In the full pipeline, this would
# invoke claude-code or the Claude SDK programmatically.

FINDINGS_FILE="$RUN_DIR/findings.json"

if [[ -f "$FINDINGS_FILE" ]]; then
    echo "  Found existing findings.json, skipping review step"
else
    echo "  WARNING: No findings.json found in $RUN_DIR"
    echo "  To complete this experiment run:"
    echo ""
    echo "  1. Run adversarial-review against the target:"
    if [[ "$INPUT_MODE" == "files" ]]; then
        echo "     /adversarial-reviewing --security --quick --save $REPO"
    else
        echo "     /adversarial-reviewing --security --quick --save --context $IR_FILE $REPO"
    fi
    echo ""
    echo "  2. Convert findings to JSON:"
    echo "     python3 $AR_HOME/scripts/findings-to-json.py <review-report.md> --profile code > $FINDINGS_FILE"
    echo ""
    echo "  3. Re-run this script to score:"
    echo "     $0 --repo $REPO --ground-truth $GROUND_TRUTH --run-id $RUN_ID --representation $REPRESENTATION"
    echo ""
    exit 0
fi

# --- Step 3: Score findings ---

echo "[Step 3] Scoring findings against ground truth"

SCORES_FILE="$RUN_DIR/scores.json"

python3 "$SCRIPT_DIR/score.py" \
    "$FINDINGS_FILE" \
    "$GROUND_TRUTH" \
    --output "$SCORES_FILE" \
    --representation "$REPRESENTATION" \
    --model "${MODEL:-unknown}" \
    --run-id "$RUN_ID"

# --- Step 4: Write metadata ---

END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
END_EPOCH=$(date +%s)
DURATION=$((END_EPOCH - START_EPOCH))

cat > "$RUN_DIR/metadata.json" << METAEOF
{
  "run_id": "$RUN_ID",
  "representation": "$REPRESENTATION",
  "model": "${MODEL:-unknown}",
  "repo": "$REPO",
  "ground_truth": "$GROUND_TRUTH",
  "ir_file": "${IR_FILE:-null}",
  "start_time": "$START_TIME",
  "end_time": "$END_TIME",
  "duration_seconds": $DURATION,
  "input_mode": "$INPUT_MODE"
}
METAEOF

echo ""
echo "[Done] Results in $RUN_DIR/"
echo "  findings.json  - adversarial-review output"
echo "  scores.json    - detection metrics"
echo "  metadata.json  - run metadata"
