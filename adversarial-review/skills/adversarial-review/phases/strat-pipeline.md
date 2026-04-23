# Document Pipeline: Create, Refine, Review

## Purpose

Orchestrates the full document pipeline when `--profile strat` or `--profile rfe` is invoked without `--review-only`. Produces a refined document through adversarial refinement, then subjects it to full adversarial review. The pipeline logic is shared between strat and rfe profiles; profile-specific behavior (template structure, agent set, section names) is driven by the profile config.

## Prerequisites

- Profile resolved to `strat` or `rfe`
- Input identified: Jira key (regex `^[A-Z][A-Z0-9_]+-\d+$`) or file path
- `--review-only` NOT specified
- Budget initialized
- If `--principles <path>` specified: validated per `protocols/principles.md`
- If `--arch-context <repo@ref>` specified: parsed into repo and ref components

## Procedure

### Step 0: Input Detection and Context Fetch

Determine input type:

```
if input matches ^[A-Z][A-Z0-9_]+-\d+$:
    input_type = "jira"
else if file exists at input path:
    input_type = "file"
else:
    error: "Input is neither a valid Jira key nor an existing file: <input>"
```

**Architecture context fetch (`--arch-context`):**

When `--arch-context <repo@ref>` is specified, fetch architecture context before proceeding:

```bash
SCRIPT_DIR="<skill_base>/scripts"
"$SCRIPT_DIR/fetch-context.sh" --label architecture --source "<repo@ref>" --output "$CACHE_DIR/context/architecture"
```

The `fetch-context.sh` script parses `@ref` automatically: it splits the source into repo and ref, expands `org/repo` shorthand to `https://github.com/org/repo.git`, clones, and checks out the specified ref (tag, branch, or SHA).

Examples:
```bash
# Tag
--arch-context opendatahub-io/architecture-context@v2.15.0

# Branch
--arch-context jctanner/platform-architecture-context-pipeline@main

# Commit SHA
--arch-context opendatahub-io/architecture-context@abc123f

# Default branch (no @ref)
--arch-context opendatahub-io/architecture-context
```

The fetched context files are then available at `$CACHE_DIR/context/architecture/` and injected into refine agents and review specialists via the standard context injection mechanism.

### Step 1: Create

**Template selection:** The template is determined by the active profile:
- `strat`: `profiles/strat/templates/strategy-template.md` (8 sections: TL;DR, Summary, Problem Statement, Goals, Acceptance Criteria, Dependencies, Constraints, Open Questions)
- `rfe`: `profiles/rfe/templates/rfe-template.md` (9 sections: TL;DR, Summary, Problem Statement, Proposed Solution, Requirements, Acceptance Criteria, Dependencies, Migration & Compatibility, Open Questions)

**Jira input:**

```bash
SCRIPT_DIR="<skill_base>/scripts"
TEMPLATE="<skill_base>/profiles/<profile>/templates/<template_file>"
"$SCRIPT_DIR/extract-jira.sh" --key <JIRA_KEY> --template "$TEMPLATE" > "$CACHE_DIR/strategy/strategy-draft.md"
```

If `extract-jira.sh` fails, abort with the error message.

**File input:**

Read the input file. If it already follows the active profile's template structure (has at least 4 of the section headings for the active template), copy it as-is to `$CACHE_DIR/strategy/strategy-draft.md`.

If the file does not follow the template structure, the orchestrator normalizes it: read the content and map it into the template sections. Use the file content as the Problem Statement, extract any bullet lists as potential ACs/Goals, set TL;DR to "(To be generated during refinement.)", and leave other sections as "(To be defined during refinement.)"

Save to `$CACHE_DIR/strategy/strategy-draft.md`.

**Multi-component detection:** After creating the strategy draft, check for multiple components:

- **Jira input:** Extract from the `components` field in the Jira response. If 2+ components are present:
  1. List the detected components to the user
  2. If `--arch-context` is specified, fetch architecture context for each component separately (using the same repo but searching for component-specific context files)
  3. The **orchestrator** (not `extract-jira.sh`) appends a `### Component Boundaries` subsection to the Constraints section of the draft after the script generates it. The subsection names each component and flags cross-component interaction points. `extract-jira.sh` only adds a flat `Components: comp1, comp2` line to constraints.
  4. Refine agents receive per-component context sections labeled: `### Architecture Context: {component_name}`

- **File input:** If the file mentions multiple components (detected by heading patterns like `## Component: X` or explicit component lists), apply the same component boundary flagging.

**Display:** Show the user the document draft and confirm:
> "{Strategy/RFE} draft created from {jira key / file}. Proceeding with quick review and adversarial refinement."

If multiple components were detected:
> "Detected N components: {list}. Per-component architecture context will be loaded where available."

This is informational, not a gate (unless `--confirm` is active, in which case gates are at Step 3b).

### Step 2: Quick Review

Run a lightweight adversarial review on the document draft using the active profile's infrastructure. This is a self-contained mini-review: Phase 1 only, no challenge round, no resolution.

**Specialists:** The `quick_specialists` from the active profile config (strat: SEC + FEAS, rfe: REQ + SEC)
**Iterations:** 2 (minimum, no convergence exit)
**Budget:** 20% of total budget allocated to quick review

1. Initialize a nested budget tracker:
   ```bash
   ${CLAUDE_SKILL_DIR}/scripts/track-budget.sh init <quick_review_budget>
   ```

2. For each quick-review specialist, compose the standard agent prompt using `phases/self-refinement.md` Step 1 procedure:
   - Role definition from `profiles/<profile>/agents/<specialist>.md`
   - Finding template from `profiles/<profile>/templates/finding-template.md`
   - Cache navigation pointing to `$CACHE_DIR` (the document draft is the only "code" file)
   - Target: `$CACHE_DIR/strategy/strategy-draft.md`

3. Spawn both specialists in parallel. Run 2 iterations of self-refinement.

4. Validate findings via `manage-cache.sh populate-findings`.

5. Extract structured findings for the refine step. For each finding, keep: finding ID, severity, title, description, evidence, recommended fix. Strip challenge/defense context.

6. Save to `$CACHE_DIR/strategy/quick-review-findings.json`:
   ```json
   {
     "findings": [
       {
         "id": "SEC-001",
         "severity": "Important",
         "title": "Missing auth model for new API endpoint",
         "description": "...",
         "evidence": "...",
         "recommended_fix": "..."
       }
     ],
     "specialist_count": 2,
     "iteration_count": 2
   }
   ```

**Skip condition:** `--quick` preset skips the quick review entirely (only 1 refine agent, no adversarial tension to inform).

### Step 3: Adversarial Refine

**Agent selection by preset:**
- `--quick`: Staff Engineer only
- default: Staff Engineer + Product Architect
- `--thorough`: Staff Engineer + Product Architect + Security Engineer

1. For each refine agent, compose the prompt:
   - Role definition from `profiles/<profile>/agents/refine-<persona>.md`
   - Append the document draft content (read from `$CACHE_DIR/strategy/strategy-draft.md`)
   - Append quick-review findings (read from `$CACHE_DIR/strategy/quick-review-findings.json`, formatted as a readable list)
   - Append architecture context if `--context` or `--arch-context` was provided (read from cache context files)
   - If `--principles` specified: append principles section per `protocols/principles.md` Injection into Agents > Refine Agents. Append `upstream_mapping` to Product Architect and Security Engineer agents only.
   - Append the document template (read from `profiles/<profile>/templates/<template_file>`) as the required output structure

2. Spawn all refine agents in parallel.

3. Save each agent's output to `$CACHE_DIR/strategy/refine-<persona>.md`.

4. Track budget for each agent:
   ```bash
   ${CLAUDE_SKILL_DIR}/scripts/track-budget.sh add <char_count> --agent REFINE-<PERSONA>
   ```

### Step 3a: Mediator

Skip if only 1 refine agent was active (use that agent's output directly as the refined strategy).

1. Compose the mediator prompt:
   - Role definition from `profiles/<profile>/agents/refine-mediator.md`
   - Append the original document draft
   - Append quick-review findings
   - If `--principles` specified: append principles section (same format as refine agents). The mediator uses principles as a tie-breaking criterion when selecting between sections.
   - Append each refine agent's output, labeled: "## Staff Engineer Version\n{content}\n\n## Product Architect Version\n{content}"

2. Spawn mediator agent.

3. Parse the mediator's output: split on `---` to separate the merged strategy from the selection log.

4. Save merged strategy to `$CACHE_DIR/strategy/strategy-refined.md`.

5. Save selection log to `$CACHE_DIR/strategy/mediator-log.md`.

6. Track budget:
   ```bash
   ${CLAUDE_SKILL_DIR}/scripts/track-budget.sh add <char_count> --agent MEDIATOR
   ```

### Step 3b: Confirm Gate (optional)

Only when `--confirm` is specified:

1. Display the refined strategy to the user.
2. Display the selection log (if mediator ran).
3. On the **first** `--confirm` gate in the session, display staff input guidance:

   ```
   ## Staff Input Guide
   Write feedback as declarative policy statements (what the strategy SHOULD do),
   not as corrections to the current draft. Think of it like a K8s resource spec:
   declare the desired end state, not the delta.

   DO:  "The strategy should not suggest a Go utility disconnected from current code"
   DON'T: "The strategy currently suggests a Go utility, but it doesn't consider..."

   DO:  "The strategy should consider principle Z, for example Y"
   DON'T: "The strategy is missing principle Z and should do Y"
   ```

   This guidance is displayed **once** at the first confirm gate. Suppress on subsequent gates in the same session (the orchestrator tracks whether the guidance has been shown).

4. Ask:
   > "Refined strategy ready. Options:
   > - **Approve**: proceed to full adversarial review
   > - **Edit**: modify the strategy before review (provide edits inline)
   > - **Abort**: stop pipeline, artifacts preserved in cache"

5. If **Edit**: apply user's changes to `$CACHE_DIR/strategy/strategy-refined.md`, then proceed.
6. If **Abort**: skip full review, print cache location, exit.
7. If **Approve**: proceed.

Without `--confirm`: proceed directly to Step 4.

### Step 4: Full Review

The refined strategy becomes the input for the standard adversarial review (Phases 1-4).

1. Set the scope to the single file: `$CACHE_DIR/strategy/strategy-refined.md` (or `refine-<persona>.md` if no mediator).

2. **Skip scope confirmation**: the user already confirmed at pipeline start. Display:
   > "Starting full adversarial review of refined strategy."

3. Regenerate cache navigation to include the refined strategy as the review target:
   ```bash
   CACHE_DIR=$CACHE_DIR ${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh generate-navigation 1 1
   ```

4. Proceed with standard Phases 1-4 as defined in SKILL.md Steps 4-7:
   - Phase 1: Self-refinement (all specialists for the active profile, or preset selection)
   - Phase 2: Challenge round (adversarial debate)
   - Phase 3: Resolution (consensus)
   - Phase 4: Report (verdict + requirements)

The budget for the full review is the remaining budget after quick review + refine steps.

## Budget Allocation

| Pipeline Step | Budget Share |
|---------------|-------------|
| Quick Review | 20% |
| Adversarial Refine + Mediator | 15% |
| Full Review (Phases 1-4) | 65% |

The orchestrator tracks actual consumption. If quick review + refine consume less than 35%, the surplus rolls into the full review budget.

## Pipeline Presets

| Preset | Quick Review | Refine Agents | Mediator | Full Review | Default Budget |
|--------|-------------|---------------|----------|-------------|----------------|
| `--quick` | skip | 1 (Staff Eng) | skip | quick_specialists, 2 iter | 200K |
| default | quick_specialists, 2 iter | 2 (Staff Eng + Prod Arch) | yes | all specialists, 3 iter | 500K |
| `--thorough` | quick_specialists, 2 iter | 3 (all three) | yes | all specialists, 3 iter | 1M |

Note: `quick_specialists` and specialist counts are profile-dependent (strat: 6 review specialists, rfe: 5 review specialists).

Note: pipeline budgets are higher than review-only budgets because they include create + refine steps.

## Artifacts

All intermediate artifacts stored in `$CACHE_DIR/strategy/`:

| File | Description |
|------|-------------|
| `jira-raw.json` | Raw acli output (Jira input only) |
| `strategy-draft.md` | Normalized template from create step |
| `quick-review-findings.json` | Structured findings from quick review |
| `refine-staff-engineer.md` | Staff Engineer's refined version |
| `refine-product-architect.md` | Product Architect's refined version |
| `refine-security-engineer.md` | Security Engineer's refined version |
| `mediator-log.md` | Section selection decisions |
| `strategy-refined.md` | Final merged strategy (review input) |

With `--keep-cache`, all artifacts are preserved.

## Error Handling

| Scenario | Response |
|----------|----------|
| `extract-jira.sh` fails | Abort pipeline with error. User should check acli config and ticket key. |
| Quick review produces 0 findings | Proceed to refine. Agents refine without finding context (they still add their perspective). |
| Refine agent fails/times out | If 1+ refine agents succeeded, proceed with available versions. If all failed, abort. |
| Mediator fails | Fall back to first successful refine agent's output. Warn user. |
| Budget exceeded during refine | Use best available output so far. Proceed to full review with remaining budget. |
