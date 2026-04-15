#!/usr/bin/env bash
# Run all adversarial-review test suites.
# Usage: run-all-tests.sh
# Exit 0 if all pass, 1 if any fail.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOTAL_PASS=0
TOTAL_FAIL=0
FAILED_SUITES=()

for test in "$SCRIPT_DIR"/test-*.sh; do
    echo ""
    output=$(bash "$test" 2>&1)
    exit_code=$?
    echo "$output"

    pass=$(echo "$output" | grep -o '[0-9]* passed' | head -1 | grep -o '[0-9]*')
    fail=$(echo "$output" | grep -o '[0-9]* failed' | head -1 | grep -o '[0-9]*')
    TOTAL_PASS=$((TOTAL_PASS + ${pass:-0}))
    TOTAL_FAIL=$((TOTAL_FAIL + ${fail:-0}))

    if [[ $exit_code -ne 0 ]]; then
        FAILED_SUITES+=("$(basename "$test")")
    fi
done

echo ""
echo "========================================"
echo "TOTAL: $TOTAL_PASS passed, $TOTAL_FAIL failed"
if [[ ${#FAILED_SUITES[@]} -gt 0 ]]; then
    echo "Failed suites: ${FAILED_SUITES[*]}"
    exit 1
else
    echo "All suites passed."
    exit 0
fi
