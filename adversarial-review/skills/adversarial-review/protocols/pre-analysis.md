# Deterministic Pre-Analysis (Strat Profile Only)

When `--profile strat` is active, run two deterministic analysis layers before dispatching specialist agents. These layers provide structured context that improves specialist precision and enables confidence scoring.

## Layer 1: Threat Surface Extraction

Extract a keyword-based threat surface inventory from each strategy document. No LLM required.

```bash
python3 scripts/extract-threat-surface.py <strat-file>
```

**Output (stdout):** JSON with:
- `tier`: review depth classification (`skip` / `light` / `standard` / `deep`)
- `keyword_categories`: matched keywords by category (auth, crypto, network, data, multi_tenant, supply_chain, compliance, agentic)
- `surface_hints`: extracted surface items (endpoints, data_stores, credentials, external_deps, trust_boundaries, crd_changes, agent_surfaces)
- `sections`: markdown section headers for citation mapping
- `acceptance_criteria`: extracted numbered ACs

**Tier classification logic:**
- `deep`: auth, crypto, multi_tenant, or agentic keywords present
- `standard`: network, data, supply_chain, or compliance keywords present
- `light`: keywords present but only in non-deep categories
- `skip`: no security-relevant keywords found

Save the output to `{CACHE_DIR}/threat-surface-<strat-id>.json`. Pass the tier to specialist agents for review depth calibration.

## Layer 2: NFR Checklist Scan

Run the recurring NFR checklist against each strategy document using a lightweight LLM call (haiku-tier).

```bash
# Generate scan prompt
python3 scripts/nfr-scan.py --prompt <strat-file> [--surface <threat-surface.json>]

# Parse scan output into structured JSON
python3 scripts/nfr-scan.py --parse <scan-output-file>
```

The NFR checklist contains 23 items across 6 categories (Authentication & Authorization, Testability, Security, Feasibility, Compliance & Governance, Cross-Cutting). Each item has a deterministic severity decision tree: the answer (YES/NO/PARTIAL/N/A) combined with context conditions produces a severity level without LLM judgment.

**Procedure:**
1. Generate the scan prompt with `--prompt`, optionally passing the Layer 1 threat surface for N/A decisions
2. Dispatch a single lightweight agent with the generated prompt
3. Parse the agent output with `--parse` to get structured JSON with severity assignments
4. Save to `{CACHE_DIR}/nfr-scan-<strat-id>.json`

NFR scan results feed into:
- **Specialist context:** agents see which NFR items scored NO/PARTIAL to focus their analysis
- **Confidence scoring:** findings aligned with NFR gaps receive a confidence boost (see `phases/resolution.md` Confidence Scoring)
- **Requirements output:** NFR gaps are listed separately in the requirements template

## Layer 3: Specialist Analysis

Phases 1-3 (self-refinement, challenge, resolution) form Layer 3. Specialists receive the Layer 1 and Layer 2 outputs as structured context alongside the strategy documents.

## Finding Normalization (when `--normalize`)

After Phase 4 (Report), normalize findings for stability:

```bash
python3 scripts/normalize_findings.py normalize <findings_file>
```

This sorts findings canonically (specialist prefix, file path, line number), standardizes formatting (severity/confidence casing, line range format, file path normalization), and collapses whitespace. The normalized output replaces the raw findings in the report.

## Finding Persistence (when `--persist`)

After Phase 4 (Report), run cross-run finding persistence:

```bash
# Fingerprint current findings
python3 scripts/fingerprint_findings.py fingerprint <findings_json>

# Compare against previous run (if history exists)
python3 scripts/fingerprint_findings.py compare <current_json> <previous_json>

# Append to history (idempotency: check protocols/idempotency.md Finding History before appending)
python3 scripts/fingerprint_findings.py history append <findings_json>
```

History is stored at `.adversarial-review/findings-history.jsonl`. Each entry records the fingerprint, finding ID, severity, title, timestamp, and commit SHA. The report's Section 15 (Finding Persistence) is populated from the comparison output.

## Prompt Version Tracking

Before Phase 1, compute prompt versions for all active specialists:

```bash
python3 scripts/prompt_version.py manifest <agents_dir>
```

The manifest is stored in the cache and included in the report metadata block (`prompt_versions` field). This enables tracking which prompt version produced which findings across runs.

## Structured Output

After Phase 4 (Report), generate machine-readable JSON output:

```bash
python3 scripts/findings-to-json.py <findings-file> --profile strat [--metadata '{"strat_id": "..."}']
```

This produces enriched JSON with severity/confidence numeric mappings, specialist prefix extraction, evidence quality signals, and summary statistics. The JSON output is written alongside the report when `--save` is active.
