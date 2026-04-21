# Strat Pipeline: Create, Refine, Review

## Purpose

Orchestrates the full strategy pipeline when `--profile strat` is invoked without `--review-only`. Produces a refined strategy document through adversarial refinement, then subjects it to full adversarial review.

## Prerequisites

- Profile resolved to `strat`
- Input identified: Jira key (regex `^[A-Z][A-Z0-9_]+-\d+$`) or file path
- `--review-only` NOT specified
- Budget initialized

## Procedure

### Step 0: Input Detection

Determine input type:

```
if input matches ^[A-Z][A-Z0-9_]+-\d+$:
    input_type = "jira"
else if file exists at input path:
    input_type = "file"
else:
    error: "Input is neither a valid Jira key nor an existing file: <input>"
```

### Step 1: Create

**Jira input:**

```bash
SCRIPT_DIR="<skill_base>/scripts"
TEMPLATE="<skill_base>/profiles/strat/templates/strategy-template.md"
"$SCRIPT_DIR/extract-jira.sh" --key <JIRA_KEY> --template "$TEMPLATE" > "$CACHE_DIR/strategy/strategy-draft.md"
```

If `extract-jira.sh` fails, abort with the error message.

**File input:**

Read the input file. If it already follows the strategy template structure (has at least 4 of the 7 section headings: Summary, Problem Statement, Goals, Acceptance Criteria, Dependencies, Constraints, Open Questions), copy it as-is to `$CACHE_DIR/strategy/strategy-draft.md`.

If the file does not follow the template structure, the orchestrator normalizes it: read the content and map it into the template sections. Use the file content as the Problem Statement, extract any bullet lists as potential ACs/Goals, and leave other sections as "(To be defined during refinement.)"

Save to `$CACHE_DIR/strategy/strategy-draft.md`.

**Display:** Show the user the strategy draft and confirm:
> "Strategy draft created from {jira key / file}. Proceeding with quick review and adversarial refinement."

This is informational, not a gate (unless `--confirm` is active, in which case gates are at Step 3b).

### Step 2: Quick Review

Run a lightweight adversarial review on the strategy draft using the existing strat profile infrastructure. This is a self-contained mini-review: Phase 1 only, no challenge round, no resolution.

**Specialists:** SEC + FEAS (the `quick_specialists` from strat profile config)
**Iterations:** 2 (minimum, no convergence exit)
**Budget:** 20% of total budget allocated to quick review

1. Initialize a nested budget tracker:
   ```bash
   scripts/track-budget.sh init <quick_review_budget>
   ```

2. For each quick-review specialist (SEC, FEAS), compose the standard agent prompt using `phases/self-refinement.md` Step 1 procedure:
   - Role definition from `profiles/strat/agents/<specialist>.md`
   - Finding template from `profiles/strat/templates/finding-template.md`
   - Cache navigation pointing to `$CACHE_DIR` (the strategy draft is the only "code" file)
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
   - Role definition from `profiles/strat/agents/refine-<persona>.md`
   - Append the strategy draft content (read from `$CACHE_DIR/strategy/strategy-draft.md`)
   - Append quick-review findings (read from `$CACHE_DIR/strategy/quick-review-findings.json`, formatted as a readable list)
   - Append architecture context if `--context` was provided (read from cache context files)
   - Append the strategy template (read from `profiles/strat/templates/strategy-template.md`) as the required output structure

2. Spawn all refine agents in parallel.

3. Save each agent's output to `$CACHE_DIR/strategy/refine-<persona>.md`.

4. Track budget for each agent:
   ```bash
   scripts/track-budget.sh add <char_count> --agent REFINE-<PERSONA>
   ```

### Step 3a: Mediator

Skip if only 1 refine agent was active (use that agent's output directly as the refined strategy).

1. Compose the mediator prompt:
   - Role definition from `profiles/strat/agents/refine-mediator.md`
   - Append the original strategy draft
   - Append quick-review findings
   - Append each refine agent's output, labeled: "## Staff Engineer Version\n{content}\n\n## Product Architect Version\n{content}"

2. Spawn mediator agent.

3. Parse the mediator's output: split on `---` to separate the merged strategy from the selection log.

4. Save merged strategy to `$CACHE_DIR/strategy/strategy-refined.md`.

5. Save selection log to `$CACHE_DIR/strategy/mediator-log.md`.

6. Track budget:
   ```bash
   scripts/track-budget.sh add <char_count> --agent MEDIATOR
   ```

### Step 3b: Confirm Gate (optional)

Only when `--confirm` is specified:

1. Display the refined strategy to the user.
2. Display the selection log (if mediator ran).
3. Ask:
   > "Refined strategy ready. Options:
   > - **Approve**: proceed to full adversarial review
   > - **Edit**: modify the strategy before review (provide edits)
   > - **Abort**: stop pipeline, artifacts preserved in cache"

4. If **Edit**: apply user's changes to `$CACHE_DIR/strategy/strategy-refined.md`, then proceed.
5. If **Abort**: skip full review, print cache location, exit.
6. If **Approve**: proceed.

Without `--confirm`: proceed directly to Step 4.

### Step 4: Full Review

The refined strategy becomes the input for the standard adversarial review (Phases 1-4).

1. Set the scope to the single file: `$CACHE_DIR/strategy/strategy-refined.md` (or `refine-<persona>.md` if no mediator).

2. **Skip scope confirmation**: the user already confirmed at pipeline start. Display:
   > "Starting full adversarial review of refined strategy."

3. Regenerate cache navigation to include the refined strategy as the review target:
   ```bash
   CACHE_DIR=$CACHE_DIR scripts/manage-cache.sh generate-navigation 1 1
   ```

4. Proceed with standard Phases 1-4 as defined in SKILL.md Steps 4-7:
   - Phase 1: Self-refinement (all 6 strat specialists or preset selection)
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
| `--quick` | skip | 1 (Staff Eng) | skip | SEC+FEAS, 2 iter | 200K |
| default | SEC+FEAS, 2 iter | 2 (Staff Eng + Prod Arch) | yes | all 6, 3 iter | 500K |
| `--thorough` | SEC+FEAS, 2 iter | 3 (all three) | yes | all 6, 3 iter | 1M |

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
