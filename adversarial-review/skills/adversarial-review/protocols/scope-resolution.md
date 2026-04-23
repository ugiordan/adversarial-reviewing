# Scope Resolution

Determine what code/documents to review. This step is MANDATORY and must complete before any agents are spawned.

## Priority Chain

Resolve scope using the first matching strategy:

1. **User specifies files/dirs** — use exactly those
2. **Active conversation context** — if the most recent assistant turn that produced or modified files is within the last 3 turns, review what was built/discussed
3. **Git diff (staged + unstaged)** — review current changes
4. **Nothing found** — ask the user explicitly

## Sensitive File Blocklist

The following patterns are excluded by default:

```
.env, *.key, *.pem, *secret*, *credential*, .git/, *password*, *.pfx, *.p12
```

If any files matching these patterns appear in scope, they require **explicit separate confirmation** from the user before inclusion. Do not bundle this confirmation with the general scope confirmation.

## Scope File Generation

Write the list of in-scope files (one repo-relative path per line) to a temporary file. Pass this file to `validate-output.sh --scope <file>` during all subsequent validation calls. In `--diff` mode, only changed files are in scope — impact graph files are context-only and do not appear in the scope file.

## Scope Confirmation (MANDATORY)

Generate the scope confirmation display using the formatting script:

```bash
python3 scripts/format-scope.py <scope_file> \
  --source-dir <repo_root> \
  --specialists "<comma_separated_prefixes>" \
  --budget-limit <budget> \
  --budget-estimate '<track-budget.sh estimate JSON output>' \
  [--sensitive "<excluded_files>"]
```

Display the script output to the user verbatim. **Wait for explicit user approval.** Do not proceed without it.

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

After scope resolution and before dispatching Phase 1, run:

```bash
scripts/track-budget.sh estimate <num_agents> <estimated_code_tokens> <configured_iterations>
```

Capture the `estimated_tokens` value from the JSON output. Compare against the configured budget:

- If `estimated_tokens > budget * 0.9`: warn the user with the estimate and budget values. Ask whether to proceed.
- If `estimated_tokens > budget * 1.5`: recommend `--quick` or a narrower scope.
- Users who want to proceed past the gate should set a higher `--budget` value. There is no bypass flag.

See `protocols/guardrails.md` for the `PRE_FLIGHT_WARN_THRESHOLD` and `PRE_FLIGHT_RECOMMEND_THRESHOLD` constants.
