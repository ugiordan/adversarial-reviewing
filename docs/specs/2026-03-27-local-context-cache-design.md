# Local Context Cache Design

**Date:** 2026-03-27
**Status:** Approved (3 architecture review rounds, converged)
**Repo:** `ugiordan/adversarial-review`

## Summary

Reduce adversarial-review token consumption by ~20-48% (depending on challenge rate) by shifting from eager loading (injecting all context into agent prompts) to lazy loading (agents Read from a temporary disk cache on demand). The cache is orchestrator-populated, agent-readonly, and preserves all existing security invariants (delimiter isolation, mediated communication, injection resistance).

## Problem

A default 5-agent, 3-iteration review consumes ~532K tokens. Code is sent ~30 times (5 agents x 3 iterations x 2 phases). The budget model undercounts by ~2x because it doesn't account for prompt overhead. Token cost is the primary adoption blocker.

## Architecture Decision

**Local disk cache with Read tool access.** No external APIs, no Anthropic prompt caching, no shared memory. Agents read files from a secured temp directory using Claude Code's built-in Read tool.

### Why Not Anthropic Prompt Caching

- Costs money (cache write/read fees)
- Each subagent has independent cache context — no sharing across agents
- Requires API-level integration outside AR's control

### Why Not Concatenated Context Files

- Loses the "read only what you challenge" optimization in Phase 2
- Finding summary optimization doesn't work with single-file approach
- Essentially moves bloat from prompt to a file — no selective reading

## Design

### 1. Cache Lifecycle

#### Creation

Orchestrator creates the cache at Phase 0 (before agent dispatch):

```bash
CACHE_HEX=$(openssl rand -hex 16)
CACHE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/adversarial-review-cache-${CACHE_HEX}-XXXXXX")
chmod 700 "$CACHE_DIR"
```

- Uses `$TMPDIR` (macOS: per-user private dir `/var/folders/...`), falls back to `/tmp`
- `mktemp -d` for atomic creation with restrictive permissions (0700)
- Session hex embedded in directory name (enables `--reuse-cache` resolution by scanning `$TMPDIR` for matching hex prefix)
- Cache HEX generated independently from delimiter HEX via `openssl rand -hex 16` (not through `generate-delimiters.sh`)

#### Population (Orchestrator-Only Writes)

| When | What | How |
|------|------|-----|
| Phase 0 | Code files | `manage-cache.sh populate-code` — copies with delimiter wrapping |
| Phase 0 | Templates | `manage-cache.sh populate-templates` — finding + challenge templates |
| Phase 0 | References | `manage-cache.sh populate-references` — enabled reference modules |
| Between Phase 1 iterations | Findings per agent | `manage-cache.sh populate-findings` — validate, sanitize, split |
| Before Phase 2 | Cross-agent summary | `manage-cache.sh build-summary` — merge agent summaries |

#### Directory Structure

```
$TMPDIR/adversarial-review-cache-<SESSION_HEX>-XXXXXX/
├── .lock                          # PID of owning process
├── manifest.json                  # integrity metadata
├── navigation.md                  # agent read instructions (generated per session)
├── code/                          # delimiter-wrapped source files
│   └── src/auth/handler.go        # mirrors repo-relative structure
├── templates/
│   ├── finding-template.md
│   └── challenge-response-template.md
├── references/
│   ├── owasp-top10-2025.md
│   ├── asvs-5-highlights.md
│   └── k8s-security.md
└── findings/
    ├── security-auditor/
    │   ├── sanitized.md           # monolithic validated+sanitized output
    │   ├── SEC-001.md             # individual finding (sanitized)
    │   ├── SEC-002.md
    │   └── summary.md            # table: ID | severity | file:line | one-liner
    ├── performance-analyst/
    │   └── ...
    └── cross-agent-summary.md    # all agents merged summary table
```

#### Cleanup

- **Default:** `trap` on EXIT, SIGHUP, SIGINT, SIGTERM removes cache directory
- **`--keep-cache`:** Skip cleanup, print session hex for later reuse
- **Stale cleanup:** `manage-cache.sh init` removes caches older than 24h where the `.lock` PID is no longer running (`kill -0 $pid` fails). Both conditions must be true — prevents deleting active long-running sessions.

#### Lock File

`.lock` contains the PID of the owning process. Written at creation, checked before stale cleanup. Prevents concurrent sessions from deleting each other's caches.

#### Cache Reuse

- **`--reuse-cache <session_hex>`:** Resolves cache path by scanning `$TMPDIR` for directories matching `adversarial-review-cache-<session_hex>-*`. Validates manifest (SHA-256 per file + commit SHA). Aborts on any mismatch. Skips code/template/reference population. Findings are regenerated.
- **Delta auto-discovery:** `.adversarial-review/last-cache.json` in repo (gitignored) stores commit SHA + session hex only (no local paths). Cache path resolved at runtime. Requires explicit user confirmation before reuse.

#### Manifest Schema

```json
{
  "version": "1.0",
  "created_at": "2026-03-27T14:30:00Z",
  "commit_sha": "a1b2c3d4e5f6...",
  "session_hex": "f0e1d2c3b4a5...",
  "specialists": ["security-auditor", "performance-analyst", "..."],
  "flags": ["--quick", "--strict-scope"],
  "files": [
    {"path": "code/src/auth/handler.go", "sha256": "abc123..."},
    {"path": "templates/finding-template.md", "sha256": "def456..."}
  ]
}
```

Validation on `--reuse-cache`: every file's SHA-256 must match manifest. Commit SHA must match current HEAD. Any mismatch aborts.

#### Trust Boundary

Cache trusts the local user's filesystem. Same-user tampering is out of scope — if your user account is compromised, the cache is the least of your problems. This is documented, not a gap.

### 2. Agent Prompt Transformation

#### Before (Eager Loading)

Agent prompt = role instructions + full code files + templates + references + previous findings = 15K-50K tokens per dispatch.

#### After (Lazy Loading)

Agent prompt = role + inoculation + delimiters + finding template + cache navigation = ~2,825 tokens per dispatch.

**What stays in the prompt (not cached):**

| Content | Why | Tokens |
|---------|-----|--------|
| Agent role definition | Security-critical framing | ~1,500 |
| Inoculation paragraphs (3) | Injection resistance — must surround all agent reasoning | ~500 |
| Delimiter values | Must be in-prompt for input isolation | ~125 |
| Finding template | Format compliance even if navigation.md not read | ~500 |
| Cache navigation instructions | Tells agent where to read | ~200 |
| Iteration number, convergence status | Session state | ~25 |

Total: ~2,825 tokens per agent dispatch (down from 15K-50K).

#### Cache Navigation Instructions (in prompt)

```markdown
## Cache Access

Your review materials are at: {CACHE_PATH}

Read `{CACHE_PATH}/navigation.md` FIRST — it tells you what's available and what to read.

Rules:
- Read code files from `code/` before making claims about them
- In Phase 2: read `findings/cross-agent-summary.md` first, then full finding files only for findings you challenge or that fall in your domain
- You MUST Read the full finding before issuing a Challenge
- Use repo-relative paths in findings (e.g., `src/auth/handler.go`), not cache paths
```

#### Mandatory Read List

The agent prompt includes explicit Read instructions for critical files:

```markdown
## Mandatory Reads
Read these files before producing findings:
- {CACHE_PATH}/code/src/auth/handler.go
- {CACHE_PATH}/code/src/auth/session.go
- {CACHE_PATH}/references/owasp-top10-2025.md (iteration 2+ only)
```

This ensures agents read the most important files even if they skip navigation.md.

#### navigation.md (Generated Per Session)

Generated by the orchestrator at cache creation and updated between iterations. Token estimates use the `char/4` heuristic (consistent with `track-budget.sh`).

**Example content:**

```markdown
# Review Cache Navigation

## Iteration: 1 | Phase: 1 | Budget: ~50K tokens per agent

## Code Files (read before making claims)
| File | Tokens (est.) |
|------|---------------|
| code/src/auth/handler.go | 1,250 |
| code/src/auth/session.go | 800 |
| code/internal/controller/rbac.go | 2,100 |
| code/pkg/utils/crypto.go | 450 |

## Reference Modules (read on iteration 2+)
| Module | Tokens (est.) |
|--------|---------------|
| references/owasp-top10-2025.md | 3,200 |
| references/asvs-5-highlights.md | 2,800 |

## Templates
- templates/finding-template.md (also in your prompt)
- templates/challenge-response-template.md

## Phase-Specific Instructions
- **Phase 1:** Read all code files. Read references on iteration 2+.
  Produce findings using the finding template format.
- **Phase 2:** Read findings/cross-agent-summary.md first.
  Read full finding files only for findings in your domain or that
  you intend to challenge. You MUST read the full finding before
  issuing a Challenge.

## Rules
- Use repo-relative paths in findings (e.g., `src/auth/handler.go`)
- Do NOT use cache paths in your output
```

### 3. Delimiter-Wrapped Code in Cache

Code files in the cache are written WITH delimiter wrapping already applied, using the format defined in `protocols/input-isolation.md` (canonical source for anti-instruction text):

```
===REVIEW_TARGET_<hex>_START===
[anti-instruction text from input-isolation.md]

[actual file content here]

===REVIEW_TARGET_<hex>_END===
```

- Uses session-wide delimiter hex for code file wrapping (same `REVIEW_TARGET` hex across all agents)
- **This is a documented relaxation from per-agent delimiters.** In non-cache mode, SKILL.md specifies per-agent delimiter pairs. In cache mode, a single session-wide hex is used to avoid duplicating every code file per agent. Accepted trade-off: the hex is 128-bit CSPRNG random, collision-checked, and agents don't communicate directly. SKILL.md must be updated to document this behavioral difference when cache mode is active (see Implementation Prerequisites).
- **Field-level isolation markers in cached findings retain per-field unique hex values** as specified in `templates/sanitized-document-template.md`. Only `REVIEW_TARGET` code delimiters are relaxed to session-wide. The `FIELD_DATA` markers used in sanitized findings are generated per-field by the orchestrator at sanitization time.
- `manage-cache.sh populate-code` runs post-hoc collision check: `grep -qF "$hex" "$file"` for each file before wrapping. Abort and regenerate on collision.

### 4. Sanitized Findings in Cache

**Critical invariant:** Agents never see raw findings from other agents. The mediated communication protocol is preserved in the cache.

Pipeline before cache write:
1. Agent produces output
2. Orchestrator runs `validate-output.sh` — format, injection, scope checks
3. Orchestrator applies sanitized document template — field isolation markers (`[FIELD_DATA_<hex>_START/END]`) + provenance markers (`[PROVENANCE::Agent::VERIFIED]`)
4. Sanitized output written to cache as monolithic file (`findings/<agent>/sanitized.md`)
5. Individual finding files split from monolithic (derived, not source of truth)
6. Summary table row generated per finding

`validate-output.sh` validates the monolithic form. `build-summary` uses monolithic files as source of truth. Splits exist only for selective Phase 2 reading.

### 5. Finding Summaries in Phase 2

#### Before

All other agents' full findings injected into each agent's prompt: ~20K tokens per agent for 5 agents with ~10 findings each.

#### After

Two-tier approach:

**Tier 1 — Summary table (agent reads `cross-agent-summary.md`):**

```markdown
| ID       | Severity | Category | File:Line        | One-liner                                  |
|----------|----------|----------|------------------|--------------------------------------------|
| SEC-001  | Critical | SEC      | auth.go:142      | RBAC precedence allows privilege escalation |
| PERF-003 | Minor    | PERF     | handler.go:88    | Unbounded goroutine spawn in hot path       |
| QUAL-007 | Important| QUAL     | utils.go:33-55   | Deep nesting reduces readability            |
```

**Tier 2 — Full details on demand:**

Agents Read individual finding files (`findings/<agent>/<ID>.md`) only for:
- Findings in their domain (e.g., security-auditor reads all SEC-* findings)
- Findings they intend to challenge (MUST read full detail before challenging)

**Quality safeguard:** Rule 4 in navigation instructions: "You MUST Read the full finding before issuing a Challenge — you cannot challenge based on the summary alone."

**Token impact:** ~20K per agent -> ~200 tokens (navigation) + ~2,500-5,000 tokens (selective reads). Savings depend on challenge rate — contentious reviews save less.

### 6. Budget Model Update

#### Formula Changes

All scripts use `${TMPDIR:-/tmp}` — no hardcoded `/tmp` paths.

**Pre-flight estimate (worst-case):**

```
prompt_overhead = prompt_tokens_per_agent * agents * (phase1_iterations + phase2_iterations)
phase1 = agents * ((code_tokens + impact_graph_tokens) * iterations + reference_tokens * (iterations - 1))
phase2 = agents^2 * avg_findings_per_agent * finding_response_size * iterations
phase3_4 = fixed_overhead (~10K)
total = prompt_overhead + phase1 + phase2 + phase3_4
```

- `prompt_overhead` is new — accounts for the minimal prompt (~2,825 tokens) sent to each agent each iteration. The current `track-budget.sh estimate` does not include this term; it must be added (see Implementation Prerequisites).
- Phase 2 formula is quadratic in agents (`agents^2`) because each agent reviews all other agents' findings. `finding_response_size` is ~200 tokens (Agree/Challenge + evidence).
- `impact_graph_tokens` is zero until ast-grep integration lands (see Future Enhancements). The formula includes it for forward-compatibility; implementations should default to 0.

**Post-iteration tracking:** Uses actual output character count (unchanged from current).

**Context cap:** navigation.md limits visible files to stay within the 50K per-iteration context cap. Orchestrator prioritizes by severity (findings) and size (code files). Token estimates per file included in navigation.md.

### 7. Agent Compliance Enforcement

The cache model converts some structural guarantees (content in prompt = agent must see it) into behavioral expectations (agent must Read from cache). Mitigations:

| Risk | Mitigation |
|------|-----------|
| Agent skips navigation.md | Finding template in prompt — format validation catches issues regardless |
| Agent reads too little code | Post-hoc: if output has no file:line refs matching cached code, auto-classify all findings as ASSUMPTION-BASED |
| Agent uses cache paths in findings | validate-output.sh strips known cache path prefix as fallback |
| Agent skips full finding before Challenge | validate-output.sh `--mode challenge` validates evidence references specific finding content |
| Path normalization edge cases | Strip leading `./`, case-insensitive comparison on HFS+ |

### 8. Challenge Response Validation (New)

Add `--mode challenge` flag to `validate-output.sh`. Requires `--finding-ids <file>` parameter containing the list of valid finding IDs (one per line) from the current review.

**Parameters:**
```bash
validate-output.sh --mode challenge --finding-ids <ids_file> [--scope <scope_file>] <input_file>
```

**Validation rules (pseudocode):**
```
1. Parse Action field → must be one of: Agree, Challenge, Abstain (case-insensitive)
2. Parse Finding ID field → must exist in --finding-ids file
3. If Action == Challenge:
   a. Parse Evidence field → must be >= MIN_EVIDENCE_CHARS (100 non-whitespace chars)
   b. Evidence must reference at least one file:line from the original finding
4. Parse optional Severity field → if present, must be Critical|Important|Minor
5. Run _injection-check.sh on all free-text fields (Evidence, rationale)
6. Run scope check if --scope provided
```

**Exit codes:** Same as existing validate-output.sh (0 = valid, 1 = validation failure with JSON error detail on stderr, 2 = usage error).

**Output format:** Same JSON schema as existing validate-output.sh (`{"valid": bool, "errors": [...], "warnings": [...]}`)

### 9. manage-cache.sh Script

New script with subcommands. Follows the same conventions as existing scripts (`track-budget.sh`, `detect-convergence.sh`).

#### Interface Contract

**Exit codes:**
- `0` — Success
- `1` — Validation failure (manifest mismatch, collision detected, stale cache)
- `2` — Usage error (bad arguments, missing required params)

**Output format:** JSON on stdout for machine-readable subcommands (`init`, `validate-cache`). Human-readable on stderr for progress/warnings.

**Environment:** Requires `CACHE_DIR` env var for all subcommands except `init` (which creates and outputs the path). `init` outputs `{"cache_dir": "<path>", "session_hex": "<hex>"}` on stdout.

**Internal dependencies:**
- `populate-findings` calls `validate-output.sh` internally for validation + sanitization. The orchestrator should NOT pre-validate — `populate-findings` owns the full validate-sanitize-split pipeline.
- `populate-code` calls `grep -qF` for collision check (does NOT call `generate-delimiters.sh`)
- `populate-references` calls `discover-references.sh` to determine which modules are enabled

#### Subcommands

| Subcommand | Parameters | Purpose |
|-----------|------------|---------|
| `init <session_hex>` | session_hex (128-bit hex) | Create cache dir via `mktemp -d`, write manifest + `.lock` (PID), clean stale caches (>24h + dead PID). Outputs JSON with cache_dir path. |
| `populate-code <file_list> <delimiter_hex>` | file_list (path to newline-separated file list), delimiter_hex (128-bit hex) | Copy files preserving repo-relative structure, wrap with delimiters per `input-isolation.md`, post-hoc collision check. Updates manifest. |
| `populate-templates` | (none) | Copy finding + challenge response templates from skill's `templates/` dir. Updates manifest. |
| `populate-references` | (none) | Copy enabled reference modules (per `discover-references.sh`). Updates manifest. |
| `populate-findings <agent> <findings_file>` | agent (agent name e.g. "security-auditor"), findings_file (path to raw agent output) | Validate via `validate-output.sh` -> sanitize via sanitized document template -> write monolithic `sanitized.md` + split into `<ID>.md` files + generate `summary.md` row. Updates manifest. |
| `build-summary` | (none) | Merge all agents' `summary.md` into `cross-agent-summary.md`. Updates manifest. |
| `validate-cache <path>` | path (cache dir path) | Verify all files against manifest SHA-256 hashes + commit SHA against current HEAD. Outputs JSON `{"valid": bool, "mismatches": [...]}`. |
| `cleanup` | (none) | Remove cache dir + `.lock`. Idempotent. |

### 10. SKILL.md Orchestration Changes

#### Phase 0 (Expanded)

```
1. Parse flags (existing)
2. Generate session delimiters (existing)
3. Initialize cache: manage-cache.sh init <session_hex>
4. Populate code: manage-cache.sh populate-code <scope_files> <delimiter_hex>
5. Populate templates: manage-cache.sh populate-templates
6. Populate references: manage-cache.sh populate-references
7. Set CACHE_PATH for all subsequent steps
```

#### Phase 1 Dispatch Changes

- Build minimal prompt (~2,825 tokens): role + inoculation + delimiters + finding template + cache navigation + mandatory read list
- Agent's first action: Read navigation.md, then Read code files
- Between iterations:
  1. Collect agent output
  2. `manage-cache.sh populate-findings <agent> <output>` — validates, sanitizes, splits (replaces the separate validate-output.sh call)
  3. Detect convergence (existing — unchanged)
  4. Update navigation.md with iteration-specific instructions

#### Phase 2 Dispatch Changes

- `manage-cache.sh build-summary` before dispatching challengers
- Minimal prompt + "Phase 2: read cross-agent-summary.md first"
- Agents Read full findings selectively

#### Flag Handling

| Flag | Cache Behavior |
|------|---------------|
| `--keep-cache` | Skip cleanup trap, print session hex. Write session hex + commit SHA to `.adversarial-review/last-cache.json`. |
| `--reuse-cache <hex>` | Resolve by hex in $TMPDIR, validate manifest, skip population, regenerate findings |
| `--delta` | Check `.adversarial-review/last-cache.json`, require user confirmation before reuse |
| `--quick` | Same cache, fewer agents populate it |
| `--diff` | Only cache changed files + direct dependents (future: ast-grep computes dependents) |

#### Flag Interaction Matrix

| Combination | Behavior |
|------------|----------|
| `--delta` alone | Looks up `last-cache.json`, prompts user, creates new cache if declined or not found |
| `--reuse-cache <hex>` alone | Resolves specific cache, validates, reuses code/templates/refs, regenerates findings |
| `--delta --reuse-cache` | **Mutually exclusive.** Error: "Use --delta for auto-discovery or --reuse-cache for explicit reuse, not both." |
| `--delta --keep-cache` | Composable. Reuses previous cache if confirmed, keeps the new/reused cache after completion. |
| `--reuse-cache --keep-cache` | Composable. Reuses specified cache and preserves it after completion. |
| `--diff --reuse-cache` | **Mutually exclusive.** Error: "--diff creates a minimal cache from changed files; --reuse-cache expects a complete cache." |
| `--diff --delta` | Composable. Delta discovers previous cache for comparison; diff limits scope to changed files. |

### 11. .gitignore Addition

Add `.adversarial-review/` to prevent local cache metadata from being committed.

## Token Savings Estimate

Savings vary by challenge rate (how many findings agents drill into during Phase 2):

| Scenario | Before | After | Savings |
|----------|--------|-------|---------|
| Low contention (few challenges) | 532K | 277K | ~48% |
| Medium contention | 532K | 350K | ~34% |
| High contention (many challenges) | 532K | 425K | ~20% |

The 48% headline assumes ideal selective reading. Real-world savings will be 20-48% depending on review contentiousness.

## Implementation Prerequisites

These must be fixed during implementation:

1. **`track-budget.sh` line 18:** Replace hardcoded `/tmp` with `${TMPDIR:-/tmp}`
2. **`detect-convergence.sh` line 25:** Replace hardcoded `/tmp` with `${TMPDIR:-/tmp}`
3. **`track-budget.sh` estimate:** Add `prompt_tokens_per_agent * agents * total_iterations` term to match the formula in Section 6
4. **`validate-output.sh`:** Add `--mode challenge` flag for challenge response validation (see Section 8 for full spec)
5. **SKILL.md Phase 1 Agent Dispatch:** Update to document session-wide delimiter hex when cache mode is active (relaxation from per-agent delimiters). Non-cache mode retains per-agent delimiters.
6. **`.gitignore`:** Add `.adversarial-review/` entry

## Future Enhancements

- **ast-grep integration:** Pre-compute call graphs for `--diff` mode impact analysis. Strengthen code-path verification gate with programmatic checks. Populate `impact-graph/` in cache.
- **tree-sitter integration:** Semantic code chunking in cached files instead of raw file dumps.
- **Per-agent delimiter wrapping:** Trade disk space for stronger isolation if threat model changes.
- **Empirical benchmark:** Run same review with eager vs. cache loading, measure actual token consumption to validate estimates.

## Security Considerations

| Property | How Preserved |
|----------|--------------|
| Input isolation (delimiters) | Code cached with delimiter wrapping + anti-instruction text |
| Mediated communication | Findings validated + sanitized before cache write |
| Injection resistance | Inoculation stays in prompt; injection checks on all agent output |
| Agent isolation | Agents Read from cache, never write; orchestrator mediates all cross-agent data |
| Cache confidentiality | `$TMPDIR` (per-user), `mktemp -d` (0700), trap cleanup |
| Cache integrity | SHA-256 manifest, validated on reuse |
| Scope confinement | validate-output.sh --scope unchanged; cache-prefix stripping as fallback |

## Architecture Review History

- **Round 1:** 5 MUST-FIX, 6 SHOULD-FIX — cache permissions, mediated communication, delimiter isolation, reuse-cache integrity, budget formula, agent compliance, stale code, cleanup, path translation, context cap
- **Round 2:** 2 MUST-FIX, 6 SHOULD-FIX — lock file for concurrent sessions, /tmp hardcoding, .gitignore, split finding convention, manifest trust boundary, delimiter collision check, Phase 2 formula, challenge validation
- **Round 3:** Converged. 0 new design issues. 3 implementation prerequisites identified.
