# Scope Resolution

Determine what code/documents to review. This step is MANDATORY and must complete before any agents are spawned.

## Priority Chain

Resolve scope using the first matching strategy:

1. **User specifies files/dirs** — use exactly those
2. **Active conversation context** — if the most recent assistant turn that produced or modified files is within the last 3 turns, review what was built/discussed
3. **Git diff (staged + unstaged)** — review current changes
4. **Nothing found** — ask the user explicitly

## Sensitive File Blocklist

The following patterns are excluded by default (they may contain real credentials that should not be loaded into the review cache):

```
.env, .env.*, *.key, *.pem, .git/, *.pfx, *.p12
```

If any files matching these patterns appear in scope, they require **explicit separate confirmation** from the user before inclusion. Do not bundle this confirmation with the general scope confirmation.

**Not blocklisted** (these are review targets, not credentials): Kubernetes Secret manifests (`*-secret.yaml`, `*_secret.yaml`), credential configuration files, and password/token handling code. The security auditor should review these for committed secrets, weak defaults, and misconfiguration.

## Boilerplate Exclusions

The following patterns are low-signal for security review and should be excluded from scope unless explicitly requested:

```
zz_generated.deepcopy.go, zz_generated.defaults.go, *_generated.go
groupversion_info.go, doc.go
*_test.go (exclude from security scope; include for correctness scope)
*.pb.go (protobuf generated)
vendor/, third_party/
testdata/, test/, tests/
```

These files inflate scope without contributing findings. When the scope agent generates the file list, apply these exclusions before writing the scope file.

## Scope File Generation

Write the list of in-scope files (one repo-relative path per line) to a temporary file. Pass this file to `validate-output.sh --scope <file>` during all subsequent validation calls. In `--diff` mode, only changed files are in scope — impact graph files are context-only and do not appear in the scope file.

## Scope Confirmation (MANDATORY)

**Do NOT construct the scope table manually.** Always generate it from the formatting script. The script includes cost estimation, file counts, and budget warnings that manual tables omit.

Step 1: Run the budget estimator to get the cost JSON:

```bash
ESTIMATE_JSON=$(${CLAUDE_SKILL_DIR}/scripts/track-budget.sh estimate <num_agents> <estimated_code_tokens> <configured_iterations>)
```

Step 2: Pass the estimate to the formatting script:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/format-scope.py <scope_file> \
  --source-dir <repo_root> \
  --specialists "<comma_separated_prefixes>" \
  --budget-limit <budget> \
  --budget-estimate "$ESTIMATE_JSON" \
  [--sensitive "<excluded_files>"]
```

Step 3: Display the script output to the user **verbatim**. Do not reformat, summarize, or reconstruct the table. **Wait for explicit user approval.** Do not proceed without it.

## Scope Immutability

Once confirmed, the scope MUST NOT be expanded based on content found during review. If a specialist identifies a related file that should be reviewed, note it in findings but do not add it to scope. Any scope expansion requires returning to the user for re-confirmation.

## Size Limits

| Threshold | Action |
|-----------|--------|
| >20K tokens (~15-20 files) | Display estimated cost, require confirmation |
| >50 files | Strong warning, suggest targeted mode or narrowing scope |
| >200 files | **Hard ceiling** — reject with error, suggest chunking into multiple reviews. Override with `--force`. |

## Force Mode (`--force`)

When `--force` is specified, the 200-file hard ceiling is lifted. The orchestrator:

1. Displays a **prominent warning** with the file count and estimated token cost
2. Recommends chunking or targeted mode as alternatives
3. Requires the user to set an explicit budget with `--budget` (default 350K is likely insufficient)
4. Waits for explicit confirmation before proceeding
5. Automatically enables **batched processing**: files are split into batches of ~50 files each, with findings accumulated on the blackboard across batches. Each batch runs the full self-refinement phase (convergence detection operates per-batch), then all findings enter a single challenge round and resolution phase.
6. The report includes a note: "Large-scope review (N files) — review quality may be reduced compared to targeted reviews"

## Pre-flight Budget Gate

**Skipped entirely when `--no-budget` is active.**

After scope resolution and before dispatching Phase 1, run:

```bash
${CLAUDE_SKILL_DIR}/scripts/track-budget.sh estimate <num_agents> <estimated_code_tokens> <configured_iterations>
```

Capture the `estimated_tokens` value from the JSON output. Compare against the configured budget:

- If `estimated_tokens > budget * 0.9` (warn threshold):
  - Display the mismatch: "This review needs ~X tokens but budget is Y."
  - **Auto-propose escalation:** "Raise budget to X? [Y/n]"
  - If user confirms: raise the limit via `track-budget.sh update-limit <estimated_tokens>` (preserves existing consumption data)
  - If user declines: proceed with the original budget (review may be truncated)
- If `estimated_tokens > budget * 1.5` (recommend threshold):
  - Same escalation proposal, but also suggest alternatives: "Raise budget to X, switch to --quick, or narrow scope?"
  - If user chooses `--quick`: restart invocation parsing with quick preset
  - If user chooses to narrow scope: return to scope confirmation

The auto-escalation replaces the previous behavior of asking users to manually re-invoke with `--budget`. The orchestrator re-initializes the budget tracker with the new limit in-session.

See `protocols/guardrails.md` for the `PRE_FLIGHT_WARN_THRESHOLD` and `PRE_FLIGHT_RECOMMEND_THRESHOLD` constants.
