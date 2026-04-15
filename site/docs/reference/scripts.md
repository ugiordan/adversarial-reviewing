# Scripts

All scripts live in `skills/adversarial-review/scripts/`. They provide programmatic validation that does not depend on LLM judgment.

## Bash scripts

### validate-output.sh

Validates finding structure and detects injection attempts.

**Usage**: Called automatically after each specialist produces output.

**What it checks**:

- All required fields present (Finding ID, Specialist, Severity, etc.)
- Finding ID prefix matches specialist tag
- Severity and confidence values are valid
- Evidence length exceeds minimum threshold
- No injection patterns in output (embedded instructions, role-play attempts)
- Source Trust field present for security findings (code profile)

### validate-triage-output.sh

Validates triage finding format.

**What it checks**:

- Verdict field present and valid (Fix/No-Fix/Investigate)
- Confidence and severity fields present
- Analysis field has sufficient content

### detect-convergence.sh

Checks if a specialist's finding set has stabilized between iterations.

**Usage**: `bash detect-convergence.sh [--triage]`

**Logic**: Compares finding IDs, severities, and key evidence between iterations. If the delta is below a threshold, the specialist has converged and stops iterating.

### deduplicate.sh / deduplicate.py

Removes duplicate findings across specialists. The logic lives in `deduplicate.py` (standalone Python); `deduplicate.sh` is a thin wrapper for backward compatibility.

**Logic**: Compares finding titles, files, and line ranges. Findings with >80% overlap are merged, keeping the higher severity and combining evidence. The `--cross-specialist` flag marks overlapping findings from different specialists as co-located instead of merging them.

### generate-delimiters.sh

Produces unique delimiters for code isolation blocks. Each specialist receives code wrapped in unique delimiters to prevent cross-agent output leakage.

### build-impact-graph.sh / build_impact_graph.py

Builds a change-impact graph from git diff. The logic lives in `build_impact_graph.py` (standalone Python with argparse); `build-impact-graph.sh` is a thin wrapper for backward compatibility.

**Usage**: `python3 build_impact_graph.py --diff-file <patch> --search-dir <dir> [--max-symbols N] [--max-callers N]`

**Output**: For each changed symbol, lists callers and callees found via grep. Used by `--diff` mode.

### parse-comments.sh / parse_comments.py

Normalizes external review comments into a structured format. The logic lives in `parse_comments.py` (standalone Python); `parse-comments.sh` is a thin wrapper for backward compatibility.

**Input**: PR comments (via GitHub MCP), JSON files, or freeform text. Source types: `github-pr`, `structured`, `freeform`.

**Output**: JSON lines (one comment per line) with id, file, line, author, author_role, comment, and category fields. Includes injection pattern scanning and near-duplicate removal.

### track-budget.sh

Token budget initialization, tracking, and estimation.

**Usage**: Called at review start (init) and after each phase (track).

**Behavior**: Estimates token consumption per agent and phase. Triggers early stop when budget is exhausted. Enforces per-agent cap (150% of fair share).

### discover-references.sh / discover_references.py

Module discovery across three layers (built-in, user, project). The logic lives in `discover_references.py` (standalone Python with argparse); `discover-references.sh` is a thin wrapper for backward compatibility.

**What it does**:

- Scans all three module directories
- Parses YAML frontmatter (name, version, specialist, source_url)
- Filters by active specialist
- Deduplicates (project > user > built-in)
- Checks staleness (modified date)
- Estimates token count
- Finding-aware truncation: `--finding-categories` prioritizes modules matching actual finding categories when budget truncation is needed

### update-references.sh

Fetches remote modules by `source_url` and interactively applies updates.

### manage-cache.sh / manage_cache.py

Cache lifecycle management. The logic lives in `manage_cache.py` (standalone Python with argparse); `manage-cache.sh` is a thin wrapper for backward compatibility.

**Subcommands**: `init`, `populate`, `validate`, `cleanup`, `navigation`

**Security**: Validates all cache paths (no symlinks, no path traversal). Second PID check before `rm -rf` during cleanup.

### profile-config.sh

Reads profile configuration from `config.yml`.

**Output**: Agent list, template paths, settings for the active profile.

### fetch-context.sh

Generic context fetcher for `--context` flag.

**Input**: Label and source (git URL, local dir, file).

**Output**: Fetched content in the cache directory, ready for injection.

### _injection-check.sh

Shared injection detection logic, sourced by both `validate-output.sh` and `validate-triage-output.sh`.

**Patterns detected**: Embedded system prompts, role reassignment attempts, instruction overrides, delimiter manipulation.

## Python utilities

### extract-threat-surface.py

Deterministic keyword-based threat surface extraction for strategy documents. Identifies security-relevant terms and concepts without LLM involvement.

### nfr-scan.py

Non-functional requirements checklist scanner with a severity decision tree. Checks strategy documents against a standard NFR checklist and assigns severity based on gap type.

### findings-to-json.py

Converts structured finding text output to JSON for downstream processing.

### generate-visuals.py

Generates review visualization charts (severity distribution, funnel, convergence, budget).

### fingerprint_findings.py

Cross-run finding persistence via content-based fingerprinting.

**Subcommands**:

- `fingerprint <findings_json>`: Compute stable SHA-256 fingerprints for findings based on specialist prefix, file, line bucket (nearest 5), title, and category. Tolerates small line shifts between runs.
- `compare <current> <previous>`: Classify findings as new, recurring, resolved, or regressed. Outputs JSON summary.
- `history append <findings_json>`: Append fingerprinted findings to `.adversarial-review/findings-history.jsonl`.
- `history query <fingerprint>`: Look up a finding's history (first seen, last seen, run count).
- `history summary`: Stats on unique findings, active count, resolved count, recurrence rate.

**Activation**: `--persist` flag.

### normalize_findings.py

Output stability through finding normalization and cross-run comparison.

**Subcommands**:

- `normalize <findings_file>`: Sort findings canonically (specialist, file, line), standardize formatting (severity/confidence casing, line range format, path normalization).
- `diff <file_a> <file_b>`: Compare normalized finding sets and compute stability metrics (overall stability score, per-field stability for severity/confidence/evidence/title).
- `canonical-order <findings_json>`: Output findings JSON in deterministic order.

**Activation**: `--normalize` flag.

### prompt_version.py

Prompt versioning system for tracking which agent prompt version produced which findings.

**Subcommands**:

- `compute <file_or_dir>`: Compute content-based SHA-256 hashes for agent prompt files (excluding frontmatter).
- `verify <prompt_file>`: Check if frontmatter content_hash matches actual content.
- `stamp <prompt_file>`: Add or update version frontmatter (version, content_hash, last_modified).
- `manifest <dir>`: Generate version manifest for all agent prompts in a profile directory.
