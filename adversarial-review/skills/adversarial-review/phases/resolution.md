# Phase 3: Resolution

## Purpose

Apply deterministic resolution rules to each finding based on specialist positions from the challenge round. Every finding is classified as consensus, majority, escalated, or dismissed. Resolution is performed by the orchestrator — agents are not involved in this phase.

### Agreement Level Classification

After resolving all findings, compute the overall agreement level for the report:

| Agreement Level | Condition | Report Label |
|----------------|-----------|--------------|
| **Full Consensus** | All findings resolved as Consensus (Section 3) | "Consensus" |
| **Strong Agreement** | >75% of findings are Consensus or Majority with no Escalated | "Strong Agreement" |
| **Partial Agreement** | Mix of Consensus, Majority, and Escalated findings | "Partial Agreement" |
| **Split Decision** | >25% of findings are Escalated or Dismissed | "Split Decision" |
| **No Agreement** | Majority of findings are Escalated | "No Agreement" |

This classification is used in the report's executive summary and bottom line. **Never use "Consensus" as a label when any findings were resolved by majority vote or escalated.**

**Reduced-pool findings:** When a finding's N_effective < N (not all specialists participated), the finding's agreement label is qualified with the pool size. For example, "Consensus (3/5)" means all 3 participating specialists agreed, but 2 abstained. This is still consensus within the voting pool, but the qualification signals reduced scrutiny.

## Prerequisites

- Phase 2 complete — all challenge round positions collected (or Phase 1 findings if Phase 2 budget-skipped)
- At least one finding exists (if zero findings from all agents, skip Phase 3 entirely — Phase 4 generates an "all clear" report)
- Active specialist count (N) known
- If Phase 2 was skipped due to budget exhaustion, enter [No-Debate Resolution](#no-debate-resolution) regardless of N — no debate positions exist

## Procedure

### Step 1: Record Global Specialist Count

Record the global active specialist count N. This is used for report metadata (e.g., "Consensus (3/5 specialists)") but is **not used for threshold computation**. Thresholds are computed per-finding from N_effective in Step 2.

```
N = number of active specialists
```

**Important:** For N=1 (single-specialist mode), skip Steps 2-3 entirely. See the [Single-Specialist Mode](#single-specialist-mode) section below.

Threshold formulas (applied per-finding using N_effective from Step 2):
- **Strict majority:** `ceil((N_effective + 1) / 2)` specialists must **Agree** for a finding to pass
- **Quorum:** `ceil((N_effective + 1) / 2)` specialists must take a **position** (Agree or Challenge, not Abstain) for a valid vote

### Step 2: Compute Domain-Scoped Voting Pool

For each finding, compute the **voting pool**: the set of specialists whose positions count for resolution. This replaces the global N with a per-finding N_effective, preventing legitimate domain abstentions from breaking quorum.

#### 2a. Pool Membership

Pool membership is determined by actual voting behavior during Phase 2, not by static domain category matching:

1. **Originator:** Always in pool (implicit Agree unless explicitly withdrawn)
2. **Active voters:** Any specialist who took a position of **Agree** or **Challenge** on the finding is in the pool
3. **Abstainers:** Specialists who chose **Abstain** are **excluded** from the pool

This is symmetric: both Agree and Challenge count as opt-in. Abstain means "this is outside my domain or I have no opinion," and that non-participation doesn't penalize the finding's quorum.

#### 2b. Compute N_effective

```
N_effective = count of pool members (originator + active voters)
            = agree_count + challenge_count
```

Recompute thresholds per-finding:

```
strict_majority = ceil((N_effective + 1) / 2)
quorum = ceil((N_effective + 1) / 2)
```

Since N_effective equals the count of active positions by definition, `(agree_count + challenge_count) = N_effective >= quorum` is always true when N_effective >= 2. This means **Rule 3e (Quorum Not Met) is structurally unreachable** with domain-scoped pools. It is retained as a safety net but should never trigger.

#### 2c. Minimum Pool Size

**N_effective must be >= 2** for multi-agent resolution rules. If N_effective = 1 (only the originator voted, all others abstained), the finding did not receive cross-agent scrutiny and MUST use [Single-Specialist Mode](#single-specialist-mode) resolution rules regardless of the global specialist count.

This prevents a finding from achieving "Consensus" status when no other specialist engaged with it.

#### 2d. Report Metadata

For each finding, record in report metadata:
- `N_effective`: voting pool size
- `pool_members`: list of specialist prefixes in the pool
- `abstained`: list of specialist prefixes who abstained (excluded from pool)

When N_effective < N (global specialist count), the report labels the finding with the pool size: e.g., "Consensus (3/5 specialists)" rather than just "Consensus".

### Step 3: Resolve Each Finding

Collect all challenge round positions into a votes JSON file and run the resolution script:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/resolve-votes.py <votes.json>
```

The orchestrator builds `votes.json` from challenge round responses:

```json
{
  "global_specialist_count": 5,
  "findings": [
    {
      "id": "SEC-001",
      "originator": "SEC",
      "severity": "Important",
      "votes": [
        {"specialist": "SEC", "position": "Agree", "severity": "Important"},
        {"specialist": "CORR", "position": "Challenge", "severity": null},
        {"specialist": "ARCH", "position": "Abstain", "severity": null}
      ]
    }
  ]
}
```

The script applies resolution rules in order (consensus, majority, dismissed, escalated, quorum not met) using domain-scoped voting pools, and resolves severity for passing findings. Each finding in the output includes: `outcome`, vote counts, `n_effective`, `n_global`, `resolved_severity`, `severity_disputed`, `label` (e.g. "Consensus (3/5 specialists)"), and `report_section`.

**Pre-script adjustments for persistent disagreement (3f):**

Before running `resolve-votes.py`, handle iteration 3 rebuttal evidence:
- If a challenger provided no file:line evidence in iteration 3, convert their Challenge to Abstain in the votes JSON
- If an originator provided no file:line evidence in iteration 3, remove the finding from the votes JSON (dismissed)
- Then run the script on the adjusted votes

### Step 5: Post-Debate Deduplication

Run cross-specialist deduplication on resolved findings:

```bash
${CLAUDE_SKILL_DIR}/scripts/deduplicate.sh <resolved_findings> --cross-specialist
```

This catches near-duplicates that survived the challenge round because they were raised by different specialists with different framing.

### Step 6: Flag Co-located Findings

**Code profile:** Identify cross-specialist findings that target **overlapping file and line ranges** (same file path, overlapping or adjacent line ranges).

**Strat/RFE profiles:** Identify cross-specialist findings that target **the same document and citation** (same Document value, same or overlapping section/paragraph reference).

Co-located findings are **not merged** — they remain separate findings. They are flagged and grouped in report Section 9 (Co-located Findings) so the user can see how different specialist perspectives relate to the same region.

### Step 7: Classify Challenge Round Findings

New findings raised during Phase 2 are resolved using the same rules above. They are additionally reported in Section 8 (Challenge Round Findings) with their mini self-refinement results from Phase 2, Step 9.

## Single-Specialist Mode

This mode applies in two cases:
1. **N = 1:** Only one specialist is active globally
2. **N_effective = 1:** Multiple specialists are active, but only the originator engaged with a specific finding (all others abstained). This is a per-finding fallback from domain-scoped voting pools (Step 2c).

When in single-specialist mode:

- **No consensus is possible** — there is only one voice
- For N=1: the devil's advocate pass from Phase 2 replaces the debate
- For N_effective=1: the finding was reviewed by the panel but no one outside the originator's domain engaged
- All findings that survived are included with a **reduced-confidence disclaimer**:

> "This review was conducted by a single specialist. Findings have not been cross-validated by independent reviewers and should be treated with reduced confidence."

Resolution in single-specialist mode:

**N=1 (global single-specialist):**
- Findings the specialist maintained after devil's advocate → include with reduced confidence
- Findings the specialist withdrew → dismiss
- Findings the devil's advocate successfully challenged (specialist conceded) → dismiss

**N_effective=1 (per-finding pool fallback):**
- The finding went through Phase 2 but no other specialist engaged (all abstained)
- Include the finding with reduced confidence and the disclaimer: "No cross-agent scrutiny: all other specialists abstained"
- The originator's self-assessed severity and confidence are used without adjustment
- These findings appear in Section 3 with the reduced-pool qualifier (e.g., "1/5 specialists")

## No-Debate Resolution

When Phase 2 was skipped due to budget exhaustion (regardless of specialist count):

- **No debate occurred** — findings have only been self-refined, not challenged
- All Phase 1 findings are included with a **budget-truncation disclaimer** (distinct from the single-specialist disclaimer)
- Skip Steps 3-4, 6-7 (no positions to resolve, no challenge round findings)
- Run Step 5 (post-debate deduplication) to catch cross-specialist near-duplicates, then proceed to Phase 4

> "Review truncated due to token budget. Some iterations were skipped and findings may be incomplete."

This mode differs from Single-Specialist Mode: single-specialist has a devil's advocate challenge; no-debate resolution has no challenge at all. Use the budget truncation disclaimer, not the single-specialist disclaimer.

## Resolution Truth Table

All thresholds use N_effective (voting pool size), not global N. N_effective = agree_count + challenge_count. Abstainers are excluded from the pool.

| Agree | Challenge | N_effective | Result |
|-------|-----------|-------------|--------|
| = N_effective (all) | 0 | >= 2 | Consensus (3a) |
| >= ceil((N_eff+1)/2) | < ceil((N_eff+1)/2) | >= 2 | Majority (3b, note dissent) |
| any | >= ceil((N_eff+1)/2) | >= 2 | Dismissed (3c) |
| < ceil((N_eff+1)/2) | 1 to < ceil((N_eff+1)/2) | >= 2 | Escalate (3d, disagreement) |
| 1 (originator only) | 0 | 1 | Single-specialist resolution |

With domain-scoped pools, quorum is always met when N_effective >= 2 (by construction). The old "Quorum Not Met" row is structurally unreachable and omitted from this table.

## Verdict Resolution (strat/rfe profiles only)

When the active profile has `has_verdicts: true` (strat, rfe), Phase 3 runs verdict resolution alongside finding resolution. This is a separate track that produces per-document verdicts.

### Procedure

For each reviewed document (strategy or RFE):

1. **Collect verdicts:** Gather each agent's verdict (Approve / Revise / Reject) from their findings output and challenge round positions.

2. **Apply resolution rules:**

| Condition | Result |
|-----------|--------|
| All agents chose the same verdict | **Unanimous verdict** |
| Strict majority agrees on a verdict | **Majority verdict** (note dissent) |
| No majority (e.g., 2 Approve, 2 Revise, 1 Reject) | **Conservative tiebreak**: most conservative verdict wins (Reject > Revise > Approve) |

3. **Record dissent:** For non-unanimous verdicts, preserve each dissenting agent's verdict and rationale in the report.

### Severity-Based Verdict Escalation

After agent verdicts are resolved, apply finding-severity rules as a second pass. These rules can **escalate** a verdict (Approve → Revise, Revise → Reject) but never downgrade one. This makes verdicts reproducible regardless of model temperature.

| Rule | Condition | Escalation |
|------|-----------|------------|
| **Critical consensus** | Any Critical finding with Consensus or Majority agreement | → REJECT |
| **Critical low-confidence** | Any Critical finding with LOW confidence (unresolved) | → REVISE (minimum) |
| **Accumulation** | 5+ findings at Important or higher (any agreement level) | → REJECT |
| **Important cluster** | 3-4 findings at Important or higher | → REVISE (minimum) |
| **Constraint violation** | Any finding matching a loaded constraint with severity floor High+ | → REVISE (minimum) |

Apply rules in order. Once a verdict reaches REJECT, no further rules are evaluated for that document.

**Example:** Agent votes resolve to Approve (3 Approve, 2 Revise). But findings include 1 Critical with Consensus agreement. The severity rule escalates the verdict to REJECT regardless of the agent vote outcome.

The escalation is logged in the report with the triggering rule and finding IDs, so the strategy author knows exactly why the verdict was overridden.

### Conservative Tiebreaker Rationale

When specialists can't agree on their vote, the conservative option protects quality:
- A strategy where half the specialists want to reject should not be approved
- "Revise" is always safer than "approve" when there's genuine disagreement
- The dissenting positions are preserved in the report so the strategy author can see why

### Verdict Agreement Level

Verdict agreement level is computed separately from finding agreement level:

| Verdict Agreement | Condition |
|-------------------|-----------|
| **Full Consensus** | All document verdicts are unanimous |
| **Strong Agreement** | >75% of verdicts are unanimous or majority, no tiebreaks |
| **Partial Agreement** | Mix of unanimous, majority, and tiebreak verdicts |
| **Split Decision** | >25% of verdicts required conservative tiebreak |
| **No Agreement** | Majority of verdicts required tiebreak |

The report's executive summary uses the **verdict agreement level** (not the finding agreement level) as the primary indicator for strat/rfe profiles.

### Verdict Challenges

During Phase 2, agents may issue verdict challenges (challenging another agent's overall verdict independently of individual findings). These are processed during verdict resolution:

- If an agent's verdict challenge is supported by majority, the target agent's verdict is overridden for resolution purposes
- The original verdict and the challenge are both recorded in the report

## Confidence Scoring

After resolution, assign a confidence label (HIGH / MEDIUM / LOW) to each validated finding using tiered rules. This scoring is deterministic given the resolution inputs.

### Confidence Signals

Four independent signals feed confidence scoring:

| Signal | Description | Values |
|--------|-------------|--------|
| **Specialist self-assessment** | The specialist's own Confidence field from the finding template | High=1.0, Medium=0.5, Low=0.25 |
| **Cross-specialist corroboration** | Another specialist independently flagged a related issue (same document section + same risk category, or same NFR checklist item) | Corroborated=1.0, Uncorroborated=0.0 |
| **Challenge survival** | Finding went through challenge round and was defended | Survived=1.0, Unchallenged=0.5, Challenged-and-weakened=0.25, N_effective=1 (no engagement)=0.25 |
| **Evidence specificity** | Finding cites a specific section/AC vs. citing an omission | Specific citation=1.0, Omission="not mentioned"=0.5, Vague=0.25 |

### Confidence Label Rules (Option C: Tiered)

Apply rules in order. First matching rule determines the label.

**HIGH confidence:**
- Finding was corroborated by 2+ specialists from different domains, OR
- Finding survived challenge round with defense accepted AND specialist self-assessed High, OR
- Finding matches an NFR checklist item scored NO with Critical severity tree outcome

**MEDIUM confidence:**
- Single specialist, self-assessed High, with specific citation (not omission), OR
- Corroborated by 2+ specialists but at least one self-assessed Low, OR
- Survived challenge round but defense was partial (challenger withdrew on different grounds), OR
- Finding matches an NFR checklist item scored NO with Important severity tree outcome

**LOW confidence:**
- Single specialist, self-assessed Medium or Low, with no corroboration, OR
- Finding is about an omission (citation is "not mentioned" or similar) with no corroboration, OR
- Did not go through challenge round AND no cross-specialist corroboration, OR
- Finding matches an NFR checklist item scored PARTIAL

### Signal Metadata

For transparency, record all 4 signal values alongside the label. This allows stakeholders to understand why a finding received its confidence level.

```
Confidence: HIGH
Signals:
  self_assessment: High (1.0)
  corroboration: SEC-003 + TEST-007 independently flagged (1.0)
  challenge_survival: survived, defense accepted (1.0)
  evidence_specificity: cites AC #4 specifically (1.0)
```

### NFR Scan Integration

When Layer 2 (NFR checklist scan) is available, findings that align with NFR checklist gaps receive a confidence boost:

- Finding aligns with NFR item scored NO → boost one tier (LOW→MEDIUM, MEDIUM→HIGH, HIGH stays HIGH)
- Finding aligns with NFR item scored PARTIAL → no change
- Finding has no NFR checklist alignment → no change (neither boost nor penalty)

This rewards findings that are independently confirmed by the deterministic checklist layer.

### Confidence in Requirements Output

The confidence label determines placement in the requirements output:
- **HIGH confidence** → "Required Amendments" (STRAT must address before approval)
- **MEDIUM confidence** → "Recommended Amendments" (STRAT should address)
- **LOW confidence** → "Findings Requiring Human Review" (team should evaluate)

## Output Resolution Status

After resolution completes, output a final progress status block (see SKILL.md "Progress Display") showing "Phase 3: Resolution" with the breakdown:

```
│ Consensus: N  │  Majority: N  │  Escalated: N  │  Dismissed: N  │
```

This is the last status block before the report. It gives the user an immediate sense of how the review went before the full report is assembled.

## Cache Interaction

Phase 3 reads deduplicated findings from `{CACHE_DIR}/findings/`. No cache writes occur during resolution. Deduplication and ranking operate on the finding files already in the cache. The `cross-agent-summary.md` generated in Phase 2 provides the complete finding inventory for resolution.

## References

- `${CLAUDE_SKILL_DIR}/scripts/deduplicate.sh` — post-debate cross-specialist deduplication
- `${CLAUDE_SKILL_DIR}/scripts/manage-cache.sh` — cache management (findings read from `{CACHE_DIR}/findings/`)
- `templates/report-template.md` — report sections that resolution maps findings into
- `protocols/convergence-detection.md` — iteration bounds that feed into persistent disagreement detection
- `phases/challenge-round.md` — domain affinity tables (advisory routing, pool metadata)
- `agents/devils-advocate.md` — single-specialist devil's advocate role
