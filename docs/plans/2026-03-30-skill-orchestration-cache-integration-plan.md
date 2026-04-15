# SKILL.md Orchestration Cache Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate manage-cache.sh into the adversarial-review orchestration pipeline so agents read from a local disk cache instead of receiving all context in their prompts.

**Architecture:** Edit SKILL.md, self-refinement.md, and challenge-round.md to make cache the default dispatch mode. Add `--scope` to populate-findings, `--resolved-ids` + context cap to generate-navigation, cache-path stripping to validate-output.sh. Add `--keep-cache`, `--reuse-cache`, `--delta` flags. Update input-isolation.md to document session-wide delimiters.

**Note:** All commit messages must include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` per project conventions.

**Tech Stack:** Bash (ShellCheck-compliant), Python3, Markdown (SKILL.md orchestration protocol)

**Spec:** `docs/specs/2026-03-30-skill-orchestration-cache-integration-design.md`

---

## File Structure

### Modified Files
| File | Change |
|------|--------|
| `scripts/manage-cache.sh` | Add `--scope` to populate-findings, `--resolved-ids` + context cap to generate-navigation, update usage header |
| `scripts/validate-output.sh` | Add cache-path prefix stripping fallback |
| `SKILL.md` | Add Phase 0 (cache init), new flags, step renumbering, error handling, cache navigation blocks |
| `phases/self-refinement.md` | Replace eager loading with minimal prompt + cache reads |
| `phases/challenge-round.md` | Replace sanitized doc injection with summary-first selective reading |
| `protocols/input-isolation.md` | Add session-wide delimiter relaxation note |
| `tests/test-manage-cache.sh` | Tests for `--scope`, `--resolved-ids`, context cap |
| `tests/test-validation-script.sh` | Test for cache-path stripping |

### No New Files

All changes are modifications to existing files.

### Naming Convention

The environment variable for the cache directory is `CACHE_DIR` (not `CACHE_PATH`). This was established in the foundation implementation (commit cc96ab2) and all new code in this plan must use `CACHE_DIR` consistently. The spec prerequisite #7 (naming standardization) is satisfied by the foundation — no additional rename work is needed.

---

### Task 1: Add `--scope` to populate-findings

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/scripts/manage-cache.sh:228-243`
- Modify: `adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`

- [ ] **Step 1: Write the failing test**

Add to `tests/test-manage-cache.sh` before the final summary block:

```bash
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`
Expected: FAIL — `populate-findings` does not accept `--scope` flag yet.

- [ ] **Step 3: Implement `--scope` in populate-findings**

In `manage-cache.sh`, modify the `populate-findings` case block. After parsing the 3 positional args (`AGENT`, `ROLE_PREFIX`, `FINDINGS_FILE`) at lines 229-231, add optional flag parsing. The current code does `shift` implicitly via positional `$2`, `$3`, `$4` — so we need to parse remaining args after `$4`.

Replace lines 228-243 with:

```bash
    populate-findings)
        AGENT="${2:?Usage: manage-cache.sh populate-findings <agent> <role_prefix> <findings_file> [--scope <file>]}"
        ROLE_PREFIX="${3:?Usage: manage-cache.sh populate-findings <agent> <role_prefix> <findings_file> [--scope <file>]}"
        FINDINGS_FILE="${4:?Usage: manage-cache.sh populate-findings <agent> <role_prefix> <findings_file> [--scope <file>]}"
        SCOPE_ARG=""
        # Parse optional flags after positional args
        shift 4
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --scope) SCOPE_ARG="${2:?--scope requires a file path}"; shift 2 ;;
                *) echo "{\"error\": \"Unknown flag: $1\"}" >&2; exit 2 ;;
            esac
        done
        if [[ -z "${CACHE_DIR:-}" ]]; then
            echo '{"error": "CACHE_DIR not set"}' >&2; exit 2
        fi
        if [[ ! -f "$FINDINGS_FILE" ]]; then
            echo "{\"error\": \"Findings file not found: $FINDINGS_FILE\"}" >&2; exit 2
        fi

        # Validate the findings using the caller-provided role prefix
        VALIDATE="$SCRIPT_DIR/validate-output.sh"
        VALIDATE_ARGS=("$FINDINGS_FILE" "$ROLE_PREFIX")
        if [[ -n "$SCOPE_ARG" ]]; then
            VALIDATE_ARGS+=(--scope "$SCOPE_ARG")
        fi
        if ! "$VALIDATE" "${VALIDATE_ARGS[@]}" >/dev/null 2>&1; then
            echo "{\"error\": \"Findings validation failed for agent $AGENT\"}" >&2
            exit 1
        fi
```

Keep the rest of the populate-findings case (sanitization, splitting, injection check) unchanged.

- [ ] **Step 4: Run tests**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`
Expected: All tests pass.

- [ ] **Step 5: Run full test suite**

Run: `bash adversarial-review/skills/adversarial-review/tests/run-all-tests.sh`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add adversarial-review/skills/adversarial-review/scripts/manage-cache.sh \
       adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh
git commit -m "feat: add --scope parameter to populate-findings

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Add `--resolved-ids` to generate-navigation

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/scripts/manage-cache.sh:430-517`
- Modify: `adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`

- [ ] **Step 1: Write the failing test**

Add to `tests/test-manage-cache.sh` before the final summary block:

```bash
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
    # Resolved finding count should be mentioned, and unresolved count should be correct
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`
Expected: FAIL — `generate-navigation` does not accept `--resolved-ids`.

- [ ] **Step 3: Implement `--resolved-ids` in generate-navigation**

In `manage-cache.sh`, modify the `generate-navigation` case. Replace lines 430-435 with:

```bash
    generate-navigation)
        ITERATION="${2:?Usage: manage-cache.sh generate-navigation <iteration> <phase> [--resolved-ids <file>]}"
        PHASE="${3:?Usage: manage-cache.sh generate-navigation <iteration> <phase> [--resolved-ids <file>]}"
        RESOLVED_IDS_FILE=""
        # Parse optional flags after positional args
        shift 3
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --resolved-ids) RESOLVED_IDS_FILE="${2:?--resolved-ids requires a file path}"; shift 2 ;;
                *) echo "{\"error\": \"Unknown flag: $1\"}" >&2; exit 2 ;;
            esac
        done
        if [[ -z "${CACHE_DIR:-}" ]]; then
            echo '{"error": "CACHE_DIR not set"}' >&2; exit 2
        fi
```

Then in the Python code block, add resolved ID filtering. Pass `RESOLVED_IDS_FILE` as a 4th argument to the Python script. Modify the Python code to:

1. Accept an optional 4th arg (resolved IDs file path)
2. If provided, load resolved IDs into a set
3. When listing findings in the summary section, skip any finding whose ID is in the resolved set

Replace the entire `python3 -c "..."` block with:

```bash
        python3 -c "
import os, sys

cache_dir = sys.argv[1]
iteration = int(sys.argv[2])
phase = int(sys.argv[3])
resolved_ids_file = sys.argv[4] if len(sys.argv) > 4 else ''

# Load resolved IDs if provided
resolved_ids = set()
if resolved_ids_file and os.path.isfile(resolved_ids_file):
    with open(resolved_ids_file) as f:
        resolved_ids = {line.strip() for line in f if line.strip()}

lines = []
lines.append('# Review Cache Navigation')
lines.append('')
lines.append(f'## Iteration: {iteration} | Phase: {phase} | Budget: ~50K tokens per agent')
lines.append('')

# Code files
code_dir = os.path.join(cache_dir, 'code')
if os.path.isdir(code_dir):
    lines.append('## Code Files (read before making claims)')
    lines.append('| File | Tokens (est.) |')
    lines.append('|------|---------------|')
    for root, dirs, files in sorted(os.walk(code_dir)):
        for f in sorted(files):
            full = os.path.join(root, f)
            rel = os.path.relpath(full, cache_dir)
            size = os.path.getsize(full)
            tokens = size // 4
            lines.append(f'| {rel} | {tokens:,} |')
    lines.append('')

# References
ref_dir = os.path.join(cache_dir, 'references')
if os.path.isdir(ref_dir) and os.listdir(ref_dir):
    lines.append('## Reference Modules (read on iteration 2+)')
    lines.append('| Module | Tokens (est.) |')
    lines.append('|--------|---------------|')
    for f in sorted(os.listdir(ref_dir)):
        if f.endswith('.md'):
            full = os.path.join(ref_dir, f)
            size = os.path.getsize(full)
            tokens = size // 4
            lines.append(f'| references/{f} | {tokens:,} |')
    lines.append('')

# Templates
tmpl_dir = os.path.join(cache_dir, 'templates')
if os.path.isdir(tmpl_dir):
    lines.append('## Templates')
    for f in sorted(os.listdir(tmpl_dir)):
        if f.endswith('.md'):
            lines.append(f'- templates/{f}')
    lines.append('')

# Findings (Phase 2 only)
findings_dir = os.path.join(cache_dir, 'findings')
summary = os.path.join(findings_dir, 'cross-agent-summary.md')
if phase == 2 and os.path.isfile(summary):
    lines.append('## Findings Summary')
    lines.append('- Read findings/cross-agent-summary.md first')
    lines.append('- Read full finding files only for findings in your domain or that you challenge')
    # Show unresolved finding count
    with open(summary) as sf:
        summary_lines = sf.readlines()
    # Data rows start at line 3 (after header + separator)
    data_rows = [l for l in summary_lines[2:] if l.strip()]
    # Column-based filtering: extract ID from first data column (| ID | ... |)
    def extract_row_id(row):
        cols = [c.strip() for c in row.split('|')]
        return cols[1] if len(cols) > 1 else ''
    unresolved = [r for r in data_rows if extract_row_id(r) not in resolved_ids]
    if resolved_ids:
        resolved_count = len(data_rows) - len(unresolved)
        if resolved_count > 0:
            lines.append(f'- {resolved_count} finding(s) resolved (omitted)')
    lines.append('')

# Phase instructions
lines.append('## Phase-Specific Instructions')
if phase == 1:
    lines.append('- **Phase 1:** Read all code files. Read references on iteration 2+.')
    lines.append('  Produce findings using the finding template format.')
else:
    lines.append('- **Phase 2:** Read findings/cross-agent-summary.md first.')
    lines.append('  Read full finding files only for findings in your domain or that')
    lines.append('  you intend to challenge. You MUST read the full finding before')
    lines.append('  issuing a Challenge.')
lines.append('')

lines.append('## Rules')
lines.append('- Use repo-relative paths in findings (e.g., \`src/auth/handler.go\`)')
lines.append('- Do NOT use cache paths in your output')

nav_path = os.path.join(cache_dir, 'navigation.md')
with open(nav_path, 'w') as f:
    f.write('\n'.join(lines) + '\n')
" "$CACHE_DIR" "$ITERATION" "$PHASE" "${RESOLVED_IDS_FILE:-}"
```

- [ ] **Step 4: Run tests**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`
Expected: All tests pass.

- [ ] **Step 5: Run full test suite**

Run: `bash adversarial-review/skills/adversarial-review/tests/run-all-tests.sh`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add adversarial-review/skills/adversarial-review/scripts/manage-cache.sh \
       adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh
git commit -m "feat: add --resolved-ids to generate-navigation

Omit resolved findings from navigation.md so agents focus on
unresolved findings during challenge iterations.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Add context cap enforcement to generate-navigation

**Depends on:** Task 2 (both modify the same `generate-navigation` Python block — Task 3 inserts into the code produced by Task 2).

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/scripts/manage-cache.sh` (generate-navigation Python block)
- Modify: `adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`

- [ ] **Step 1: Write the failing test**

Add to `tests/test-manage-cache.sh` before the final summary block:

```bash
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`
Expected: FAIL — no context cap logic in generate-navigation yet.

- [ ] **Step 3: Implement context cap**

In the `generate-navigation` Python code (from Task 2), add context cap logic after the code files section. After building the code file rows, compute the total token estimate. If it exceeds 50,000, add a warning note.

In the Python code, after the code files section (after the `lines.append('')` following the code file loop), add:

```python
    # Context cap enforcement (50K tokens)
    CONTEXT_CAP = 50000
    total_tokens = 0
    if os.path.isdir(code_dir):
        for root, dirs, files in os.walk(code_dir):
            for f in files:
                total_tokens += os.path.getsize(os.path.join(root, f)) // 4
    if os.path.isdir(ref_dir):
        for f in os.listdir(ref_dir):
            if f.endswith('.md'):
                total_tokens += os.path.getsize(os.path.join(ref_dir, f)) // 4
    if total_tokens > CONTEXT_CAP:
        lines.append(f'> **Warning:** Total estimated tokens ({total_tokens:,}) exceed the {CONTEXT_CAP:,} per-iteration context limits.')
        lines.append('>')
        # Build severity-ordered file list, omitting lowest-priority files
        file_entries = []
        if os.path.isdir(code_dir):
            for root, dirs, files in sorted(os.walk(code_dir)):
                for f in sorted(files):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, cache_dir)
                    tokens = os.path.getsize(full) // 4
                    file_entries.append((rel, tokens))
        # Sort by size descending — largest files listed first as candidates for skipping
        file_entries.sort(key=lambda x: x[1], reverse=True)
        running = 0
        included = []
        omitted = []
        for rel, tokens in file_entries:
            if running + tokens <= CONTEXT_CAP:
                included.append((rel, tokens))
                running += tokens
            else:
                omitted.append((rel, tokens))
        if omitted:
            lines.append(f'> {len(omitted)} file(s) omitted to stay within budget. Read these first:')
            for rel, tokens in included:
                lines.append(f'>   - {rel} ({tokens:,} tokens)')
            lines.append(f'> Omitted (read only if needed): {", ".join(r for r, _ in omitted)}')
        else:
            lines.append('> Prioritize reading Critical and Important findings first.')
        lines.append('')
```

Insert this block right before the `# Phase instructions` comment in the Python code.

- [ ] **Step 4: Run tests**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add adversarial-review/skills/adversarial-review/scripts/manage-cache.sh \
       adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh
git commit -m "feat: add context cap enforcement to generate-navigation

Warn when total token estimate exceeds 50K per-iteration cap.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Update manage-cache.sh usage header

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/scripts/manage-cache.sh:1-13`

- [ ] **Step 1: Update usage comment**

Replace lines 4-12 of `manage-cache.sh` with:

```bash
# Usage: manage-cache.sh <action> [args]
#   init <session_hex>                          — create cache directory, write manifest + lock
#   populate-code <file_list> <delimiter_hex>    — copy code files with delimiter wrapping
#   populate-templates                           — copy finding + challenge templates
#   populate-references                          — copy enabled reference modules
#   populate-findings <agent> <role_prefix> <findings_file> [--scope <file>]
#                                                — validate, sanitize, split findings
#   build-summary                                — merge agent summaries into cross-agent-summary.md
#   generate-navigation <iteration> <phase> [--resolved-ids <file>]
#                                                — generate navigation.md for agents
#   validate-cache <path>                        — verify file hashes against manifest
#   cleanup                                      — remove cache directory
```

- [ ] **Step 2: Run ShellCheck**

Run: `make lint`
Expected: ShellCheck passed.

- [ ] **Step 3: Commit**

```bash
git add adversarial-review/skills/adversarial-review/scripts/manage-cache.sh
git commit -m "docs: update manage-cache.sh usage header with all subcommands

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Add cache-path stripping to validate-output.sh

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/scripts/validate-output.sh`
- Modify: `adversarial-review/skills/adversarial-review/tests/test-validation-script.sh`

- [ ] **Step 1: Write the failing test**

Add to `tests/test-validation-script.sh` before the final summary block:

```bash
echo "=== Cache path stripping tests ==="

# Create a finding with a cache path instead of repo-relative path
CACHE_PATH_FINDING=$(mktemp)
cat > "$CACHE_PATH_FINDING" <<'FINDING'
Finding ID: SEC-001
Specialist: Security Auditor
Severity: Critical
Confidence: High
File: /var/folders/xx/adversarial-review-cache-abcd1234/code/src/auth/handler.go
Lines: 10-20
Title: RBAC bypass in handler
Evidence: The authentication handler at /var/folders/xx/adversarial-review-cache-abcd1234/code/src/auth/handler.go:15 allows unauthenticated access through a precedence bug in the RBAC check that skips validation when system:authenticated is the role.
FINDING

RESULT=$("$VALIDATE" "$CACHE_PATH_FINDING" SEC 2>&1) || true
# Should produce a warning about cache path stripping but still validate
if echo "$RESULT" | grep -qi "cache.*path\|stripped"; then
    echo "  PASS: cache path stripping warning emitted"
    PASS=$((PASS + 1))
else
    echo "  FAIL: no cache path stripping warning"
    FAIL=$((FAIL + 1))
fi

rm -f "$CACHE_PATH_FINDING"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-validation-script.sh`
Expected: FAIL — no cache-path stripping logic.

- [ ] **Step 3: Implement cache-path stripping**

In `validate-output.sh`, after the unicode normalization step (around line 47, after `content=$(python3 -c "...` block), add:

```bash
# Cache-path stripping fallback: if findings reference cache paths, strip prefix
CACHE_PATH_PATTERN='[^ ]*/adversarial-review-cache-[a-f0-9]+-[A-Za-z0-9._-]+/code/'
if echo "$content" | grep -qE "$CACHE_PATH_PATTERN"; then
    WARNINGS+=("Cache paths detected in output — stripping to repo-relative paths")
    content=$(echo "$content" | sed -E "s|$CACHE_PATH_PATTERN||g")
fi
```

- [ ] **Step 4: Run tests**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-validation-script.sh`
Expected: All tests pass.

- [ ] **Step 5: Run full test suite**

Run: `bash adversarial-review/skills/adversarial-review/tests/run-all-tests.sh`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add adversarial-review/skills/adversarial-review/scripts/validate-output.sh \
       adversarial-review/skills/adversarial-review/tests/test-validation-script.sh
git commit -m "feat: add cache-path prefix stripping to validate-output.sh

If agent output uses cache paths instead of repo-relative paths,
strip the prefix and emit a warning.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Update protocols/input-isolation.md

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/protocols/input-isolation.md`

- [ ] **Step 1: Add session-wide delimiter note**

After the "Anti-Instruction Wrapper" section (after line 37, before "### Field-Level Isolation"), add:

```markdown
### Session-Wide Delimiter Relaxation (Cache Mode)

When the local context cache is active (default), a single session-wide `REVIEW_TARGET` delimiter hex is used across all agents. This avoids duplicating every code file per agent in the cache directory.

This is a documented relaxation from per-agent delimiters. The trade-off is accepted because:
- The hex is 128-bit CSPRNG random (collision probability negligible)
- Collision-checked against all scope files before wrapping
- Agents never communicate directly — all cross-agent data flows through the orchestrator
- `FIELD_DATA` markers in sanitized findings retain per-field unique hex values (unchanged)

See the local context cache spec (Section 3) for full rationale.
```

- [ ] **Step 2: Commit**

```bash
git add adversarial-review/skills/adversarial-review/protocols/input-isolation.md
git commit -m "docs: document session-wide delimiter relaxation in cache mode

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Update SKILL.md — Add Phase 0 and step renumbering

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/SKILL.md`

This is the largest task — modifying the main orchestrator file. Changes:
1. Add new Step 3 (Initialize Cache) between current Step 2 and Step 3
2. Renumber all subsequent steps (+1)
3. Add `--keep-cache`, `--reuse-cache`, `--delta` to the Mode Flags table
4. Add flag interaction matrix
5. Add cache error handling table
6. Update the checklist
7. Update task tracking example
8. Add `manage-cache.sh` and `generate-navigation` to file structure reference

- [ ] **Step 1: Add new flags to Mode Flags table**

In SKILL.md, find the Mode Flags table (around line 64). Add these rows before the `--strict-scope` row:

```markdown
| `--keep-cache` | Preserve cache after review. Writes `.adversarial-review/last-cache.json` with session hex + commit SHA. Prints session hex for reuse. |
| `--reuse-cache <hex>` | Reuse an existing cache by session hex. Validates manifest (SHA-256 per file + commit SHA). Skips code/template/reference population. Findings regenerated. |
```

Also add `--delta`'s cache behavior — find the existing `--delta` row and append to its Effect cell: ` When `.adversarial-review/last-cache.json` exists, prompts user to reuse previous cache.`

- [ ] **Step 2: Add flag interaction matrix**

After the Mode Flags table, add:

```markdown
### Flag Interaction: Cache Flags

| Combination | Behavior |
|------------|----------|
| `--delta` + `--reuse-cache` | **Mutually exclusive.** Error: "Use --delta for auto-discovery or --reuse-cache for explicit reuse, not both." |
| `--diff` + `--reuse-cache` | **Mutually exclusive.** Error: "--diff creates a minimal cache from changed files; --reuse-cache expects a complete cache." |
| `--delta` + `--keep-cache` | Composable. Reuses previous cache if confirmed, preserves after completion. |
| `--reuse-cache` + `--keep-cache` | Composable. Reuses specified cache and preserves after completion. |
| `--diff` + `--delta` | Composable. Delta discovers previous cache; diff limits scope to changed files. |
```

- [ ] **Step 3: Add Step 3 — Initialize Cache**

After the "Pre-flight Budget Gate" section (around line 189), add:

```markdown
## Step 3: Initialize Cache

After scope confirmation and pre-flight budget check, initialize the local context cache before dispatching any agents.

### Cache Initialization Procedure

1. **Generate session hex:** Run `openssl rand -hex 16`. This identifies the cache session (separate from delimiter hex).
2. **Initialize cache directory:**
   ```bash
   scripts/manage-cache.sh init <session_hex>
   ```
   Capture `CACHE_DIR` from the JSON output (`{"cache_dir": "<path>", "session_hex": "<hex>"}`).
3. **Generate delimiter hex:** Run `scripts/generate-delimiters.sh` to produce a session-wide `REVIEW_TARGET` delimiter hex. Collision-check against all scope files.
4. **Populate code:**
   ```bash
   CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh populate-code <scope_file> <delimiter_hex>
   ```
5. **Populate templates:**
   ```bash
   CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh populate-templates
   ```
6. **Populate references:**
   ```bash
   CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh populate-references
   ```
7. **Generate navigation:**
   ```bash
   CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh generate-navigation 1 1
   ```
8. **Set cleanup trap** (via Bash tool):
   ```bash
   trap "CACHE_DIR='$CACHE_DIR' '$SCRIPT_DIR/manage-cache.sh' cleanup" EXIT HUP INT TERM
   ```
   **Skip this step if `--keep-cache` is specified.**
9. **Export `CACHE_DIR`** — all subsequent steps use this path.

**Session-wide delimiters:** In cache mode, a single `REVIEW_TARGET` delimiter hex is shared across all agents (see `protocols/input-isolation.md` Session-Wide Delimiter Relaxation). `FIELD_DATA` markers in sanitized findings retain per-field unique hex values.

**Failure:** If any step 2-7 fails, abort the review with error. See the Cache Errors table in Error Handling.

### `--reuse-cache <hex>` Override

When `--reuse-cache` is specified, replace steps 2-7 above with:

1. Validate hex: must match `^[a-f0-9]{32}$`.
2. Scan `$TMPDIR` for directories matching `adversarial-review-cache-<hex>-*`.
3. Run `scripts/manage-cache.sh validate-cache <path>`. If invalid, abort with mismatch details.
4. Set `CACHE_DIR` to the resolved path. Skip all populate steps.
5. Clear findings: `rm -rf "$CACHE_DIR/findings/"*` then `mkdir -p "$CACHE_DIR/findings"`.
6. Regenerate navigation: `scripts/manage-cache.sh generate-navigation 1 1`.

### `--delta` Auto-Discovery

When `--delta` is specified, check for `.adversarial-review/last-cache.json` in the repo root before cache initialization:

- **If found:** Display the session hex and commit SHA. Ask user to confirm reuse.
- **If confirmed:** Follow the `--reuse-cache` flow above with the discovered hex.
- **If declined or not found:** Proceed with normal cache initialization.

### `--keep-cache` Post-Review

After Phase 4 (Report) completes:

1. Write `.adversarial-review/last-cache.json`:
   ```json
   {"session_hex": "<hex>", "commit_sha": "<HEAD>"}
   ```
2. Print: "Cache preserved. Reuse with `--reuse-cache <hex>`"
```

- [ ] **Step 4: Renumber existing steps**

Find and replace all step references in SKILL.md:
- "Step 3: Phase 1" → "Step 4: Phase 1"
- "Step 4: Phase 2" → "Step 5: Phase 2"
- "Step 5: Phase 3" → "Step 6: Phase 3"
- "Step 6: Phase 4" → "Step 7: Phase 4"
- "Step 7: Phase 5" → "Step 8: Phase 5"
- Update the checklist at lines 36-43
- Update the task tracking example at lines 371-391
- Update all `[Step N]` references throughout

- [ ] **Step 5: Add cache errors to Error Handling**

In the Error Handling section (around line 349), add a new subsection:

```markdown
### Cache Errors

| Scenario | Response |
|----------|----------|
| `manage-cache.sh init` fails | Abort review with error |
| `populate-code` fails (collision, missing file) | Abort review — cache integrity cannot be guaranteed |
| `populate-templates` or `populate-references` fails | Abort review — agents need templates and references |
| `populate-findings` fails | Spawn fresh agent with error, max 2 retries. Exclude agent if retries exhausted. |
| `validate-cache` fails on `--reuse-cache` | Abort with mismatch details |
| `generate-navigation` fails | Non-fatal warning — agents use mandatory reads list from prompt |
| Cache directory disappears mid-review | Abort review — unrecoverable |
| `last-cache.json` missing on `--delta` | Treat as not found — create new cache, inform user |
```

- [ ] **Step 6: Add Phase 3/4/5 cache interaction notes**

In the SKILL.md sections for Phase 3 (Deduplication & Ranking), Phase 4 (Report), and Phase 5 (Cleanup), add cache interaction notes:

**Phase 3 (Deduplication & Ranking):** Add after the existing deduplication description:

```markdown
**Cache interaction:** Phase 3 reads deduplicated findings from `{CACHE_DIR}/findings/`. No cache writes — deduplication and ranking operate on the finding files already in the cache.
```

**Phase 4 (Report):** Add after the report generation description:

```markdown
**Cache interaction:** The final report reads from `{CACHE_DIR}/findings/` for all consensus findings. If `--keep-cache` is specified, write `.adversarial-review/last-cache.json` with session hex and commit SHA before cleanup.
```

**Phase 5 (Cleanup):** Add:

```markdown
**Cache interaction:** Unless `--keep-cache` is specified, the cleanup trap (set in Phase 0) removes the cache directory. If `--keep-cache` is active, the trap is skipped and the cache is preserved for future `--reuse-cache` use.
```

- [ ] **Step 7: Add manage-cache.sh to file structure**

In the File Structure Reference section (around line 458), add under `scripts/`:

```
    manage-cache.sh                   # Cache lifecycle: init, populate, validate, cleanup
```

- [ ] **Step 8: Commit**

```bash
git add adversarial-review/skills/adversarial-review/SKILL.md
git commit -m "feat: add Phase 0 cache initialization to SKILL.md

Add Step 3 (Initialize Cache), --keep-cache/--reuse-cache flags,
flag interaction matrix, cache error handling, step renumbering.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Update self-refinement.md — Minimal prompt dispatch

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/phases/self-refinement.md`

- [ ] **Step 1: Replace Steps 1-2 with cache-based dispatch**

Replace the "Step 1: Generate Isolation Delimiters" and "Step 2: Spawn Agents in Parallel" sections (lines 15-34) with:

```markdown
### Step 1: Agent Prompt Composition

For each active specialist, compose a minimal prompt (~2,825 tokens) containing:

| Content | Source | ~Tokens |
|---------|--------|---------|
| Role definition | `agents/<specialist>.md` (includes inoculation) | ~1,500 |
| Inoculation paragraphs (3) | Already in role files | ~500 |
| Delimiter values | Session-wide hex from Phase 0 | ~125 |
| Finding template | `templates/finding-template.md` inline | ~500 |
| Cache navigation block | See below | ~200 |

**Cache navigation block (included in prompt):**

```
## Cache Access

Your review materials are at: {CACHE_DIR}

Read `{CACHE_DIR}/navigation.md` FIRST — it tells you what's available and what to read.

## Mandatory Reads
Read these files before producing findings:
- {CACHE_DIR}/code/{file1}
- {CACHE_DIR}/code/{file2}
- ...

Rules:
- Read code files from `code/` before making claims about them
- Use repo-relative paths in findings (e.g., `src/auth/handler.go`), not cache paths
- Read references on iteration 2+
```

The mandatory reads list includes all scope files to ensure agents read code even if they skip `navigation.md`.

### Step 2: Spawn Agents in Parallel

Dispatch each agent with the minimal prompt from Step 1. Agents run in **parallel** within each iteration. Each agent's first action is to Read `navigation.md`, then Read code files from the cache.
```

- [ ] **Step 2: Replace Steps 3-5 with cache-based between-iteration flow**

Replace "Step 3: Collect Initial Output", "Step 4: Validate Output", and "Step 5: Self-Refinement Re-prompt" (lines 36-93) with:

```markdown
### Step 3: Collect and Cache Output

Gather raw output from each agent.

### Step 4: Validate, Sanitize, and Cache Findings

Run `manage-cache.sh populate-findings` on each agent's output:

```bash
CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh populate-findings <agent_name> <role_prefix> <output_file> --scope <scope_file>
```

This single call replaces the separate `validate-output.sh` invocation. It:
1. Validates output format and scope compliance
2. Applies sanitized document template (field isolation + provenance markers)
3. Splits into individual finding files
4. Generates summary table

**If validation fails:** Same as before — spawn a **fresh agent** with the validation error appended to the prompt. Up to **2 validation attempts** per agent per iteration.

**If the agent reports zero findings:** The output must contain the `NO_FINDINGS_REPORTED` marker. An empty response without this marker is a validation failure.

### Step 5: Self-Refinement Re-prompt

Re-prompt each agent with:

> "Review your prior findings at `{CACHE_DIR}/findings/<agent>/sanitized.md`. What did you miss? What's a false positive? Refine."

The agent reads its own prior findings from the cache. The orchestrator does NOT feed prior output back into the prompt.
```

Keep the Verification Gate and Reference Cross-Check subsections under Step 5, but update the reference cross-check to point agents to cache:

Add after "Reference Cross-Check (Iteration 2+)" instruction block:

```markdown
> Read reference modules from `{CACHE_DIR}/references/` for cross-checking.
```

- [ ] **Step 3: Update Step 6 (convergence) and Step 7 (budget)**

In Step 6 (Iterate with Convergence Detection), add after the convergence check:

```markdown
After convergence check, update navigation for the next iteration:

```bash
CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh generate-navigation <iteration+1> 1
```
```

Step 7 (Budget Check) is unchanged — `track-budget.sh` calls remain the same.

- [ ] **Step 4: Update Step 8**

Replace "Step 8: Collect Final Findings" with:

```markdown
### Step 8: Collect Final Findings

After all iterations complete, the final validated findings for each agent are in the cache at `{CACHE_DIR}/findings/<agent>/sanitized.md`. These are the input to Phase 2 (Challenge Round).
```

- [ ] **Step 5: Update Parallel Execution Model diagram**

Replace the ASCII diagram to reflect cache-based flow:

```markdown
## Parallel Execution Model

```
Iteration 1:
  Agent A ──┐                              ┌── populate-findings A
  Agent B ──┼── parallel (Read from cache) ─┼── populate-findings B ──> Collect
  Agent C ──┘                              └── populate-findings C

Iteration 2:
  Agent A (reads own findings from cache) ──┐
  Agent B (reads own findings from cache) ──┼── parallel ──> populate-findings ──> Convergence check
  Agent C (reads own findings from cache) ──┘

Iteration 3 (only if not converged):
  Agent A (reads own findings from cache) ──┐
  Agent B (reads own findings from cache) ──┼── parallel ──> populate-findings ──> Collect final
  Agent C (reads own findings from cache) ──┘
```
```

- [ ] **Step 6: Commit**

```bash
git add adversarial-review/skills/adversarial-review/phases/self-refinement.md
git commit -m "feat: replace eager loading with cache-based dispatch in self-refinement.md

Agents receive minimal prompts (~2,825 tokens) and Read code from
the local context cache. populate-findings replaces validate-output.sh.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Update challenge-round.md — Selective reading

**Files:**
- Modify: `adversarial-review/skills/adversarial-review/phases/challenge-round.md`

- [ ] **Step 1: Replace Steps 1-4 with cache-based challenge dispatch**

Replace "Step 1: Pre-Debate Deduplication", "Step 2: Assemble Sanitized Document", "Step 3: Context Cap Enforcement", and "Step 4: Broadcast and Collect Responses" (lines 16-58) with:

```markdown
### Step 1: Pre-Debate Deduplication

Run `scripts/deduplicate.sh` on all Phase 1 findings combined (unchanged):

```bash
scripts/deduplicate.sh <all_phase1_findings>
```

### Step 2: Build Cross-Agent Summary

```bash
CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh build-summary
```

Merges all agents' `summary.md` files into `findings/cross-agent-summary.md`.

### Step 3: Generate Phase 2 Navigation

```bash
CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh generate-navigation <iteration> 2
```

Updates `navigation.md` for Phase 2. On subsequent challenge iterations, pass resolved finding IDs:

```bash
CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh generate-navigation <iteration> 2 --resolved-ids <resolved_file>
```

### Step 3.5: Generate Finding IDs File

Extract the ID column from `cross-agent-summary.md` into a file (one ID per line) for challenge validation:

```bash
FINDING_IDS_FILE=$(mktemp "${TMPDIR:-/tmp}/finding-ids.XXXXXX")
awk -F'|' 'NR>2 && NF>2 {gsub(/^[ \t]+|[ \t]+$/, "", $2); if ($2 != "") print $2}' \
    "$CACHE_DIR/findings/cross-agent-summary.md" > "$FINDING_IDS_FILE"
# Clean up after use (or at end of Phase 2 iteration):
# rm -f "$FINDING_IDS_FILE"
```

### Step 4: Broadcast via Cache and Collect Responses

Send each agent a minimal prompt (~2,825 tokens) with Phase 2 cache navigation:

```
## Cache Access — Phase 2

Your review materials are at: {CACHE_DIR}

Read `{CACHE_DIR}/navigation.md` FIRST.

1. Read `findings/cross-agent-summary.md` — overview of all findings
2. Read full finding files ONLY for findings you intend to challenge or that fall in your domain
3. You MUST Read the full finding before issuing a Challenge — you cannot challenge based on the summary alone
4. Use `templates/challenge-response-template.md` for your response format
```

**Two-tier finding access:**

- **Tier 1:** Agent reads `findings/cross-agent-summary.md` (~200 tokens) — ID, Severity, Category, File:Line, One-liner.
- **Tier 2:** Agent reads individual finding files (`findings/<agent>/<ID>.md`) only for findings they challenge or that fall in their domain.
```

- [ ] **Step 2: Update Step 5 (Validate Responses)**

Replace "Step 5: Validate Responses" with:

```markdown
### Step 5: Validate Responses

Two distinct validation paths:

1. **Challenge responses:** Run `scripts/validate-output.sh` with challenge mode:
   ```bash
   scripts/validate-output.sh <response_file> <role_prefix> --mode challenge --finding-ids <ids_file>
   ```
2. **New findings raised during challenge:** Run through `manage-cache.sh populate-findings`:
   ```bash
   CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh populate-findings <agent> <role_prefix> <new_findings_file> --scope <scope_file>
   ```

Failed validations: spawn fresh agent with error, up to 2 attempts (same as Phase 1).
```

- [ ] **Step 3: Update Step 6 (Drop Resolved Findings)**

Replace the current Step 6 to reference cache:

```markdown
### Step 6: Drop Resolved Findings

After each iteration, identify **RESOLVED** findings (all specialists chose **Agree**, no challenges).

Add resolved finding IDs to the resolved file (one per line). Resolved findings remain in the cache for audit but are omitted from `navigation.md` via `--resolved-ids` on the next `generate-navigation` call.

Resolved findings proceed directly to the report as consensus findings.
```

- [ ] **Step 4: Update iteration flow descriptions**

In the "Iteration Flow" section (Iteration 1, 2, 3 descriptions), replace references to "sanitized document" with cache-based flow:

- "All agents receive the full sanitized document" → "All agents read `findings/cross-agent-summary.md` from cache, then selectively read individual findings"
- "Agents see updated document" → "Agents read updated `navigation.md` and selectively read findings"

- [ ] **Step 5: Commit**

```bash
git add adversarial-review/skills/adversarial-review/phases/challenge-round.md
git commit -m "feat: replace sanitized doc injection with selective cache reading in challenge-round.md

Agents read cross-agent-summary.md first, then selectively read
full finding files only for findings they challenge or in their domain.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 10: Run full test suite and lint verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `bash adversarial-review/skills/adversarial-review/tests/run-all-tests.sh`
Expected: All tests pass, 0 failures.

- [ ] **Step 2: Run ShellCheck**

Run: `make lint`
Expected: "ShellCheck passed."

- [ ] **Step 3: Run manage-cache tests in isolation**

Run: `bash adversarial-review/skills/adversarial-review/tests/test-manage-cache.sh`
Expected: All tests pass.

- [ ] **Step 4: Verify no temp files leaked**

Run: `ls ${TMPDIR:-/tmp}/adversarial-review-cache-* 2>/dev/null | wc -l`
Expected: 0
