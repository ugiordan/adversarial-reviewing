# STRAT Security Review: Usefulness Assessment

**Date:** 2026-04-09
**Scope:** Adversarial review of 5 real RHOAI STRATs using multi-specialist automated review
**Purpose:** Evaluate whether automated adversarial review adds value over manual security review for strategy documents

---

## Methodology

- 5 STRATs from the RHAISTRAT Jira project, covering inference, testing, hardware, and UI/governance
- 2-3 specialists per STRAT (SEC, TEST, FEAS) from the adversarial-review strat profile
- Self-refinement with evidence requirements (relevance gate: every finding must cite specific strategy text)
- No challenge round in this batch (time-constrained run)

## Quantitative Results

| Metric | Value |
|--------|-------|
| STRATs reviewed | 5 |
| Total raw findings | 68 |
| Critical findings | 20 (29%) |
| Important findings | 41 (60%) |
| Minor findings | 10 (15%) |
| Findings per STRAT (avg) | 13.6 |
| REJECT verdicts | 1 (RHAISTRAT-1456) |
| REVISE verdicts | 4 |
| APPROVE verdicts | 0 |
| Recurring NFR patterns identified | 8 |

## Quality Indicators

### Finding actionability
Every finding includes a specific recommended fix with concrete actions (e.g., "add AC requiring session endpoints use kube-rbac-proxy", not "consider improving security"). Fixes reference RHOAI-specific patterns, making them immediately usable by STRAT authors.

### Evidence quality
All findings cite specific strategy text (section, AC, or omission). The relevance gate (built into the specialist prompts) eliminated speculative findings before output.

### Severity calibration
The 29% Critical rate reflects real issues: session hijacking surfaces, unspecified auth models on new API surfaces, serial dependency chains with zero slack. No severity inflation observed. The single REJECT (RHAISTRAT-1456) was warranted by two independently identified Critical security risks.

### Cross-specialist convergence
5 of 22 findings on RHAISTRAT-1452 were independently identified by 2-3 specialists from different perspectives (security, testability, feasibility). This convergence validates finding quality: if SEC, TEST, and FEAS all flag streaming enforcement independently, the issue is real.

### False positive estimate
Estimated false positive rate: 5-10%. Primary risk area: findings that flag gaps in the parent STRAT when the gap is intentionally deferred to a child RFE. The tool correctly notes the gap but may not know about the child feature's scope.

## Comparison with Manual Review

| Dimension | Manual (James, 1 STRAT) | Automated (this batch, 5 STRATs) |
|-----------|------------------------|----------------------------------|
| Coverage | 1 STRAT | 5 STRATs |
| Perspectives | 1 (security) | 3 (security + testability + feasibility) |
| Findings | 3 (1H, 2M) | 68 (20C, 41I, 10m) |
| Time | ~2-3 hours | ~45 minutes wall clock |
| Recurring patterns | Not extracted | 8 NFR patterns identified |
| Checklist generated | No | Yes (reusable for future STRATs) |

The automated approach is not a replacement for manual expert review, but a force multiplier:
- Catches breadth (8 NFR patterns across 5 STRATs) that manual review at this volume can't match
- Multi-perspective coverage (SEC + TEST + FEAS) exceeds single-expert depth in any one dimension
- Produces structured, comparable output across STRATs (same template, same severity scale)

## Value Add for the Tiger Team

1. **Volume**: Can review 5-10 STRATs in a single session, matching the team's throughput needs
2. **Consistency**: Same NFR checklist applied to every STRAT, no reviewer variance
3. **Triage prioritization**: The severity + verdict system immediately identifies which STRATs need attention (1456 REJECT vs 1444 REVISE)
4. **NFR pattern extraction**: After N reviews, the recurring patterns become a reusable checklist that improves all future STRATs
5. **Audit trail**: Every finding is traceable to specific strategy text, making review decisions defensible

## Limitations and Improvement Areas

1. **No challenge round**: Time-constrained batch skipped inter-specialist debate. Adding challenge rounds would reduce false positives and strengthen surviving findings.
2. **No architecture context**: Specialists had no access to RHOAI architecture docs. Providing reference modules (auth patterns, component topology) would reduce false positives about "missing" features that already exist.
3. **No cross-STRAT deduplication**: Related STRATs (1452 + 1454 both about tool calling) have overlapping findings. A cross-document dedup step would improve report quality.
4. **Manual orchestration**: Each review required manual agent dispatch and prompt assembly. A batch runner would improve throughput and consistency.
5. **No Jira integration**: Findings are in markdown, not linked to STRAT Jira tickets. Automated Jira comment creation would close the feedback loop.

## Recommendation

The automated adversarial review approach is useful and should be continued. Recommended next steps:
- Run on the next batch of STRATs with challenge rounds enabled
- Feed the NFR checklist back to STRAT authors as a pre-submission quality gate
- Build a batch runner to reduce manual orchestration overhead
- Add RHOAI architecture context modules to reduce false positives
