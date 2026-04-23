# Cache Initialization

After scope confirmation and pre-flight budget check, initialize the local context cache before dispatching any agents.

## Cache Initialization Procedure

1. **Generate session hex:** Run `openssl rand -hex 16`. This identifies the cache session (separate from delimiter hex).
2. **Initialize cache directory:**
   ```bash
   SOURCE_ROOT=<absolute_path_to_source> ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh init <session_hex>
   ```
   `SOURCE_ROOT` is the absolute path to the directory containing the code under review. This is stored in the manifest and included in agent prompts so agents know where to search when verifying findings. If omitted, defaults to `$(pwd)`.
   Capture `CACHE_DIR` from the JSON output (`{"cache_dir": "<path>", "session_hex": "<hex>"}`).

**Pipeline mode (strat/rfe profile without `--review-only`):** After cache init, create the strategy artifacts directory:
```bash
mkdir -p "$CACHE_DIR/strategy"
```
This directory stores all pipeline intermediates: `strategy-draft.md`, `quick-review-findings.json`, `refine-*.md`, `mediator-log.md`, `strategy-refined.md`.

3. **Generate delimiter hex:** Run `${CLAUDE_SKILL_DIR}/scripts/generate-delimiters.sh` to produce a session-wide `REVIEW_TARGET` delimiter hex. Collision-check against all scope files.
4. **Populate code:**
   ```bash
   CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-code <scope_file> <delimiter_hex>
   ```
5. **Populate templates:**
   ```bash
   REVIEW_PROFILE=<profile> CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-templates
   ```
6. **Populate references:**
   ```bash
   REVIEW_PROFILE=<profile> CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-references
   ```

   `REVIEW_PROFILE` selects the profile directory for templates and references (`code`, `strat`, or `rfe`). Defaults to `code` if not set.
7. **Populate context (if `--context` flags present):**
   For each `--context label=source` flag:
   ```bash
   CONTEXT_LABEL=<label> CONTEXT_SOURCE=<source> CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-context
   ```
   Context files appear in the navigation under `## Context: <label>` headings. Agents read them like any other cached file. The label tells agents what the context represents (e.g., `architecture` = component boundaries and APIs, `compliance` = regulatory requirements, `threat-model` = known attack surfaces).
8. **Populate constraints (if `--constraints` flag present):**
   ```bash
   CONSTRAINTS_SOURCE=<path> CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh populate-constraints
   ```
   Constraints are loaded from a pack directory (containing `constraints.yaml` + `.md` reference files) or a direct YAML file. Constraints are filtered by the active `REVIEW_PROFILE`: constraints with a `profile` field that doesn't match the active profile are dropped. The navigation includes a `## Constraints` section listing all active constraints with their severity floors and a clear instruction that agents cannot downgrade below the constraint severity.
9. **Generate navigation:**
   ```bash
   CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh generate-navigation 1 1
   ```
10. **Set cleanup trap** (via Bash tool):
    ```bash
    trap "CACHE_DIR='$CACHE_DIR' '$SCRIPT_DIR/manage-cache.sh' cleanup" EXIT HUP INT TERM
    ```
    **Skip this step if `--keep-cache` is specified.** Note: in agent-tool execution models (e.g., Claude Code Bash tool), the trap may not persist across invocations. The `cleanup_stale` function in `manage-cache.sh` provides a reliability backstop.
11. **Export `CACHE_DIR`** — all subsequent steps use this path.

**Session-wide delimiters:** In cache mode, a single `REVIEW_TARGET` delimiter hex is shared across all agents (see `protocols/input-isolation.md` Session-Wide Delimiter Relaxation). `FIELD_DATA` markers in sanitized findings retain per-field unique hex values.

**Failure:** If any step 2-9 fails, abort the review with error. See the Cache Errors table in SKILL.md Error Handling.

## `--reuse-cache <hex>` Override

When `--reuse-cache` is specified, replace steps 2-8 above with:

1. Validate hex: must match `^[a-f0-9]{32}$`.
2. Scan `$TMPDIR` for directories matching `adversarial-review-cache-<hex>-*`.
3. Run `${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh validate-cache <path>`. If invalid, abort with mismatch details.
4. Set `CACHE_DIR` to the resolved path. Skip all populate steps.
5. Clear findings: `rm -rf "$CACHE_DIR/findings/"*` then `mkdir -p "$CACHE_DIR/findings"`.
6. Regenerate navigation: `${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh generate-navigation 1 1`.

## `--delta` Auto-Discovery

When `--delta` is specified, check for `.adversarial-review/last-cache.json` in the repo root before cache initialization:

- **If found:** Display the session hex and commit SHA. Ask user to confirm reuse.
- **If confirmed:** Follow the `--reuse-cache` flow above with the discovered hex.
- **If declined or not found:** Proceed with normal cache initialization.

## `--keep-cache` Post-Review

After Phase 4 (Report) completes:

1. Write `.adversarial-review/last-cache.json`:
   ```json
   {"session_hex": "<hex>", "commit_sha": "<HEAD>"}
   ```
2. Print: "Cache preserved. Reuse with `--reuse-cache <hex>`"
