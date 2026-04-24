#!/usr/bin/env bash
# Integration test: update-references.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$SCRIPT_DIR/scripts"
FIXTURES="$SCRIPT_DIR/tests/fixtures"
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

assert_contains() {
    local desc="$1" haystack="$2" needle="$3"
    if echo "$haystack" | grep -qF -- "$needle"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (output does not contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local desc="$1" haystack="$2" needle="$3"
    if ! echo "$haystack" | grep -qF -- "$needle"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (output should not contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== update-references.sh integration test ==="

# Test 1: --check-only identifies modules with source_url
echo "Test 1: --check-only identifies modules with source_url"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
# Create a fake remote file for testing
REMOTE_FILE=$(mktemp)
cat > "$REMOTE_FILE" <<'EOF'
---
name: test-module
specialist: security
version: "1.0.0"
last_updated: "2026-03-20"
source_url: "https://example.com/test-module.md"
description: "Test reference module for unit tests"
enabled: true
---

# Test Module

## Verification Patterns

- Check for hardcoded credentials in configuration files
- Verify TLS certificate validation is not disabled
EOF
result=$("$SCRIPTS/update-references.sh" --check-only --test-remote "$REMOTE_FILE" --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "update-references.sh exits 0" "0" "$exit_code"
assert_contains "Output shows module found" "$result" "Found 1 module(s) with source_url"
assert_contains "Output shows test-module" "$result" "test-module"
rm -f "$REMOTE_FILE"
rm -rf "$TEMP_DIR"

# Test 2: --check-only skips modules without source_url
echo ""
echo "Test 2: --check-only skips modules without source_url"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
# Create module without source_url
cat > "$TEMP_DIR/security/no-source.md" <<'EOF'
---
name: no-source-module
specialist: security
version: "1.0.0"
enabled: true
---
# No source URL
EOF
result=$("$SCRIPTS/update-references.sh" --check-only --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0" "0" "$exit_code"
assert_contains "Output shows no modules found" "$result" "No modules with source_url found"
rm -rf "$TEMP_DIR"

# Test 3: --check-only does not modify files
echo ""
echo "Test 3: --check-only does not modify files"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
MODULE_FILE="$TEMP_DIR/security/sample-reference-valid.md"
# Get file hash before
HASH_BEFORE=$(shasum -a 256 "$MODULE_FILE" | awk '{print $1}')
# Create remote with different version
REMOTE_FILE=$(mktemp)
cat > "$REMOTE_FILE" <<'EOF'
---
name: test-module
specialist: security
version: "2.0.0"
enabled: true
---
# Updated module
EOF
result=$("$SCRIPTS/update-references.sh" --check-only --test-remote "$REMOTE_FILE" --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0" "0" "$exit_code"
# Get file hash after
HASH_AFTER=$(shasum -a 256 "$MODULE_FILE" | awk '{print $1}')
if [[ "$HASH_BEFORE" == "$HASH_AFTER" ]]; then
    echo "  PASS: File unchanged in check-only mode"
    PASS=$((PASS + 1))
else
    echo "  FAIL: File was modified in check-only mode"
    FAIL=$((FAIL + 1))
fi
assert_contains "Output shows check-only message" "$result" "--check-only mode: no files modified"
rm -f "$REMOTE_FILE"
rm -rf "$TEMP_DIR"

# Test 4: Same version shows "up to date"
echo ""
echo "Test 4: Same version shows 'up to date'"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
# Create local module with version 1.0.0
cat > "$TEMP_DIR/security/test.md" <<'EOF'
---
name: test-module
specialist: security
version: "1.0.0"
source_url: "https://example.com/test.md"
enabled: true
---
# Test content
EOF
# Create remote with same version and same content
REMOTE_FILE=$(mktemp)
cat > "$REMOTE_FILE" <<'EOF'
---
name: test-module
specialist: security
version: "1.0.0"
source_url: "https://example.com/test.md"
enabled: true
---
# Test content
EOF
result=$("$SCRIPTS/update-references.sh" --check-only --test-remote "$REMOTE_FILE" --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0" "0" "$exit_code"
assert_contains "Output shows up to date" "$result" "UP TO DATE"
rm -f "$REMOTE_FILE"
rm -rf "$TEMP_DIR"

# Test 5: Newer version detected
echo ""
echo "Test 5: Newer version detected"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
# Create local module with version 1.0.0
cat > "$TEMP_DIR/security/test.md" <<'EOF'
---
name: test-module
specialist: security
version: "1.0.0"
source_url: "https://example.com/test.md"
enabled: true
---
# Test content
EOF
# Create remote with version 1.1.0
REMOTE_FILE=$(mktemp)
cat > "$REMOTE_FILE" <<'EOF'
---
name: test-module
specialist: security
version: "1.1.0"
source_url: "https://example.com/test.md"
enabled: true
---
# Updated content
EOF
result=$("$SCRIPTS/update-references.sh" --check-only --test-remote "$REMOTE_FILE" --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0" "0" "$exit_code"
assert_contains "Output shows update available" "$result" "UPDATE AVAILABLE (1.0.0 → 1.1.0)"
rm -f "$REMOTE_FILE"
rm -rf "$TEMP_DIR"

# Test 6: Download failure handled gracefully
echo ""
echo "Test 6: Download failure handled gracefully"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
# Create module with nonexistent URL (no --test-remote, so it will try to download)
cat > "$TEMP_DIR/security/test.md" <<'EOF'
---
name: test-module
specialist: security
version: "1.0.0"
source_url: "https://nonexistent-domain-for-testing-12345.invalid/test.md"
enabled: true
---
# Test content
EOF
stderr=$(mktemp)
result=$("$SCRIPTS/update-references.sh" --check-only --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent 2>"$stderr")
exit_code=$?
stderr_output=$(cat "$stderr")
assert_exit "Script exits 0 despite download failure" "0" "$exit_code"
assert_contains "Warning emitted for download failure" "$stderr_output" "Failed to download"
# Module should still be counted but with warning
assert_contains "Output shows module found" "$result" "Found 1 module(s) with source_url"
rm -f "$stderr"
rm -rf "$TEMP_DIR"

# Test 7: Local version newer than remote
echo ""
echo "Test 7: Local version newer than remote"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
# Create local module with version 2.0.0
cat > "$TEMP_DIR/security/test.md" <<'EOF'
---
name: test-module
specialist: security
version: "2.0.0"
source_url: "https://example.com/test.md"
enabled: true
---
# Test content
EOF
# Create remote with version 1.0.0
REMOTE_FILE=$(mktemp)
cat > "$REMOTE_FILE" <<'EOF'
---
name: test-module
specialist: security
version: "1.0.0"
source_url: "https://example.com/test.md"
enabled: true
---
# Older content
EOF
result=$("$SCRIPTS/update-references.sh" --check-only --test-remote "$REMOTE_FILE" --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0" "0" "$exit_code"
assert_contains "Output shows local newer" "$result" "LOCAL NEWER (2.0.0 > 1.0.0)"
rm -f "$REMOTE_FILE"
rm -rf "$TEMP_DIR"

# Test 8: Same version but different content
echo ""
echo "Test 8: Same version but different content"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
# Create local module with version 1.0.0
cat > "$TEMP_DIR/security/test.md" <<'EOF'
---
name: test-module
specialist: security
version: "1.0.0"
source_url: "https://example.com/test.md"
enabled: true
---
# Original content
EOF
# Create remote with same version but different content
REMOTE_FILE=$(mktemp)
cat > "$REMOTE_FILE" <<'EOF'
---
name: test-module
specialist: security
version: "1.0.0"
source_url: "https://example.com/test.md"
enabled: true
---
# Different content here
EOF
result=$("$SCRIPTS/update-references.sh" --check-only --test-remote "$REMOTE_FILE" --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent)
exit_code=$?
assert_exit "Script exits 0" "0" "$exit_code"
assert_contains "Output shows content differs" "$result" "CONTENT DIFFERS (same version: 1.0.0)"
rm -f "$REMOTE_FILE"
rm -rf "$TEMP_DIR"

# Test 9: Malformed remote frontmatter handled gracefully
echo ""
echo "Test 9: Malformed remote frontmatter handled gracefully"
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/security"
cp "$FIXTURES/sample-reference-valid.md" "$TEMP_DIR/security/"
# Create malformed remote
REMOTE_FILE=$(mktemp)
echo "This is not valid YAML frontmatter" > "$REMOTE_FILE"
stderr=$(mktemp)
result=$("$SCRIPTS/update-references.sh" --check-only --test-remote "$REMOTE_FILE" --builtin-dir "$TEMP_DIR" --user-dir /nonexistent --project-dir /nonexistent 2>"$stderr")
exit_code=$?
stderr_output=$(cat "$stderr")
assert_exit "Script exits 0 despite malformed remote" "0" "$exit_code"
assert_contains "Warning emitted for malformed remote" "$stderr_output" "Malformed frontmatter"
rm -f "$REMOTE_FILE" "$stderr"
rm -rf "$TEMP_DIR"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
