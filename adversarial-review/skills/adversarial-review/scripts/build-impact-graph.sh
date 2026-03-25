#!/usr/bin/env bash
# Build a change-impact graph from a git diff, identifying changed symbols and their callers/callees.
# Usage: build-impact-graph.sh --diff-file <patch> --search-dir <dir> [--max-symbols N] [--max-callers N]
#        build-impact-graph.sh --git-range <range> --search-dir <dir> [--max-symbols N] [--max-callers N]
# Exit codes: 0 success, 1 error, 2 empty diff

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATE_DELIMITERS="$SCRIPT_DIR/generate-delimiters.sh"

# Default limits (per spec: max 10 symbols, 20 callers, 50K token cap)
MAX_SYMBOLS=10
MAX_CALLERS=20
MAX_CALLEES=20
TOKEN_LIMIT=50000  # 50K token cap

# Parse arguments
DIFF_FILE=""
GIT_RANGE=""
SEARCH_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --diff-file)
            DIFF_FILE="${2:?--diff-file requires a path}"
            shift 2
            ;;
        --git-range)
            GIT_RANGE="${2:?--git-range requires a range}"
            shift 2
            ;;
        --search-dir)
            SEARCH_DIR="${2:?--search-dir requires a path}"
            shift 2
            ;;
        --max-symbols)
            MAX_SYMBOLS="${2:?--max-symbols requires a number}"
            shift 2
            ;;
        --max-callers)
            MAX_CALLERS="${2:?--max-callers requires a number}"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: build-impact-graph.sh --diff-file <patch> --search-dir <dir> [--max-symbols N] [--max-callers N]" >&2
            echo "       build-impact-graph.sh --git-range <range> --search-dir <dir> [--max-symbols N] [--max-callers N]" >&2
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$SEARCH_DIR" ]]; then
    echo "Error: --search-dir is required" >&2
    exit 1
fi

if [[ -z "$DIFF_FILE" && -z "$GIT_RANGE" ]]; then
    echo "Error: Either --diff-file or --git-range is required" >&2
    exit 1
fi

if [[ -n "$DIFF_FILE" && -n "$GIT_RANGE" ]]; then
    echo "Error: Cannot specify both --diff-file and --git-range" >&2
    exit 1
fi

# Get diff content
DIFF_CONTENT=""
if [[ -n "$DIFF_FILE" ]]; then
    if [[ ! -f "$DIFF_FILE" ]]; then
        echo "Error: Diff file not found: $DIFF_FILE" >&2
        exit 1
    fi
    DIFF_CONTENT=$(cat "$DIFF_FILE")
elif [[ -n "$GIT_RANGE" ]]; then
    DIFF_CONTENT=$(git diff "$GIT_RANGE" 2>/dev/null || echo "")
    if [[ -z "$DIFF_CONTENT" ]]; then
        echo "Error: Failed to get diff for range: $GIT_RANGE" >&2
        exit 1
    fi
fi

# Check for empty diff
if [[ -z "$DIFF_CONTENT" || "$DIFF_CONTENT" =~ ^[[:space:]]*$ ]]; then
    echo "Error: Empty diff" >&2
    exit 2
fi

# Extract changed symbols from diff
# Look for function/method definitions in Go, Python, etc.
extract_symbols() {
    local diff="$1"

    # Go functions (exported and unexported): func FunctionName( or func functionName(
    echo "$diff" | grep -E '^\+.*func [a-zA-Z_][a-zA-Z0-9_]*\(' | \
        sed -E 's/.*func ([a-zA-Z_][a-zA-Z0-9_]*)\(.*/\1/' | sort -u

    # Python functions/methods: def function_name(
    echo "$diff" | grep -E '^\+.*def [a-zA-Z_][a-zA-Z0-9_]*\(' | \
        sed -E 's/.*def ([a-zA-Z_][a-zA-Z0-9_]*)\(.*/\1/' | sort -u

    # TypeScript/JavaScript: function name(, const name =, export function name(
    echo "$diff" | grep -E '^\+.*(function |const |let |export function )[a-zA-Z_][a-zA-Z0-9_]*[( =]' | \
        sed -E 's/.*(function |const |let |export function )([a-zA-Z_][a-zA-Z0-9_]*).*/\2/' | sort -u

    # Java/Rust: public/fn keyword before identifier
    echo "$diff" | grep -E '^\+.*(public |private |protected |fn )[a-zA-Z_][a-zA-Z0-9_]*\(' | \
        sed -E 's/.*(public |private |protected |fn )([a-zA-Z_][a-zA-Z0-9_]*)\(.*/\2/' | sort -u

    # Also look for functions that are being modified (not just added)
    # Extract the function context from diff headers
    echo "$diff" | grep -E '^@@.*@@.*(func |def |function |fn )[a-zA-Z_][a-zA-Z0-9_]*\(' | \
        sed -E 's/.*(func |def |function |fn )([a-zA-Z_][a-zA-Z0-9_]*)\(.*/\2/' | sort -u
}

SYMBOLS=$(extract_symbols "$DIFF_CONTENT")

if [[ -z "$SYMBOLS" ]]; then
    echo "Warning: No symbols found in diff" >&2
    exit 2
fi

# Find callers of a symbol
find_callers() {
    local symbol="$1"
    local search_dir="$2"

    # Use grep to find function calls, showing file:line:content
    grep -r -n "${symbol}(" "$search_dir" 2>/dev/null | \
        grep -v "^Binary" | \
        grep -v "func ${symbol}(" | \
        head -n "$MAX_CALLERS" || true

    # Also try to extract the enclosing function names
    # This is a heuristic - for each file that calls the symbol,
    # try to identify which functions contain those calls
    local files
    files=$(grep -r -l "${symbol}(" "$search_dir" 2>/dev/null | grep -v "Binary" || true)

    if [[ -n "$files" ]]; then
        while IFS= read -r file; do
            if [[ -f "$file" ]]; then
                # Find function definitions that occur before calls to the symbol
                # This is a simple heuristic for Go code
                awk -v symbol="$symbol" '
                    /^func [a-zA-Z_][a-zA-Z0-9_]*\(/ {
                        current_func = $0
                        sub(/^func /, "", current_func)
                        sub(/\(.*/, "", current_func)
                    }
                    $0 ~ symbol "\\(" && !/^func/ {
                        if (current_func != "" && current_func != symbol) {
                            print current_func
                        }
                    }
                ' "$file" 2>/dev/null | sort -u
            fi
        done <<< "$files"
    fi
}

# Find callees (functions called by this symbol)
find_callees() {
    local symbol="$1"
    local search_dir="$2"

    # Find the file containing the symbol definition
    local symbol_file
    symbol_file=$(grep -r -l "func ${symbol}(" "$search_dir" 2>/dev/null | head -1 || echo "")

    if [[ -z "$symbol_file" ]]; then
        return
    fi

    # Extract function body and find function calls within it
    # Look for capitalized identifiers followed by '(' (Go convention for exported functions)
    awk "/func ${symbol}[(]/,/^}/" "$symbol_file" 2>/dev/null | \
        grep -o '[A-Z][a-zA-Z0-9_]*(' | \
        sed 's/($//' | \
        grep -v "^${symbol}$" | \
        sort -u | \
        head -n "$MAX_CALLEES" || true
}

# Create temp file for delimiter input
TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

echo "Impact graph analysis" > "$TEMP_FILE"

# Generate delimiters
DELIM_JSON=$("$GENERATE_DELIMITERS" --category IMPACT_GRAPH "$TEMP_FILE")
START_DELIM=$(echo "$DELIM_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['start_delimiter'])")
END_DELIM=$(echo "$DELIM_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['end_delimiter'])")

# Build the impact graph output
OUTPUT=""
OUTPUT+="$START_DELIM"$'\n'
OUTPUT+="ADVISORY: This impact graph analysis may be INCOMPLETE."$'\n'
OUTPUT+="It uses heuristic pattern matching and may miss indirect calls,"$'\n'
OUTPUT+="dynamic dispatch, reflection, or cross-package dependencies."$'\n'
OUTPUT+=""$'\n'

SYMBOL_COUNT=0
TOTAL_SIZE=0

# Process each symbol
while IFS= read -r symbol; do
    if [[ -z "$symbol" ]]; then
        continue
    fi

    if (( SYMBOL_COUNT >= MAX_SYMBOLS )); then
        OUTPUT+="[TRUNCATED: Max symbols ($MAX_SYMBOLS) reached]"$'\n'
        break
    fi

    SYMBOL_OUTPUT=""
    SYMBOL_OUTPUT+="SYMBOL: $symbol"$'\n'

    # Find callers
    CALLERS=$(find_callers "$symbol" "$SEARCH_DIR")
    if [[ -n "$CALLERS" ]]; then
        CALLER_COUNT=$(echo "$CALLERS" | wc -l | tr -d ' ')
        SYMBOL_OUTPUT+="  CALLERS ($CALLER_COUNT):"$'\n'

        CALLER_LINE_COUNT=0
        while IFS= read -r caller_line; do
            SYMBOL_OUTPUT+="    $caller_line"$'\n'
            CALLER_LINE_COUNT=$((CALLER_LINE_COUNT + 1))

            # Check token limit (approximate - 1 token ~= 4 chars)
            CURRENT_SIZE=$((${#OUTPUT} + ${#SYMBOL_OUTPUT}))
            if (( CURRENT_SIZE > TOKEN_LIMIT * 4 )); then
                SYMBOL_OUTPUT+="    [TRUNCATED: Token limit reached]"$'\n'
                break
            fi
        done <<< "$CALLERS"
    else
        SYMBOL_OUTPUT+="  CALLERS: (none found)"$'\n'
    fi

    # Find callees
    CALLEES=$(find_callees "$symbol" "$SEARCH_DIR")
    if [[ -n "$CALLEES" ]]; then
        CALLEE_COUNT=$(echo "$CALLEES" | wc -l | tr -d ' ')
        SYMBOL_OUTPUT+="  CALLEES ($CALLEE_COUNT):"$'\n'

        while IFS= read -r callee; do
            if [[ -n "$callee" ]]; then
                SYMBOL_OUTPUT+="    $callee"$'\n'
            fi

            # Check token limit
            CURRENT_SIZE=$((${#OUTPUT} + ${#SYMBOL_OUTPUT}))
            if (( CURRENT_SIZE > TOKEN_LIMIT * 4 )); then
                SYMBOL_OUTPUT+="    [TRUNCATED: Token limit reached]"$'\n'
                break
            fi
        done <<< "$CALLEES"
    else
        SYMBOL_OUTPUT+="  CALLEES: (none found)"$'\n'
    fi

    SYMBOL_OUTPUT+=""$'\n'

    # Check if adding this symbol would exceed token limit
    POTENTIAL_SIZE=$((${#OUTPUT} + ${#SYMBOL_OUTPUT}))
    if (( POTENTIAL_SIZE > TOKEN_LIMIT * 4 )); then
        OUTPUT+="[TRUNCATED: Token limit reached - remaining symbols omitted]"$'\n'
        break
    fi

    OUTPUT+="$SYMBOL_OUTPUT"
    SYMBOL_COUNT=$((SYMBOL_COUNT + 1))

done <<< "$SYMBOLS"

OUTPUT+="$END_DELIM"$'\n'

echo "$OUTPUT"
exit 0
