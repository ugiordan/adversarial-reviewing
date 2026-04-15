# Agents & Profiles

Detailed reference for all specialist agents across both profiles.

## Code profile agents

### Security Auditor (SEC)

**Focus**: Vulnerabilities, injection, authentication, cryptography, OWASP Top 10.

**What it checks**:

- SQL injection, command injection, XSS, path traversal
- Authentication and authorization gaps
- Cryptographic weaknesses (weak algorithms, hardcoded keys)
- Secret exposure (API keys, credentials in code)
- Source trust classification (First-Party / Third-Party / Generated / Vendored / Test)
- OWASP Top 10:2025 patterns via reference modules
- Kubernetes/operator security patterns

**Unique feature**: Source Trust field. Every finding is tagged with the trust level of the code where it was found. Findings in third-party or generated code are treated differently from first-party code.

### Performance Analyst (PERF)

**Focus**: Complexity, memory, I/O, caching, scalability.

**What it checks**:

- Algorithmic complexity (O(n^2) loops, unnecessary allocations)
- Memory leaks and unbounded growth
- I/O bottlenecks (synchronous calls, missing batching)
- Cache misuse (missing invalidation, unbounded caches)
- Concurrency issues (lock contention, goroutine leaks)
- Scalability concerns (linear scans of large datasets)

### Code Quality Reviewer (QUAL)

**Focus**: Maintainability, SOLID, patterns, readability.

**What it checks**:

- SOLID principle violations
- Code duplication and dead code
- Naming conventions and readability
- Error handling patterns
- Test coverage gaps
- Documentation quality

### Correctness Verifier (CORR)

**Focus**: Logic errors, edge cases, race conditions, invariants.

**What it checks**:

- Off-by-one errors, boundary conditions
- Null/nil dereferences
- Race conditions and data races
- Contract violations (preconditions, postconditions, invariants)
- Error propagation (swallowed errors, wrong error types)
- State machine correctness

### Architecture Reviewer (ARCH)

**Focus**: Coupling, cohesion, boundaries, extensibility.

**What it checks**:

- Package/module boundary violations
- Circular dependencies
- Abstraction leaks
- Interface design (too broad, too narrow)
- Extensibility patterns (or lack thereof)
- Consistency with existing architecture patterns

## Strategy profile agents

### Feasibility Analyst (FEAS)

**Focus**: Technical approach, effort estimates, dependency availability.

**What it checks**:

- Are the proposed technologies available and mature?
- Are effort estimates realistic given the scope?
- Are external dependencies available and maintained?
- Are there hidden technical risks not addressed?
- Is the phasing/sequencing logical?

### Architecture Reviewer (ARCH)

**Focus**: Integration patterns, component boundaries, API contracts.

**What it checks**:

- Does the proposal fit the existing architecture?
- Are component boundaries well-defined?
- Are API contracts specified?
- Are integration points identified and addressed?
- Are failure modes documented?

### Security Analyst (SEC)

**Focus**: Security risks, missing mitigations, auth patterns.

**What it checks**:

- Are security implications identified?
- Are authentication and authorization patterns specified?
- Are data handling requirements addressed?
- Are threat mitigations proportional to risks?
- Does the proposal comply with platform security constraints?

### User Impact Analyst (USER)

**Focus**: Backward compatibility, migration burden, API usability.

**What it checks**:

- Does the proposal break existing user workflows?
- Is the migration path documented and reasonable?
- Are new APIs intuitive and consistent with existing patterns?
- Is the learning curve justified by the value?
- Are documentation needs addressed?

### Scope & Completeness Analyst (SCOP)

**Focus**: Right-sizing, acceptance criteria quality, completeness gaps.

**What it checks**:

- Is the scope appropriate for the timeline?
- Are acceptance criteria specific, measurable, testable?
- Are edge cases and error scenarios covered?
- Are non-functional requirements addressed?
- Is the proposal complete (no missing sections)?

### Testability Analyst (TEST)

**Focus**: Test strategy gaps, verification coverage, AC testability.

**What it checks**:

- Can each acceptance criterion be verified by a test?
- Is the test strategy proportional to the risk?
- Are integration test requirements identified?
- Are performance/load test needs addressed?
- Are test data and environment requirements specified?

## Devil's Advocate

Both profiles include a devil's advocate agent used in single-specialist mode or as a self-challenge mechanism. The devil's advocate:

- Challenges each finding from Phase 1
- Discards findings that do not survive scrutiny
- Adjusts severity of partially valid findings
- Uses architecture context (when provided) to sharpen challenges
- Performs **weakest-link analysis**: for every finding, identifies the single weakest piece of evidence and attacks it directly
- Flags findings that rely on assumptions rather than traced code paths or cited strategy text
- Applies **survivorship framing**: retained findings are explicitly annotated with why they could not be refuted, strengthening the final report's credibility

The devil's advocate is not a specialist. It does not produce findings independently. It only challenges and strengthens existing ones.

## Prompt versioning

All agent prompts include version frontmatter with a content-based SHA-256 hash:

```yaml
---
version: "1.0"
content_hash: "2305fdeae..."
last_modified: "2026-04-15"
---
```

This enables reproducibility analysis: if findings changed between runs, you can determine whether the prompt or the code changed. Use `scripts/prompt_version.py verify <file>` to check if a prompt's content matches its declared hash, or `manifest <dir>` to generate a version manifest for all agents in a profile.

## Single-specialist mode

When only one specialist is selected (e.g., `--security` alone), the system adapts:

1. **Phase 1**: Self-refinement runs normally
2. **Phase 2**: Instead of cross-agent debate, the devil's advocate challenges the specialist's findings. The specialist responds once.
3. **Phase 3**: Findings the specialist maintained are included with a reduced-confidence flag. Withdrawn findings are dismissed.
4. **Phase 4**: Report includes a disclaimer noting findings were not cross-validated

This mode is available in both profiles. It provides a faster, cheaper review at the cost of reduced adversarial scrutiny.
