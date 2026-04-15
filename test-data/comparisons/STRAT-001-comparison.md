# STRAT-001 Review Comparison: adversarial-review vs rfe-creator

**Strategy**: RHOAI support for Ingress / Gateway API sharding
**Date**: 2026-04-08

---

## 1. Finding Overlap

Both tools independently identified the same core issues. Shared findings:

| Theme | adversarial-review | rfe-creator |
|-------|-------------------|-------------|
| OCP per-shard GatewayClass unvalidated | FEAS-001, SCOP-002 | Feasibility #2, Architecture #1 |
| Effort dramatically underestimated (L vs XL-XXL) | FEAS-002 | Feasibility #7, Scope (overall) |
| OSSM multi-Gateway support unverified | FEAS-003, ARCH-004 | Feasibility #3 (EnvoyFilter singleton) |
| Gateway selection mechanism undecided | FEAS-004, SCOP-005, USER-002 | Scope #1 (phase boundary), Testability #6 |
| Acceptance criteria vague/untestable | SCOP-001 | Testability #1, #3 |
| DSCI spec migration path missing | ARCH-001, USER-001 | Architecture #4 (API version bump) |
| Backwards compatibility undefined | FEAS-006, SCOP-004, USER-006 | Scope #5, Testability #6 |
| Missing components from scope (TrustyAI, pipelines, etc.) | FEAS-005, SEC-012 | Feasibility #9, Architecture #9, Scope #3 |
| Cross-gateway access control / RBAC undefined | SEC-001, SEC-002, SEC-007 | Security #2 |
| BYO Gateway auth bypass risk | SEC-003 (KNative), SEC-006 | Security #1 (Critical) |
| KNative/model serving gateway conflicts | ARCH-003 | Feasibility #5 |
| Dashboard RBAC filtering missing | ARCH-007, SEC-011 | (Scope #2 tangentially) |

Both tools converged on the same 5 cross-cutting agreements: unvalidated OCP dependency, undecided gateway selection, underestimated effort, missing backwards compatibility, and absent auth/authz model.

---

## 2. Unique to adversarial-review

Findings that adversarial-review surfaced but rfe-creator did not explicitly call out:

- **SEC-005: mTLS enforcement model for multi-gateway** (PeerAuthentication policies, mesh topology per zone)
- **SEC-008: Audit logging for gateway assignment changes** (Prometheus metrics, AlertManager drift detection)
- **SEC-009: Per-workload gateway assignment covert channel** (data exfiltration via shared storage across zones)
- **SEC-010: Upgrade path security regression testing**
- **USER-003: OCP version adoption blocker** (users may adopt RHOAI expecting multi-gateway on unsupported OCP)
- **USER-004: BYO Gateway operational burden documentation** (example YAML, troubleshooting guide)
- **USER-005: Phased delivery creates partial feature confusion**
- **ARCH-006: Dual-mode routing conflict resolution** (path-based vs host-based coexistence)

Most of adversarial-review's unique findings are in the Security specialist's deeper exploration (mTLS, audit logging, covert channels) and User Impact's adoption/documentation concerns.

---

## 3. Unique to rfe-creator

Findings that rfe-creator surfaced but adversarial-review did not:

- **Authentication coupling as a blocker** (kube-auth-proxy singleton, EnvoyFilter scoped to `data-science-gateway`): rfe-creator's architecture reviewer cross-referenced the actual architecture docs (PLATFORM.md, rhods-operator.md) and identified that EnvoyFilter `data-science-authn-filter` and kube-auth-proxy are singleton-scoped. This was the strongest finding in the rfe-creator review, and adversarial-review's SEC-001 touches it but doesn't identify the specific singleton coupling.
- **"Single-domain is not the problem"**: rfe-creator's architecture reviewer noted the Gateway already has two listeners with different hostnames, and the notebook controller already reads `NOTEBOOK_GATEWAY_NAME`/`NOTEBOOK_GATEWAY_NAMESPACE` env vars. This reframes the RFE, showing multi-gateway partially exists already.
- **HTTPRoute cross-namespace parent references require ReferenceGrant**: Specific Gateway API mechanism detail from architecture docs.
- **DestinationRule singleton** (`data-science-tls-rule`): Specific Istio resource scoping issue.
- **NetworkPolicy gaps**: kube-auth-proxy NetworkPolicy allows ingress only from `openshift-ingress`, additional Gateways in different namespaces need policy updates.
- **Model serving uses VirtualService, not Gateway API**: Strategy assumes HTTPRoute for model serving but KServe uses VirtualService by default with Gateway API disabled.
- **Testability gaps**: 12+ missing edge cases enumerated (gateway deletion, shard failure, concurrent creation, certificate rotation, scale testing), test infrastructure requirements (OCP cluster with sharding), no test strategy breakdown. This is the testability reviewer that adversarial-review lacks entirely.
- **Split into 4 named epics**: Scope reviewer proposed concrete STRAT-001A/B/C/D decomposition with effort estimates per epic.

rfe-creator's advantage comes from two sources: (1) architecture context docs gave reviewers access to actual implementation details (singleton resources, env vars, existing listeners), and (2) the testability reviewer provided systematic test gap analysis.

---

## 4. Verdict Alignment

| Specialist Area | adversarial-review | rfe-creator |
|----------------|-------------------|-------------|
| Feasibility | REVISE | REJECT |
| Architecture | REVISE | REJECT |
| Security | REVISE | REVISE |
| Scope | REJECT | REJECT |
| User Impact / Testability | REVISE (User Impact) | REVISE (Testability) |
| **Overall** | **REJECT** | **REJECT** |

Both tools reach the same overall REJECT verdict. The difference is in per-specialist severity: rfe-creator's feasibility and architecture reviewers are harsher (reject vs revise) because they had architecture docs proving OCP doesn't support per-shard GatewayClass. adversarial-review's specialists hedged with "unvalidated" rather than "confirmed missing."

---

## 5. Depth Comparison

**adversarial-review strengths**:
- More structured per-finding format (ID, severity, confidence, citation, evidence, fix)
- Explicit cross-specialist agreements and disagreements section
- Prioritized remediation roadmap (Priority 1/2/3 with finding cross-references)
- Broader security surface coverage (12 security findings vs 2 risks + 4 NFR gaps)
- Each finding has a concrete fix recommendation

**rfe-creator strengths**:
- Architecture findings grounded in actual code/config references (PLATFORM.md line numbers, rhods-operator.md references, kubeflow.md env var details)
- Testability reviewer provides systematic gap analysis (12+ edge cases, test infrastructure requirements, test strategy structure)
- More precise technical analysis (identifies specific singleton resources by name: `data-science-authn-filter`, `default-gateway`, `data-science-tls-rule`)
- Scope reviewer provides actionable epic decomposition (STRAT-001A/B/C/D with effort sizing)
- Security acceptance criteria are concrete and testable (4 specific criteria with observable conditions)

**Assessment**: adversarial-review provides broader coverage with more findings, while rfe-creator provides deeper technical analysis per finding due to architecture context access.

---

## 6. Specialist Coverage

| adversarial-review | rfe-creator | Coverage difference |
|-------------------|-------------|-------------------|
| FEAS (Feasibility) | Feasibility | Similar scope. rfe-creator's is harsher due to architecture doc evidence. |
| ARCH (Architecture) | Architecture | rfe-creator identified 10 specific findings with doc line references. adversarial-review had 7 findings without code-level grounding. |
| SEC (Security) | Security | adversarial-review produced 12 findings vs rfe-creator's 2 risks + 4 NFR gaps. adversarial-review's security coverage is significantly broader. |
| USER (User Impact) | (no equivalent) | adversarial-review has a dedicated user impact reviewer. rfe-creator folds UX concerns into scope and feasibility. |
| SCOP (Scope & Completeness) | Scope | Both cover scope well. rfe-creator adds the 4-epic split recommendation. |
| (no equivalent) | Testability | rfe-creator has a dedicated testability reviewer. adversarial-review folds testability into SCOP (acceptance criteria) and partially into other specialists. |

The reviewer compositions are complementary. adversarial-review's USER specialist catches adoption/documentation gaps. rfe-creator's testability specialist catches systematic test strategy gaps. Neither tool covers the other's unique specialist area well.

---

## 7. Key Metrics Table

| Dimension | adversarial-review | rfe-creator |
|-----------|-------------------|-------------|
| Total findings | 36 | ~30 (unnumbered, estimated from enumerated concerns) |
| Critical | 7 | ~3 (1 Critical security + architectural blockers) |
| Important | 20 | ~15 (majority of findings) |
| Minor | 9 | ~12 (NFR gaps, informational items) |
| Overall verdict | REJECT | REJECT |
| Specialists | 5 (FEAS, ARCH, SEC, USER, SCOP) | 5 (feasibility, testability, scope, architecture, security) |
| Challenge rounds | 1 iteration | Not specified (pipeline review) |
| Architecture context | No (reviewed strategy text only) | Yes (PLATFORM.md, rhods-operator.md, kubeflow.md, kserve.md) |
| Structured finding IDs | Yes (FEAS-001, SEC-012, etc.) | No (numbered lists per reviewer) |
| Remediation roadmap | Yes (prioritized, cross-referenced) | Partial (split recommendation in scope) |
| Testability coverage | Minimal (via SCOP-001) | Dedicated reviewer with 12+ edge cases |
| User impact coverage | Dedicated reviewer (6 findings) | Distributed across other reviewers |

---

## 8. Assessment

### What the adversarial approach adds

1. **Broader security surface**: 12 security findings vs rfe-creator's 6 (2 risks + 4 gaps). The adversarial review's security specialist explored threat vectors that rfe-creator's security reviewer didn't enumerate: mTLS enforcement gaps, covert channel via per-workload assignment, SSRF via uncontrolled namespace gateway references, audit logging absence. These are real attack surface concerns that a real security reviewer would want to see.

2. **Structured output**: Finding IDs, severity/confidence ratings, citation/evidence/fix structure make findings trackable and actionable. The remediation roadmap with cross-references is directly usable for planning.

3. **Cross-specialist synthesis**: The agreements/disagreements section and cross-cutting findings analysis adds value. Seeing 3+ specialists independently flag the same issue gives confidence it's real.

4. **User impact perspective**: The dedicated USER specialist catches adoption blockers (OCP version confusion, BYO documentation burden, phased delivery confusion) that rfe-creator distributes across reviewers or misses.

### Where adversarial-review falls short

1. **No architecture context**: Without access to actual codebase docs, adversarial-review's findings are based on the strategy text alone. rfe-creator's cross-referencing of PLATFORM.md and rhods-operator.md produced stronger, more precise findings (singleton resources by name, existing env vars, line-number citations). adversarial-review says "unvalidated dependency," rfe-creator says "no per-shard GatewayClass exists in the architecture, here's the line reference."

2. **No testability specialist**: The missing testability reviewer is a gap. rfe-creator's testability reviewer provided 12+ edge cases, test infrastructure requirements, and a test strategy critique that adversarial-review doesn't cover.

3. **Security breadth vs depth**: adversarial-review's 12 security findings cover more surface but some are speculative (confidence: Low/Medium). rfe-creator's 2 security risks are both grounded in architecture doc evidence and more immediately actionable.

4. **Severity calibration**: adversarial-review rated 7 findings as Critical. rfe-creator's security reviewer rated 1 as Critical (BYO Gateway auth bypass) but that one finding is better substantiated with the singleton EnvoyFilter evidence. More findings doesn't always mean better review.

### Comparison with James Tanner's security review

James Tanner's independent security review of STRAT-001 found 1 High + 2 Medium severity findings. For context:
- Both adversarial-review (12 security findings) and rfe-creator (2 risks + 4 NFR gaps) produced significantly more security findings than a single human reviewer.
- The BYO Gateway auth bypass (Critical in both tools) aligns with concerns a human reviewer would flag.
- The volume difference suggests automated tools explore more attack surface, but a human reviewer's findings tend to be higher signal-to-noise. James's 3 findings likely had zero false positives, while some of the automated tools' findings may be lower confidence.

### Bottom line

adversarial-review and rfe-creator are complementary, not competitive. adversarial-review excels at broad coverage, structured output, and security depth. rfe-creator excels at architecture-grounded analysis and testability. The ideal pipeline would combine both: rfe-creator's architecture context and testability reviewer with adversarial-review's structured output format and security depth. Neither tool alone catches everything the other does.

---

*Comparison generated 2026-04-08*
