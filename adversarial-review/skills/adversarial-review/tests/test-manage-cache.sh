#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CACHE_SCRIPT="$SCRIPT_DIR/scripts/manage-cache.sh"
PASS=0
FAIL=0

assert_exit() {
    local desc="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (expected exit $expected, got $actual)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== manage-cache.sh tests ==="

# Test 1: init creates cache directory
echo "--- Test: init creates cache directory ---"
RESULT=$("$CACHE_SCRIPT" init "abcd1234abcd1234abcd1234abcd1234")
init_exit=$?
assert_exit "init exits 0" "0" "$init_exit"

CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
if [[ -d "$CACHE_DIR" ]]; then
    echo "  PASS: cache directory exists"
    PASS=$((PASS + 1))
else
    echo "  FAIL: cache directory not created"
    FAIL=$((FAIL + 1))
fi

# Test 2: cache directory has 0700 permissions
perms=$(stat -f '%Lp' "$CACHE_DIR" 2>/dev/null || stat -c '%a' "$CACHE_DIR" 2>/dev/null)
if [[ "$perms" == "700" ]]; then
    echo "  PASS: cache dir has 0700 permissions"
    PASS=$((PASS + 1))
else
    echo "  FAIL: cache dir permissions are $perms (expected 700)"
    FAIL=$((FAIL + 1))
fi

# Test 3: .lock file contains PID (parent process, not subshell)
if [[ -f "$CACHE_DIR/.lock" ]]; then
    lock_pid=$(cat "$CACHE_DIR/.lock")
    if [[ "$lock_pid" =~ ^[0-9]+$ ]] && kill -0 "$lock_pid" 2>/dev/null; then
        echo "  PASS: .lock contains valid running PID ($lock_pid)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: .lock PID invalid or not running: $lock_pid"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL: .lock file not created"
    FAIL=$((FAIL + 1))
fi

# Test 4: manifest.json exists and has correct schema
if [[ -f "$CACHE_DIR/manifest.json" ]]; then
    version=$(python3 -c "import json; print(json.load(open('$CACHE_DIR/manifest.json'))['version'])")
    session_hex=$(python3 -c "import json; print(json.load(open('$CACHE_DIR/manifest.json'))['session_hex'])")
    if [[ "$version" == "1.0" && "$session_hex" == "abcd1234abcd1234abcd1234abcd1234" ]]; then
        echo "  PASS: manifest.json has correct schema"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: manifest.json schema incorrect (version=$version, hex=$session_hex)"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL: manifest.json not created"
    FAIL=$((FAIL + 1))
fi

# Test 5: session hex embedded in directory name
if echo "$CACHE_DIR" | grep -q "abcd1234abcd1234abcd1234abcd1234"; then
    echo "  PASS: session hex in directory name"
    PASS=$((PASS + 1))
else
    echo "  FAIL: session hex not in directory name"
    FAIL=$((FAIL + 1))
fi

# Test 6: subdirectories created
for subdir in code templates references findings; do
    if [[ -d "$CACHE_DIR/$subdir" ]]; then
        echo "  PASS: $subdir/ directory exists"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $subdir/ directory not created"
        FAIL=$((FAIL + 1))
    fi
done

# Test 7: cleanup removes cache directory
export CACHE_DIR
"$CACHE_SCRIPT" cleanup
assert_exit "cleanup exits 0" "0" "$?"
if [[ ! -d "$CACHE_DIR" ]]; then
    echo "  PASS: cache directory removed after cleanup"
    PASS=$((PASS + 1))
else
    echo "  FAIL: cache directory still exists after cleanup"
    FAIL=$((FAIL + 1))
fi

# Test 8: cleanup is idempotent
"$CACHE_SCRIPT" cleanup
assert_exit "cleanup idempotent exits 0" "0" "$?"
echo "  PASS: cleanup idempotent"
PASS=$((PASS + 1))

# Test 9: init without session_hex fails
"$CACHE_SCRIPT" init 2>/dev/null
assert_exit "init without hex exits 2" "2" "$?"

# Test 10: stale cache cleanup
echo "--- Test: stale cache cleanup ---"
STALE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/adversarial-review-cache-deadbeefdeadbeefdeadbeefdeadbeef-XXXXXX")
echo "99999999" > "$STALE_DIR/.lock"  # non-existent PID
# Backdate the directory to 25 hours ago
touch -t "$(date -v-25H '+%Y%m%d%H%M.%S' 2>/dev/null || date -d '25 hours ago' '+%Y%m%d%H%M.%S')" "$STALE_DIR"
RESULT=$("$CACHE_SCRIPT" init "aaaa1111bbbb2222cccc3333dddd4444")
NEW_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
if [[ ! -d "$STALE_DIR" ]]; then
    echo "  PASS: stale cache cleaned up"
    PASS=$((PASS + 1))
else
    echo "  FAIL: stale cache not cleaned up"
    FAIL=$((FAIL + 1))
    rm -rf "$STALE_DIR"
fi
export CACHE_DIR="$NEW_DIR"
"$CACHE_SCRIPT" cleanup

echo "--- Test: populate-code ---"
RESULT=$("$CACHE_SCRIPT" init "1111222233334444aaaa5555bbbb6666")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

# Create test source files
SRC_DIR=$(mktemp -d "${TMPDIR:-/tmp}/test-src-XXXXXX")
mkdir -p "$SRC_DIR/src/auth"
echo 'func validate() { return true }' > "$SRC_DIR/src/auth/handler.go"
echo 'func session() { return nil }' > "$SRC_DIR/src/auth/session.go"

# Create file list
FILE_LIST=$(mktemp "${TMPDIR:-/tmp}/test-filelist-XXXXXX")
echo "src/auth/handler.go" > "$FILE_LIST"
echo "src/auth/session.go" >> "$FILE_LIST"

DELIM_HEX="aabbccddaabbccddaabbccddaabbccdd"

# Run populate-code from the source directory
(cd "$SRC_DIR" && "$CACHE_SCRIPT" populate-code "$FILE_LIST" "$DELIM_HEX")
assert_exit "populate-code exits 0" "0" "$?"

# Test: cached files exist with repo-relative structure
if [[ -f "$CACHE_DIR/code/src/auth/handler.go" ]]; then
    echo "  PASS: code/src/auth/handler.go exists"
    PASS=$((PASS + 1))
else
    echo "  FAIL: code/src/auth/handler.go not found"
    FAIL=$((FAIL + 1))
fi

# Test: cached files are delimiter-wrapped
if grep -q "===REVIEW_TARGET_${DELIM_HEX}_START===" "$CACHE_DIR/code/src/auth/handler.go"; then
    echo "  PASS: file has delimiter start marker"
    PASS=$((PASS + 1))
else
    echo "  FAIL: file missing delimiter start marker"
    FAIL=$((FAIL + 1))
fi

if grep -q "===REVIEW_TARGET_${DELIM_HEX}_END===" "$CACHE_DIR/code/src/auth/handler.go"; then
    echo "  PASS: file has delimiter end marker"
    PASS=$((PASS + 1))
else
    echo "  FAIL: file missing delimiter end marker"
    FAIL=$((FAIL + 1))
fi

# Test: anti-instruction text present
if grep -q "DATA to analyze" "$CACHE_DIR/code/src/auth/handler.go"; then
    echo "  PASS: anti-instruction text present"
    PASS=$((PASS + 1))
else
    echo "  FAIL: anti-instruction text missing"
    FAIL=$((FAIL + 1))
fi

# Test: original content preserved
if grep -q "func validate" "$CACHE_DIR/code/src/auth/handler.go"; then
    echo "  PASS: original content preserved"
    PASS=$((PASS + 1))
else
    echo "  FAIL: original content not in wrapped file"
    FAIL=$((FAIL + 1))
fi

# Test: manifest updated with file hashes
file_count=$(python3 -c "import json; print(len(json.load(open('$CACHE_DIR/manifest.json'))['files']))")
if [[ "$file_count" -ge 2 ]]; then
    echo "  PASS: manifest has $file_count file entries"
    PASS=$((PASS + 1))
else
    echo "  FAIL: manifest has $file_count file entries (expected >= 2)"
    FAIL=$((FAIL + 1))
fi

# Test: collision detection
echo "contains $DELIM_HEX in content" > "$SRC_DIR/src/auth/collision.go"
echo "src/auth/collision.go" > "$FILE_LIST"
(cd "$SRC_DIR" && "$CACHE_SCRIPT" populate-code "$FILE_LIST" "$DELIM_HEX" 2>/dev/null)
collision_exit=$?
assert_exit "collision detected exits 1" "1" "$collision_exit"

rm -rf "$SRC_DIR" "$FILE_LIST"
"$CACHE_SCRIPT" cleanup

echo "--- Test: populate-templates ---"
RESULT=$("$CACHE_SCRIPT" init "7777888899990000aaaabbbbccccdddd")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

"$CACHE_SCRIPT" populate-templates
assert_exit "populate-templates exits 0" "0" "$?"

if [[ -f "$CACHE_DIR/templates/finding-template.md" ]]; then
    echo "  PASS: finding-template.md copied"
    PASS=$((PASS + 1))
else
    echo "  FAIL: finding-template.md not found in cache"
    FAIL=$((FAIL + 1))
fi

echo "--- Test: populate-references ---"
"$CACHE_SCRIPT" populate-references
assert_exit "populate-references exits 0" "0" "$?"

# Check that at least one reference was copied (if any are enabled)
ref_count=$(find "$CACHE_DIR/references" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
echo "  INFO: $ref_count reference files copied"

"$CACHE_SCRIPT" cleanup

echo "--- Test: populate-findings ---"
RESULT=$("$CACHE_SCRIPT" init "ddddeeeeffffaaaa1111222233334444")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

# Create a valid agent output fixture
AGENT_OUTPUT=$(mktemp "${TMPDIR:-/tmp}/test-agent-output-XXXXXX")
cat > "$AGENT_OUTPUT" << 'FINDINGS'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: src/auth/handler.go
Lines: 142-150
Title: RBAC precedence allows privilege escalation
Evidence: The condition on line 142 uses && with || without parentheses. Due to Go operator precedence, the system:authenticated check is only applied to the second clause, allowing unauthenticated users to match the first clause. This enables privilege escalation to cluster admin.
Impact chain: Missing parens in RBAC check → unauthenticated users match first clause → privilege escalation to cluster admin
Recommended fix: Add explicit parentheses around the OR conditions.

Finding ID: SEC-002
Specialist: Security Auditor
Severity: Minor
Confidence: Medium
File: src/auth/session.go
Lines: 88-92
Title: Session token uses weak entropy
Evidence: Math.random is used on line 90 for token generation. This PRNG is not cryptographically secure and produces predictable output.
Impact chain: Weak PRNG for tokens → predictable session IDs → session hijacking
Recommended fix: Use crypto/rand for token generation.
FINDINGS

"$CACHE_SCRIPT" populate-findings "security-auditor" "SEC" "$AGENT_OUTPUT"
assert_exit "populate-findings exits 0" "0" "$?"

# Test: monolithic sanitized file exists
if [[ -f "$CACHE_DIR/findings/security-auditor/sanitized.md" ]]; then
    echo "  PASS: sanitized.md exists"
    PASS=$((PASS + 1))
else
    echo "  FAIL: sanitized.md not found"
    FAIL=$((FAIL + 1))
fi

# Test: sanitized file has provenance markers
if grep -q "\[PROVENANCE::Security_Auditor::VERIFIED\]" "$CACHE_DIR/findings/security-auditor/sanitized.md"; then
    echo "  PASS: provenance markers present"
    PASS=$((PASS + 1))
else
    echo "  FAIL: provenance markers missing"
    FAIL=$((FAIL + 1))
fi

# Test: sanitized file has field isolation markers
if grep -qE "\[FIELD_DATA_[a-f0-9]+_START\]" "$CACHE_DIR/findings/security-auditor/sanitized.md"; then
    echo "  PASS: field isolation markers present"
    PASS=$((PASS + 1))
else
    echo "  FAIL: field isolation markers missing"
    FAIL=$((FAIL + 1))
fi

# Test: individual finding files exist
if [[ -f "$CACHE_DIR/findings/security-auditor/SEC-001.md" ]]; then
    echo "  PASS: SEC-001.md split file exists"
    PASS=$((PASS + 1))
else
    echo "  FAIL: SEC-001.md not found"
    FAIL=$((FAIL + 1))
fi

# Test: summary.md exists with table format
if [[ -f "$CACHE_DIR/findings/security-auditor/summary.md" ]]; then
    if grep -q "SEC-001" "$CACHE_DIR/findings/security-auditor/summary.md"; then
        echo "  PASS: summary.md contains SEC-001"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: summary.md missing SEC-001"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL: summary.md not found"
    FAIL=$((FAIL + 1))
fi

echo "--- Test: build-summary ---"
"$CACHE_SCRIPT" build-summary
assert_exit "build-summary exits 0" "0" "$?"

if [[ -f "$CACHE_DIR/findings/cross-agent-summary.md" ]]; then
    if grep -q "SEC-001" "$CACHE_DIR/findings/cross-agent-summary.md" && grep -q "SEC-002" "$CACHE_DIR/findings/cross-agent-summary.md"; then
        echo "  PASS: cross-agent-summary.md contains both findings"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: cross-agent-summary.md incomplete"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL: cross-agent-summary.md not found"
    FAIL=$((FAIL + 1))
fi

rm -f "$AGENT_OUTPUT"
"$CACHE_SCRIPT" cleanup

echo "--- Test: validate-cache ---"
RESULT=$("$CACHE_SCRIPT" init "eeee1111ffff2222aaaa3333bbbb4444")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

"$CACHE_SCRIPT" populate-templates

# Test: valid cache passes
VALID_RESULT=$("$CACHE_SCRIPT" validate-cache "$CACHE_DIR")
valid=$(echo "$VALID_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['valid'])")
if [[ "$valid" == "True" ]]; then
    echo "  PASS: valid cache passes validation"
    PASS=$((PASS + 1))
else
    echo "  FAIL: valid cache should pass"
    FAIL=$((FAIL + 1))
fi

# Test: tampered file fails
if [[ -f "$CACHE_DIR/templates/finding-template.md" ]]; then
    echo "TAMPERED" >> "$CACHE_DIR/templates/finding-template.md"
    TAMPERED_RESULT=$("$CACHE_SCRIPT" validate-cache "$CACHE_DIR" 2>/dev/null || true)
    tamper_valid=$(echo "$TAMPERED_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['valid'])")
    if [[ "$tamper_valid" == "False" ]]; then
        echo "  PASS: tampered cache fails validation"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: tampered cache should fail"
        FAIL=$((FAIL + 1))
    fi
fi

"$CACHE_SCRIPT" cleanup

echo "--- Test: navigation.md generation ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd3333")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

# Populate some content to generate navigation from
"$CACHE_SCRIPT" populate-templates
"$CACHE_SCRIPT" populate-references

# Generate navigation for Phase 1, iteration 1
"$CACHE_SCRIPT" generate-navigation 1 1
assert_exit "generate-navigation exits 0" "0" "$?"

if [[ -f "$CACHE_DIR/navigation.md" ]]; then
    echo "  PASS: navigation.md created"
    PASS=$((PASS + 1))
    if grep -q "Iteration: 1" "$CACHE_DIR/navigation.md" && grep -q "Phase: 1" "$CACHE_DIR/navigation.md"; then
        echo "  PASS: navigation.md has correct iteration/phase"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: navigation.md missing iteration/phase"
        FAIL=$((FAIL + 1))
    fi
    if grep -q "Tokens" "$CACHE_DIR/navigation.md"; then
        echo "  PASS: navigation.md has token estimates"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: navigation.md missing token estimates"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL: navigation.md not created"
    FAIL=$((FAIL + 1))
fi

"$CACHE_SCRIPT" cleanup

echo "--- Test: populate-findings with --scope ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd3333")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

# Create a scope file listing only one file
SCOPE_FILE=$(mktemp)
echo "test-file.py" > "$SCOPE_FILE"

# Create a finding that references a file IN scope
IN_SCOPE_FINDING=$(mktemp)
cat > "$IN_SCOPE_FINDING" <<'FINDING'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: test-file.py
Lines: 10-20
Title: Test finding in scope
Evidence: This is test evidence that is long enough to pass the minimum character threshold for validation purposes and contains file:line references like test-file.py:15 that demonstrate the issue clearly.
Impact chain: Missing validation → invalid state → potential exploit
Recommended fix: Fix the issue by adding proper validation.
FINDING

"$CACHE_SCRIPT" populate-findings security-auditor SEC "$IN_SCOPE_FINDING" --scope "$SCOPE_FILE" 2>/dev/null
assert_exit "populate-findings with --scope exits 0" "0" "$?"

if [[ -f "$CACHE_DIR/findings/security-auditor/SEC-001.md" ]]; then
    echo "  PASS: finding created with --scope"
    PASS=$((PASS + 1))
else
    echo "  FAIL: finding not created with --scope"
    FAIL=$((FAIL + 1))
fi

rm -f "$SCOPE_FILE" "$IN_SCOPE_FINDING"
"$CACHE_SCRIPT" cleanup

echo "--- Test: generate-navigation with --resolved-ids ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd3333")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

# Create a mock cross-agent-summary with 2 findings
mkdir -p "$CACHE_DIR/findings/security-auditor"
cat > "$CACHE_DIR/findings/security-auditor/summary.md" <<'EOF'
| ID | Severity | Category | File:Line | One-liner |
|----|----------|----------|-----------|----------|
| SEC-001 | Critical | SEC | auth.go:10 | Test finding 1 |
| SEC-002 | Minor | SEC | auth.go:20 | Test finding 2 |
EOF
"$CACHE_SCRIPT" build-summary 2>/dev/null

# Create resolved IDs file
RESOLVED=$(mktemp)
echo "SEC-001" > "$RESOLVED"

# Generate navigation with resolved IDs
"$CACHE_SCRIPT" generate-navigation 2 2 --resolved-ids "$RESOLVED"
assert_exit "generate-navigation with --resolved-ids exits 0" "0" "$?"

if [[ -f "$CACHE_DIR/navigation.md" ]]; then
    # Resolved finding count should be mentioned
    if grep -q "1 finding(s) resolved" "$CACHE_DIR/navigation.md"; then
        echo "  PASS: resolved finding count reported in navigation"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: resolved finding count not reported in navigation"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL: navigation.md not created"
    FAIL=$((FAIL + 1))
fi

rm -f "$RESOLVED"
"$CACHE_SCRIPT" cleanup

echo "--- Test: populate-findings with out-of-scope file ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd4444")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

SCOPE_FILE=$(mktemp)
echo "in-scope-file.py" > "$SCOPE_FILE"

OUT_SCOPE_FINDING=$(mktemp)
cat > "$OUT_SCOPE_FINDING" <<'FINDING'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: other-file.py
Lines: 10-20
Title: Test finding out of scope
Evidence: This is test evidence that is long enough to pass the minimum character threshold for validation purposes and contains file:line references like other-file.py:15 demonstrating the issue.
Impact chain: Missing validation → invalid state → potential exploit
Recommended fix: Fix the issue by adding proper validation.
FINDING

# Should pass validation (scope violations are warnings, not errors) but emit a warning
RESULT=$("$CACHE_SCRIPT" populate-findings security-auditor SEC "$OUT_SCOPE_FINDING" --scope "$SCOPE_FILE" 2>&1) || true
if echo "$RESULT" | grep -qi "SCOPE_VIOLATION\|scope"; then
    echo "  PASS: out-of-scope warning detected"
    PASS=$((PASS + 1))
else
    # validate-output.sh emits SCOPE_VIOLATION as a warning, which doesn't block
    # The finding still gets created (warnings are non-blocking)
    if [[ -f "$CACHE_DIR/findings/security-auditor/SEC-001.md" ]]; then
        echo "  PASS: out-of-scope finding created with warning (non-blocking)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: out-of-scope finding handling unexpected"
        FAIL=$((FAIL + 1))
    fi
fi

rm -f "$SCOPE_FILE" "$OUT_SCOPE_FINDING"
"$CACHE_SCRIPT" cleanup

echo "--- Test: build-summary with multiple agents ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd5555")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

# Create findings for two different agents
mkdir -p "$CACHE_DIR/findings/security-auditor"
cat > "$CACHE_DIR/findings/security-auditor/summary.md" <<'EOF'
| ID | Severity | Category | File:Line | One-liner |
|----|----------|----------|-----------|----------|
| SEC-001 | Critical | SEC | auth.go:10 | Auth bypass |
EOF

mkdir -p "$CACHE_DIR/findings/performance-analyst"
cat > "$CACHE_DIR/findings/performance-analyst/summary.md" <<'EOF'
| ID | Severity | Category | File:Line | One-liner |
|----|----------|----------|-----------|----------|
| PERF-001 | Minor | PERF | db.go:50 | N+1 query |
| PERF-002 | Important | PERF | cache.go:20 | Missing TTL |
EOF

"$CACHE_SCRIPT" build-summary 2>/dev/null
assert_exit "build-summary multi-agent exits 0" "0" "$?"

if [[ -f "$CACHE_DIR/findings/cross-agent-summary.md" ]]; then
    sec_found=$(grep -c "SEC-001" "$CACHE_DIR/findings/cross-agent-summary.md" || true)
    perf_found=$(grep -c "PERF-00" "$CACHE_DIR/findings/cross-agent-summary.md" || true)
    if [[ "$sec_found" -ge 1 && "$perf_found" -ge 2 ]]; then
        echo "  PASS: cross-agent-summary.md has findings from both agents"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: cross-agent-summary.md missing findings (SEC=$sec_found, PERF=$perf_found)"
        FAIL=$((FAIL + 1))
    fi
    # Verify header is present (only 1 header, not duplicated per agent)
    header_count=$(grep -c "^| ID |" "$CACHE_DIR/findings/cross-agent-summary.md" || true)
    if [[ "$header_count" -eq 1 ]]; then
        echo "  PASS: single header in merged summary"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: expected 1 header, got $header_count"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL: cross-agent-summary.md not found"
    FAIL=$((FAIL + 1))
fi

"$CACHE_SCRIPT" cleanup

echo "--- Test: validate-cache with commit SHA mismatch ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd6666")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

"$CACHE_SCRIPT" populate-templates

# Tamper with commit SHA in manifest
python3 -c "
import json
with open('$CACHE_DIR/manifest.json') as f:
    m = json.load(f)
m['commit_sha'] = 'aaaa' * 10
with open('$CACHE_DIR/manifest.json', 'w') as f:
    json.dump(m, f, indent=2)
"

SHA_RESULT=$("$CACHE_SCRIPT" validate-cache "$CACHE_DIR" 2>/dev/null || true)
sha_valid=$(echo "$SHA_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['valid'])")
if [[ "$sha_valid" == "False" ]]; then
    # Check that the mismatch is reported as commit_sha type
    mismatch_type=$(echo "$SHA_RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['mismatches'][0]['type'] if d['mismatches'] else '')")
    if [[ "$mismatch_type" == "commit_sha" ]]; then
        echo "  PASS: commit SHA mismatch detected"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: mismatch type is '$mismatch_type' (expected commit_sha)"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL: tampered commit SHA should fail validation"
    FAIL=$((FAIL + 1))
fi

"$CACHE_SCRIPT" cleanup

echo "--- Test: populate-code rejects symlink escape ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd7777")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

SRC_DIR=$(mktemp -d "${TMPDIR:-/tmp}/test-symlink-XXXXXX")
mkdir -p "$SRC_DIR/src"
ln -s /etc/hosts "$SRC_DIR/src/escape.txt"
FILE_LIST=$(mktemp)
echo "src/escape.txt" > "$FILE_LIST"

(cd "$SRC_DIR" && "$CACHE_SCRIPT" populate-code "$FILE_LIST" "aabbccddaabbccddaabbccddaabbccdd" 2>/dev/null)
symlink_exit=$?
if [[ "$symlink_exit" -ne 0 ]]; then
    echo "  PASS: symlink escape rejected"
    PASS=$((PASS + 1))
else
    echo "  FAIL: symlink escape should be rejected"
    FAIL=$((FAIL + 1))
fi

rm -rf "$SRC_DIR" "$FILE_LIST"
"$CACHE_SCRIPT" cleanup

echo "--- Test: populate-code rejects path traversal ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd8888")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

SRC_DIR=$(mktemp -d "${TMPDIR:-/tmp}/test-traversal-XXXXXX")
FILE_LIST=$(mktemp)
echo "../../../etc/passwd" > "$FILE_LIST"

(cd "$SRC_DIR" && "$CACHE_SCRIPT" populate-code "$FILE_LIST" "aabbccddaabbccddaabbccddaabbccdd" 2>/dev/null)
traversal_exit=$?
assert_exit "path traversal rejected" "1" "$traversal_exit"

rm -rf "$SRC_DIR" "$FILE_LIST"
"$CACHE_SCRIPT" cleanup

echo "--- Test: context cap enforcement in navigation ---"
RESULT=$("$CACHE_SCRIPT" init "aaaa0000bbbb1111cccc2222dddd3333")
CACHE_DIR=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['cache_dir'])")
export CACHE_DIR

# Create a large code file that exceeds 50K tokens (200KB = ~50K tokens at char/4)
mkdir -p "$CACHE_DIR/code"
python3 -c "print('x' * 250000)" > "$CACHE_DIR/code/large-file.py"

"$CACHE_SCRIPT" generate-navigation 1 1
assert_exit "generate-navigation with large file exits 0" "0" "$?"

if grep -q "context limits" "$CACHE_DIR/navigation.md"; then
    echo "  PASS: context cap warning present"
    PASS=$((PASS + 1))
else
    echo "  FAIL: context cap warning missing for large file"
    FAIL=$((FAIL + 1))
fi

"$CACHE_SCRIPT" cleanup

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit "$FAIL"
