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

## Prerequisites

- Phase 2 complete — all challenge round positions collected (or Phase 1 findings if Phase 2 budget-skipped)
- At least one finding exists (if zero findings from all agents, skip Phase 3 entirely — Phase 4 generates an "all clear" report)
- Active specialist count (N) known
- If Phase 2 was skipped due to budget exhaustion, enter [No-Debate Resolution](#no-debate-resolution) regardless of N — no debate positions exist

## Procedure

### Step 1: Compute Thresholds

Calculate the strict majority and quorum thresholds from the active specialist count:

```
N = number of active specialists
strict_majority = ceil((N + 1) / 2)
quorum = ceil((N + 1) / 2)
```

**Important:** For N=1 (single-specialist mode), these formulas are not used. See the [Single-Specialist Mode](#single-specialist-mode) section below — it replaces the multi-agent resolution rules entirely.

Both thresholds use the same formula. The distinction is what they apply to:
- **Strict majority:** at least `ceil((N+1)/2)` specialists must **Agree** for a finding to pass
- **Quorum:** at least `ceil((N+1)/2)` specialists must take a **position** (Agree or Challenge, not Abstain) for a valid vote

### Step 2: Count Originator Position

The originator of a finding counts as an **implicit Agree** unless they explicitly withdrew the finding during the challenge round. This implicit vote is included in all vote tallies.

### Step 3: Resolve Each Finding

For each finding, tally positions and apply rules in order:

#### 3a. Consensus (Unanimous Agreement)

**Condition:** All specialists who took a position chose Agree, and no challenges exist.

**Result:** Include in report Section 3 (Consensus Findings).

#### 3b. Strict Majority (Quorum Met)

**Condition:**
- Quorum is met: `(agree_count + challenge_count) >= quorum`
- Strict majority agrees: `agree_count >= strict_majority`

**Result:** Include in report Section 4 (Majority Findings). Note all dissenting positions and any severity disputes.

#### 3c. No Majority (Quorum Met)

**Condition:**
- Quorum is met: `(agree_count + challenge_count) >= quorum`
- Strict majority NOT reached: `agree_count < strict_majority`

**Result:** Escalate to user. Include in report Section 5 (Escalated Disagreements) with all positions presented.

#### 3d. Quorum Not Met

**Condition:**
- Quorum is NOT met: `(agree_count + challenge_count) < quorum`
- Too many abstentions to reach a valid decision

**Result:** Escalate to user. Include in report Section 6 (Escalated - Quorum Not Met).

#### 3e. Persistent Disagreement

**Condition:** Finding went through all 3 challenge round iterations without reaching consensus or majority.

**Evidence-based resolution (post iteration 3 rebuttal):**
- If a challenger provided no file:line evidence in iteration 3, treat their Challenge as a retraction (convert to Abstain). Recount votes with the updated positions.
- If an originator provided no file:line evidence in iteration 3, treat the finding as withdrawn. Move to Section 7 (Dismissed).
- If both sides provided file:line evidence and still disagree, this is a genuine disagreement. Escalate to user with all evidence presented.

**Result:** Escalate to user. Include in report Section 5 (Escalated Disagreements) with all evidence from the rebuttal round.

#### 3f. Dismissed

**Condition:** Strict majority chose Challenge (i.e., `challenge_count >= strict_majority`).

**Result:** Include in report Section 7 (Dismissed Findings) with rejection reasoning.

### Step 4: Resolve Severity

For findings that pass (consensus or majority):

1. **Majority severity:** use the severity level agreed by the majority of specialists
2. **No severity majority:** use the **highest** severity among all Agree positions
3. **Severity disputes:** note in the report which specialists disagreed on severity

### Step 5: Post-Debate Deduplication

Run cross-specialist deduplication on resolved findings:

```bash
scripts/deduplicate.sh <resolved_findings> --cross-specialist
```

This catches near-duplicates that survived the challenge round because they were raised by different specialists with different framing.

### Step 6: Flag Co-located Findings

Identify cross-specialist findings that target **overlapping file and line ranges**:

- Same file path
- Overlapping or adjacent line ranges

Co-located findings are **not merged** — they remain separate findings. They are flagged and grouped in report Section 9 (Co-located Findings) so the user can see how different specialist perspectives relate to the same code region.

### Step 7: Classify Challenge Round Findings

New findings raised during Phase 2 are resolved using the same rules above. They are additionally reported in Section 8 (Challenge Round Findings) with their mini self-refinement results from Phase 2, Step 9.

## Single-Specialist Mode

When only 1 specialist is active (N = 1):

- **No consensus is possible** — there is only one voice
- The devil's advocate pass from Phase 2 replaces the debate
- All findings that survived the devil's advocate challenge are included
- The entire report carries a **reduced-confidence disclaimer**:

> "This review was conducted by a single specialist. Findings have not been cross-validated by independent reviewers and should be treated with reduced confidence."

Resolution in single-specialist mode:
- Findings the specialist maintained after devil's advocate → include with reduced confidence
- Findings the specialist withdrew → dismiss
- Findings the devil's advocate successfully challenged (specialist conceded) → dismiss

## No-Debate Resolution

When Phase 2 was skipped due to budget exhaustion (regardless of specialist count):

- **No debate occurred** — findings have only been self-refined, not challenged
- All Phase 1 findings are included with a **budget-truncation disclaimer** (distinct from the single-specialist disclaimer)
- Skip Steps 3-4, 6-7 (no positions to resolve, no challenge round findings)
- Run Step 5 (post-debate deduplication) to catch cross-specialist near-duplicates, then proceed to Phase 4

> "Review truncated due to token budget. Some iterations were skipped and findings may be incomplete."

This mode differs from Single-Specialist Mode: single-specialist has a devil's advocate challenge; no-debate resolution has no challenge at all. Use the budget truncation disclaimer, not the single-specialist disclaimer.

## Resolution Truth Table

| Agree | Challenge | Abstain | Quorum Met? | Majority? | Result |
|-------|-----------|---------|-------------|-----------|--------|
| N     | 0         | 0       | Yes         | Yes       | Consensus |
| >= ceil((N+1)/2) | < ceil((N+1)/2) | any | Yes | Yes | Majority (note dissent) |
| < ceil((N+1)/2) | >= 1 | any | Yes | No | Escalate (disagreement) |
| any   | any       | many    | No          | N/A       | Escalate (no quorum) |
| < ceil((N+1)/2) | >= ceil((N+1)/2) | any | Yes | No | Dismissed |

## Cache Interaction

Phase 3 reads deduplicated findings from `{CACHE_DIR}/findings/`. No cache writes occur during resolution. Deduplication and ranking operate on the finding files already in the cache. The `cross-agent-summary.md` generated in Phase 2 provides the complete finding inventory for resolution.

## References

- `scripts/deduplicate.sh` — post-debate cross-specialist deduplication
- `scripts/manage-cache.sh` — cache management (findings read from `{CACHE_DIR}/findings/`)
- `templates/report-template.md` — report sections that resolution maps findings into
- `protocols/convergence-detection.md` — iteration bounds that feed into persistent disagreement detection
- `agents/devils-advocate.md` — single-specialist devil's advocate role
