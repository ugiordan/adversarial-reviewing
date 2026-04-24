#!/usr/bin/env bash
set -euo pipefail

# Test suite for fetch-context.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FETCH_CONTEXT="$SCRIPT_DIR/../scripts/fetch-context.sh"

# Test state
TESTS_PASSED=0
TESTS_FAILED=0
TEMP_DIR=""

# Helper functions
assert_contains() {
  local haystack="$1"
  local needle="$2"
  local test_name="$3"

  if echo "$haystack" | grep -q "$needle"; then
    echo "✓ $test_name"
    ((TESTS_PASSED++))
    return 0
  else
    echo "✗ $test_name"
    echo "  Expected to find: $needle"
    echo "  In: $haystack"
    ((TESTS_FAILED++))
    return 1
  fi
}

assert_eq() {
  local expected="$1"
  local actual="$2"
  local test_name="$3"

  if [[ "$expected" == "$actual" ]]; then
    echo "✓ $test_name"
    ((TESTS_PASSED++))
    return 0
  else
    echo "✗ $test_name"
    echo "  Expected: $expected"
    echo "  Actual: $actual"
    ((TESTS_FAILED++))
    return 1
  fi
}

# Cleanup function
cleanup() {
  if [[ -n "$TEMP_DIR" ]] && [[ -d "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
}

trap cleanup EXIT

# Test 1: Local directory source
test_local_directory() {
  echo "Test 1: Local directory source"

  TEMP_DIR=$(mktemp -d)
  mkdir -p "$TEMP_DIR/test-dir"
  echo "# Doc 1" > "$TEMP_DIR/test-dir/doc1.md"
  echo "# Doc 2" > "$TEMP_DIR/test-dir/doc2.md"
  echo "Not markdown" > "$TEMP_DIR/test-dir/file.txt"

  local output
  output=$("$FETCH_CONTEXT" --label "test-label" --source "$TEMP_DIR/test-dir" 2>&1)

  assert_contains "$output" "test-label" "Label is returned"
  assert_contains "$output" "\"file_count\": 2" "File count is 2"

  cleanup
  TEMP_DIR=""
}

# Test 2: Local file source
test_local_file() {
  echo ""
  echo "Test 2: Local file source"

  TEMP_DIR=$(mktemp -d)
  echo "# Single doc" > "$TEMP_DIR/single.md"

  local output
  output=$("$FETCH_CONTEXT" --label "file-label" --source "$TEMP_DIR/single.md" --output "$TEMP_DIR/output" 2>&1)

  assert_contains "$output" "file-label" "Label is returned"
  assert_contains "$output" "\"file_count\": 1" "File count is 1"

  cleanup
  TEMP_DIR=""
}

# Test 3: Missing source
test_missing_source() {
  echo ""
  echo "Test 3: Missing source"

  TEMP_DIR=$(mktemp -d)
  local nonexistent="$TEMP_DIR/does-not-exist"

  local output
  output=$("$FETCH_CONTEXT" --label "test-label" --source "$nonexistent" 2>&1 || true)

  assert_contains "$output" "error" "Error JSON is returned"
  assert_contains "$output" "Source path does not exist" "Error message mentions missing source"

  cleanup
  TEMP_DIR=""
}

# Test 4: Missing label argument
test_missing_label() {
  echo ""
  echo "Test 4: Missing label argument"

  TEMP_DIR=$(mktemp -d)
  mkdir -p "$TEMP_DIR/test-dir"

  local output
  output=$("$FETCH_CONTEXT" --source "$TEMP_DIR/test-dir" 2>&1 || true)

  assert_contains "$output" "error" "Error JSON is returned"
  assert_contains "$output" "Missing required argument: --label" "Error message mentions missing label"

  cleanup
  TEMP_DIR=""
}

# Run all tests
test_local_directory
test_local_file
test_missing_source
test_missing_label

# Print summary
echo ""
echo "========================================="
echo "Test Results Summary"
echo "========================================="
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo "========================================="

if [[ $TESTS_FAILED -eq 0 ]]; then
  echo "All tests passed!"
  exit 0
else
  echo "Some tests failed!"
  exit 1
fi
