#!/usr/bin/env bash
# Integration test: RFE profile validation, config, and shared pipeline logic
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$SCRIPT_DIR/scripts"
FIXTURES="$SCRIPT_DIR/tests/fixtures"
PASS=0
FAIL=0
TEMP_FILES=()

cleanup() {
    for f in "${TEMP_FILES[@]}"; do
        rm -f "$f"
    done
}
trap cleanup EXIT

assert_check() {
    local desc="$1" condition="$2"
    if eval "$condition"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc"
        FAIL=$((FAIL + 1))
    fi
}

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

echo "=== RFE profile integration tests ==="

# --- Section 1: Profile config ---
echo ""
echo "--- Test: profile-config.sh reads rfe config ---"
if [[ -f "$SCRIPTS/profile-config.sh" ]]; then
    agents=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/rfe" agents 2>/dev/null || echo "")
    if [[ -n "$agents" ]]; then
        echo "  PASS: rfe profile config readable"
        PASS=$((PASS + 1))
        # Verify rfe has 5 agents (REQ, FEAS, ARCH, SEC, COMPAT)
        count=$(echo "$agents" | grep -c "prefix:" || true)
        assert_check "rfe profile has 5 agents (got $count)" "[[ $count -eq 5 ]]"
    else
        echo "  FAIL: rfe profile config returned empty agents"
        FAIL=$((FAIL + 1))
    fi

    has_verdicts=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/rfe" has_verdicts 2>/dev/null || echo "")
    assert_check "rfe profile has_verdicts=true" "[[ '$has_verdicts' == 'true' ]]"

    evidence_format=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/rfe" evidence_format 2>/dev/null || echo "")
    assert_check "rfe profile evidence_format=text_citation" "[[ '$evidence_format' == 'text_citation' ]]"

    phase5=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/rfe" phase5_enabled 2>/dev/null || echo "")
    assert_check "rfe profile phase5_enabled=false" "[[ '$phase5' == 'false' ]]"

    pipeline=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/rfe" pipeline_enabled 2>/dev/null || echo "")
    assert_check "rfe profile pipeline_enabled=true" "[[ '$pipeline' == 'true' ]]"

    quick=$("$SCRIPTS/profile-config.sh" "$SCRIPT_DIR/profiles/rfe" quick_specialists 2>/dev/null || echo "")
    assert_check "rfe quick_specialists includes REQ" "echo '$quick' | grep -q 'REQ'"
    assert_check "rfe quick_specialists includes SEC" "echo '$quick' | grep -q 'SEC'"
else
    echo "  SKIP: profile-config.sh not found"
fi

# --- Section 2: RFE finding validation ---
echo ""
echo "--- Test: valid rfe finding passes validation ---"
rfe_finding=$(mktemp "${TMPDIR:-/tmp}/rfe-finding-XXXXXX")
TEMP_FILES+=("$rfe_finding")
cat > "$rfe_finding" << 'FIXTURE'
Finding ID: REQ-001
Specialist: Requirements Analyst
Severity: Important
Confidence: High
Document: RFE-model-upload-api
Citation: Requirements, FR-3
Title: Functional requirement FR-3 lacks measurable target for concurrent uploads
Evidence: FR-3 states "system should handle concurrent uploads" but does not specify a concurrency target. Without a number, this requirement is untestable. The acceptance criteria section does not clarify this either. A test engineer cannot determine whether 10 concurrent uploads or 1000 concurrent uploads satisfies this requirement, making it unverifiable.
Recommended fix: Change FR-3 to "system must support at least 50 concurrent uploads per tenant with p99 latency under 5 seconds" and add a corresponding acceptance criterion.
Verdict: Revise
FIXTURE

result=$("$SCRIPTS/validate-output.sh" "$rfe_finding" REQ --profile rfe 2>&1)
exit_code=$?
assert_exit "valid rfe finding accepted" "0" "$exit_code"

if echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['valid'] == True" 2>/dev/null; then
    echo "  PASS: validation JSON reports valid=true"
    PASS=$((PASS + 1))
else
    echo "  FAIL: validation should report valid=true"
    FAIL=$((FAIL + 1))
fi

# --- Section 3: RFE finding with COMPAT prefix ---
echo ""
echo "--- Test: COMPAT prefix accepted for rfe profile ---"
compat_finding=$(mktemp "${TMPDIR:-/tmp}/rfe-compat-XXXXXX")
TEMP_FILES+=("$compat_finding")
cat > "$compat_finding" << 'FIXTURE'
Finding ID: COMPAT-001
Specialist: Compatibility Analyst
Severity: Critical
Confidence: High
Document: RFE-model-upload-api
Citation: Proposed Solution, paragraph 4
Title: New upload endpoint changes response format without deprecation period
Evidence: The Proposed Solution states "the /v1/models/upload endpoint will return a structured JSON response with upload_id and status fields" (paragraph 4), replacing the current plain-text response. Existing clients that parse the plain-text response will break without warning. No deprecation period, versioned endpoint, or Accept header negotiation is specified in the Migration & Compatibility section.
Recommended fix: Add a versioned endpoint (/v2/models/upload) with the new response format. Keep /v1 unchanged for at least 2 minor releases.
Verdict: Reject
FIXTURE

result=$("$SCRIPTS/validate-output.sh" "$compat_finding" COMPAT --profile rfe 2>&1)
exit_code=$?
assert_exit "COMPAT finding accepted" "0" "$exit_code"

# --- Section 4: RFE zero findings with verdict ---
echo ""
echo "--- Test: rfe zero findings requires verdict ---"
rfe_zero=$(mktemp "${TMPDIR:-/tmp}/rfe-zero-XXXXXX")
TEMP_FILES+=("$rfe_zero")
echo "NO_FINDINGS_REPORTED" > "$rfe_zero"

result=$("$SCRIPTS/validate-output.sh" "$rfe_zero" REQ --profile rfe 2>&1)
exit_code=$?
assert_exit "zero findings without verdict rejected for rfe" "1" "$exit_code"

# Now with verdict
rfe_zero_ok=$(mktemp "${TMPDIR:-/tmp}/rfe-zero-ok-XXXXXX")
TEMP_FILES+=("$rfe_zero_ok")
cat > "$rfe_zero_ok" << 'FIXTURE'
NO_FINDINGS_REPORTED
Verdict: Approve
FIXTURE

result=$("$SCRIPTS/validate-output.sh" "$rfe_zero_ok" REQ --profile rfe 2>&1)
exit_code=$?
assert_exit "zero findings with verdict accepted for rfe" "0" "$exit_code"

# --- Section 5: Code finding fails rfe validation ---
echo ""
echo "--- Test: code finding fails rfe validation ---"
result=$("$SCRIPTS/validate-output.sh" "$FIXTURES/valid-finding.txt" SEC --profile rfe 2>&1)
if echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
errors = ' '.join(d.get('errors', []))
assert 'Document' in errors or d['valid'] == False
" 2>/dev/null; then
    echo "  PASS: code finding rejected by rfe validator"
    PASS=$((PASS + 1))
else
    echo "  FAIL: code finding should fail rfe validation"
    FAIL=$((FAIL + 1))
fi

# --- Section 6: Budget estimate for rfe profile ---
echo ""
echo "--- Test: budget estimate works for rfe agent count (5 specialists) ---"
budget_result=$("$SCRIPTS/track-budget.sh" estimate 5 15000 3 0 0 0)
exit_code=$?
assert_exit "budget estimate for 5 rfe agents succeeds" "0" "$exit_code"

est=$(echo "$budget_result" | python3 -c "import json,sys; print(json.load(sys.stdin)['estimated_tokens'])")
assert_check "estimate is positive ($est > 0)" "[[ $est -gt 0 ]]"

# --- Section 7: Convergence detection with rfe findings ---
echo ""
echo "--- Test: convergence detection with rfe findings ---"
"$SCRIPTS/detect-convergence.sh" "$rfe_finding" "$rfe_finding" >/dev/null 2>&1
assert_exit "convergence detected for identical rfe findings" "0" "$?"

"$SCRIPTS/detect-convergence.sh" "$rfe_finding" "$compat_finding" >/dev/null 2>&1
conv_exit=$?
assert_check "different rfe findings do not converge (exit=$conv_exit)" "[[ $conv_exit -ne 0 ]]"

# --- Section 8: RFE template structure ---
echo ""
echo "--- Test: rfe template has expected sections ---"
template="$SCRIPT_DIR/profiles/rfe/templates/rfe-template.md"
assert_check "rfe template exists" "[[ -f '$template' ]]"
assert_check "template has TL;DR" "grep -q '## TL;DR' '$template'"
assert_check "template has Proposed Solution" "grep -q '## Proposed Solution' '$template'"
assert_check "template has Requirements" "grep -q '## Requirements' '$template'"
assert_check "template has Migration & Compatibility" "grep -q '## Migration & Compatibility' '$template'"
assert_check "template has 9 level-2 sections" "[[ \$(grep -c '^## ' '$template') -eq 9 ]]"
section_count=$(grep -c '^## ' "$template" || true)
assert_check "template has expected heading count ($section_count)" "[[ $section_count -ge 9 ]]"

# --- Section 9: RFE agent files exist ---
echo ""
echo "--- Test: all rfe agent files exist ---"
agents_dir="$SCRIPT_DIR/profiles/rfe/agents"
for agent in requirements-analyst.md feasibility-analyst.md architecture-reviewer.md security-analyst.md compatibility-analyst.md devils-advocate.md refine-staff-engineer.md refine-product-architect.md refine-security-engineer.md refine-mediator.md; do
    assert_check "agent file $agent exists" "[[ -f '$agents_dir/$agent' ]]"
done

# --- Section 10: Manifest integrity ---
echo ""
echo "--- Test: manifest.json lists all review agents ---"
manifest="$agents_dir/manifest.json"
assert_check "manifest.json exists" "[[ -f '$manifest' ]]"
for agent in requirements-analyst.md feasibility-analyst.md architecture-reviewer.md security-analyst.md compatibility-analyst.md devils-advocate.md; do
    assert_check "manifest lists $agent" "grep -q '$agent' '$manifest'"
done

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
