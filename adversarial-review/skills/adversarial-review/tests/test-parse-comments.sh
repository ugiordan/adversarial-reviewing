#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PARSE_COMMENTS="$SKILL_DIR/scripts/parse-comments.sh"
FIXTURES_DIR="$SCRIPT_DIR/fixtures"

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

test_name() {
    echo -e "\n${YELLOW}TEST:${NC} $1"
    TESTS_RUN=$((TESTS_RUN + 1))
}

# Test 1: GitHub PR format produces valid JSON lines with EXT-001 through EXT-003
test_name "GitHub PR format produces valid JSON lines with EXT-001 through EXT-003"
output=$("$PARSE_COMMENTS" github-pr "$FIXTURES_DIR/github-pr-comments.json")
line_count=$(echo "$output" | wc -l | tr -d ' ')
if [[ "$line_count" == "3" ]]; then
    # Verify each line is valid JSON
    valid=true
    while IFS= read -r line; do
        if ! echo "$line" | jq empty 2>/dev/null; then
            valid=false
            break
        fi
    done <<< "$output"

    if [[ "$valid" == "true" ]]; then
        # Check IDs
        ids=$(echo "$output" | jq -r .id | sort)
        expected_ids=$(echo -e "EXT-001\nEXT-002\nEXT-003" | sort)
        if [[ "$ids" == "$expected_ids" ]]; then
            pass "GitHub PR format produces 3 valid JSON lines with correct IDs"
        else
            fail "IDs don't match expected EXT-001 through EXT-003"
        fi
    else
        fail "Output contains invalid JSON"
    fi
else
    fail "Expected 3 lines, got $line_count"
fi

# Test 2: Bot detection (coderabbitai → author_role: bot)
test_name "Bot detection (coderabbitai → author_role: bot)"
output=$("$PARSE_COMMENTS" github-pr "$FIXTURES_DIR/github-pr-comments.json")
bot_role=$(echo "$output" | jq -r 'select(.author == "coderabbitai") | .author_role')
if [[ "$bot_role" == "bot" ]]; then
    pass "Bot detected correctly"
else
    fail "Bot role not set correctly, got: $bot_role"
fi

# Test 3: Collaborator role detection
test_name "Collaborator role detection"
output=$("$PARSE_COMMENTS" github-pr "$FIXTURES_DIR/github-pr-comments.json")
collab_role=$(echo "$output" | jq -r 'select(.author == "reviewer1") | .author_role')
if [[ "$collab_role" == "collaborator" ]]; then
    pass "Collaborator role detected correctly"
else
    fail "Collaborator role not set correctly, got: $collab_role"
fi

# Test 4: Null file/line handled
test_name "Null file/line handled"
output=$("$PARSE_COMMENTS" github-pr "$FIXTURES_DIR/github-pr-comments.json")
null_file_entry=$(echo "$output" | jq -r 'select(.author == "reviewer1") | .file')
null_line_entry=$(echo "$output" | jq -r 'select(.author == "reviewer1") | .line')
if [[ "$null_file_entry" == "null" ]] && [[ "$null_line_entry" == "null" ]]; then
    pass "Null file/line handled correctly"
else
    fail "Null file/line not handled correctly"
fi

# Test 5: Structured format parses correctly
test_name "Structured format parses correctly"
output=$("$PARSE_COMMENTS" structured "$FIXTURES_DIR/structured-comments.json")
line_count=$(echo "$output" | wc -l | tr -d ' ')
if [[ "$line_count" == "2" ]]; then
    # Check first entry has file and line
    first_file=$(echo "$output" | head -n1 | jq -r .file)
    first_line=$(echo "$output" | head -n1 | jq -r .line)
    if [[ "$first_file" == "src/auth/login.py" ]] && [[ "$first_line" == "42" ]]; then
        pass "Structured format parses correctly"
    else
        fail "Structured format file/line incorrect"
    fi
else
    fail "Expected 2 lines, got $line_count"
fi

# Test 6: Freeform text parses correctly, extracts file paths
test_name "Freeform text parses correctly, extracts file paths"
output=$("$PARSE_COMMENTS" freeform "$FIXTURES_DIR/freeform-comments.txt")
line_count=$(echo "$output" | wc -l | tr -d ' ')
if [[ "$line_count" == "3" ]]; then
    # Check first entry has file and line
    first_file=$(echo "$output" | head -n1 | jq -r .file)
    first_line=$(echo "$output" | head -n1 | jq -r .line)
    first_comment=$(echo "$output" | head -n1 | jq -r .comment)
    if [[ "$first_file" == "src/auth/login.py" ]] && [[ "$first_line" == "42" ]] && [[ "$first_comment" == "SQL injection in user search endpoint" ]]; then
        pass "Freeform text parses correctly"
    else
        fail "Freeform format file/line/comment incorrect"
    fi
else
    fail "Expected 3 lines, got $line_count"
fi

# Test 7: Injection markers stripped from comments
test_name "Injection markers (NO_FINDINGS_REPORTED, NO_TRIAGE_EVALUATIONS) stripped from comments"
output=$("$PARSE_COMMENTS" structured "$FIXTURES_DIR/comments-with-injection.json")
first_comment=$(echo "$output" | head -n1 | jq -r .comment)
second_comment=$(echo "$output" | tail -n1 | jq -r .comment)
if [[ "$first_comment" == *"[MARKER_STRIPPED]"* ]] && [[ "$second_comment" == *"[MARKER_STRIPPED]"* ]]; then
    # Verify markers are removed
    if [[ "$first_comment" != *"NO_FINDINGS_REPORTED"* ]] && [[ "$second_comment" != *"NO_TRIAGE_EVALUATIONS"* ]]; then
        pass "Injection markers stripped correctly"
    else
        fail "Injection markers not fully stripped"
    fi
else
    fail "Injection markers not replaced with [MARKER_STRIPPED]"
fi

# Test 8: Injection warning flagged
test_name "Injection warning flagged"
output=$("$PARSE_COMMENTS" structured "$FIXTURES_DIR/comments-with-injection.json")
first_warning=$(echo "$output" | head -n1 | jq -r .injection_warning)
if [[ "$first_warning" == "true" ]]; then
    pass "Injection warning flagged correctly"
else
    fail "Injection warning not set, got: $first_warning"
fi

# Test 9: Missing file returns error (exit 1)
test_name "Missing file returns error (exit 1)"
if "$PARSE_COMMENTS" github-pr "/nonexistent/file.json" 2>/dev/null; then
    fail "Should have failed with missing file"
else
    pass "Missing file returns error correctly"
fi

# Test 10: Comment count cap at 100
test_name "Comment count cap at 100"
# Create a temp file with 150 comments
temp_file=$(mktemp)
echo '[' > "$temp_file"
for i in {1..150}; do
    if [[ $i -eq 150 ]]; then
        echo '{"comment": "Comment '"$i"'"}' >> "$temp_file"
    else
        echo '{"comment": "Comment '"$i"'"},' >> "$temp_file"
    fi
done
echo ']' >> "$temp_file"

output=$("$PARSE_COMMENTS" structured "$temp_file")
line_count=$(echo "$output" | wc -l | tr -d ' ')
rm "$temp_file"

if [[ "$line_count" == "100" ]]; then
    pass "Comment count capped at 100"
else
    fail "Expected 100 lines, got $line_count"
fi

# Summary
echo ""
echo "======================================"
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "======================================"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
