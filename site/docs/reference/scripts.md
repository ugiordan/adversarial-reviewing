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

### deduplicate.sh

Removes duplicate findings across specialists.

**Logic**: Compares finding titles, files, and line ranges. Findings with >80% overlap are merged, keeping the higher severity and combining evidence.

### generate-delimiters.sh

Produces unique delimiters for code isolation blocks. Each specialist receives code wrapped in unique delimiters to prevent cross-agent output leakage.

### build-impact-graph.sh

Builds a change-impact graph from git diff.

**Usage**: `bash build-impact-graph.sh [--range <range>]`

**Output**: For each changed symbol, lists callers and callees found via grep. Used by `--diff` mode.

### parse-comments.sh

Normalizes external review comments into a structured format.

**Input**: PR comments (via GitHub MCP), JSON files, or stdin.

**Output**: Normalized JSON array with id, source, file, line, and body fields.

### track-budget.sh

Token budget initialization, tracking, and estimation.

**Usage**: Called at review start (init) and after each phase (track).

**Behavior**: Estimates token consumption per agent and phase. Triggers early stop when budget is exhausted. Enforces per-agent cap (150% of fair share).

### discover-references.sh

Module discovery across three layers (built-in, user, project).

**What it does**:

- Scans all three module directories
- Parses YAML frontmatter (name, version, specialist, source_url)
- Filters by active specialist
- Deduplicates (project > user > built-in)
- Checks staleness (modified date)
- Estimates token count

### update-references.sh

Fetches remote modules by `source_url` and interactively applies updates.

### manage-cache.sh

Cache lifecycle management.

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
