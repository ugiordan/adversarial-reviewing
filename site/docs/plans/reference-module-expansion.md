# Reference Module Expansion Strategy

## Problem Statement

The adversarial-reviewing tool currently has an imbalanced reference module distribution. All 4 code profile modules are security-focused (OWASP Top 10, ASVS, K8s security, agentic AI security), leaving PERF, QUAL, CORR, and ARCH agents with zero domain-specific reference material. The strat profile has 3 organization-specific "all specialist" modules but nothing domain-specific per specialist.

This means non-security code agents and all strat agents rely entirely on LLM training knowledge, which is less precise and cannot be updated independently of model releases.

### Design Principle: Organization-Agnostic Builtins

All builtin reference modules must be organization-agnostic. They should codify industry standards, well-known patterns, and publicly documented best practices. Organization-specific content (team velocity data, component maps, internal auth patterns, compliance scope) belongs in project-level configuration loaded via `--context` or `.adversarial-review/references/`.

The existing strat profile modules (`rhoai-auth-patterns`, `rhoai-platform-constraints`, `productization-requirements`) violate this principle. They should be migrated to a project-level extension as part of this work.

## Scope

Add ~12 new builtin reference modules across both profiles, organized in 3 phases:

- **Phase 1** (4 modules): Highest-impact code profile modules
- **Phase 2** (4 modules): Remaining code profile modules
- **Phase 3** (4 modules): Strat profile modules

Additionally, migrate existing RHOAI-specific strat modules from builtins to a project-level extension.

Each module follows the existing frontmatter format (name, version, specialist, enabled, categories, description, source_url) and is placed in `profiles/<profile>/references/<specialist>/`.

### Directory Structure and Specialist Names

`discover_references.py` matches modules by scanning `references/<specialist>/` directories where `<specialist>` is the lowercase full name (not the prefix). The frontmatter `specialist` field must exactly match this name, or be `all`.

**Code profile directory mapping:**

| Module | Directory | `specialist` field |
|--------|-----------|-------------------|
| go-performance-patterns | `profiles/code/references/performance/` | `performance` |
| k8s-controller-performance | `profiles/code/references/performance/` | `performance` |
| database-query-patterns | `profiles/code/references/performance/` | `performance` |
| go-idioms | `profiles/code/references/quality/` | `quality` |
| concurrency-patterns | `profiles/code/references/correctness/` | `correctness` |
| error-handling-patterns | `profiles/code/references/correctness/` | `correctness` |
| operator-architecture | `profiles/code/references/architecture/` | `architecture` |

**Strat profile directory mapping:**

| Module | Directory | `specialist` field |
|--------|-----------|-------------------|
| estimation-anti-patterns | `profiles/strat/references/feasibility/` | `feasibility` |
| api-versioning-policy | `profiles/strat/references/all/` | `all` |
| testing-strategy-checklist | `profiles/strat/references/testability/` | `testability` |
| scope-sizing-heuristics | `profiles/strat/references/scope-completeness/` | `scope-completeness` |

New directories to create: `performance/`, `quality/`, `correctness/` (code profile); `feasibility/`, `testability/` (strat profile). The `architecture/`, `security/`, `scope-completeness/` directories already exist.

### Multi-Specialist Modules

`discover_references.py` does not support comma-separated `specialist` values. Modules that serve multiple specialists must use one of:
- `specialist: all` (loaded for every specialist, costs token budget across all)
- Duplication into each specialist's directory (content parity enforced by CI test)

`api-versioning-policy` uses `specialist: all` because both ARCH and USER need it, and it's useful context for other strat specialists too.

## Proposed Modules

### Phase 1: Code Profile (Highest Impact)

#### 1. operator-architecture (specialist: architecture)

Kubernetes operator architecture patterns:
- Reconciler design (idempotent, level-triggered)
- Status conditions (types, transitions, observedGeneration)
- Finalizers (when to use, cleanup patterns)
- Owner references (garbage collection, cross-namespace)
- Event recording (when to record, severity levels)
- Multi-resource coordination (ordering, dependencies)
- CRD versioning and conversion webhooks

**Rationale**: The operator pattern is the dominant architecture in Kubernetes-native projects. Without this module, ARCH reviews operator code using generic architecture heuristics and misses operator-specific concerns (e.g., missing finalizer for external resource cleanup).

**Source**: [Kubernetes Operator Best Practices](https://sdk.operatorframework.io/docs/best-practices/), [controller-runtime docs](https://pkg.go.dev/sigs.k8s.io/controller-runtime)

**Categories**: operator, reconciler, crd, finalizer, status-condition

#### 2. go-performance-patterns (specialist: performance)

Common Go performance pitfalls and patterns:
- String concatenation in loops (use strings.Builder)
- Slice preallocation (make with capacity)
- sync.Pool usage for high-allocation paths
- Context cancellation propagation
- Goroutine leak patterns (unbuffered channels, missing done signals)
- Map pre-sizing for known cardinality
- Interface boxing costs

**Rationale**: Go is a primary language for Kubernetes ecosystem projects. PERF currently flags generic algorithmic issues but misses Go-specific patterns that account for the majority of real performance regressions.

**Source**: [Effective Go](https://go.dev/doc/effective_go), [Go Performance Wiki](https://github.com/golang/go/wiki/Performance)

**Categories**: complexity, memory, goroutine, allocation, caching

#### 3. concurrency-patterns (specialist: correctness)

Go concurrency correctness patterns:
- Channel ownership rules (who closes, who reads)
- Mutex vs. channel decision matrix
- errgroup usage for parallel work with error propagation
- Context cancellation and deadline propagation
- sync.Once for lazy initialization
- Data race checklist (shared state, goroutine lifetime)
- Select statement patterns (timeout, cancellation, fan-in)

**Rationale**: Race conditions are CORR's primary domain. Go's concurrency model has specific patterns that training knowledge covers broadly but not with the precision needed for actionable findings.

**Source**: [Go Concurrency Patterns](https://go.dev/blog/pipelines), [Go Memory Model](https://go.dev/ref/mem)

**Categories**: concurrency, goroutine, channel, mutex, race-condition

#### 4. testing-strategy-checklist (specialist: testability)

Test strategy evaluation criteria:
- Test pyramid ratios by component type (unit/integration/e2e)
- Integration test requirements (what must be tested against real dependencies)
- Performance test thresholds (latency p99, throughput, resource limits)
- Test data management (fixtures, factories, seeding)
- CI pipeline integration (when tests run, parallelization)
- Acceptance criteria testability scoring (specific, measurable, automatable)

**Rationale**: TEST is the newest specialist and has no reference material. This module gives TEST concrete criteria for evaluating test strategies rather than relying on generic LLM knowledge.

**Source**: [Google Testing Blog](https://testing.googleblog.com/), [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

**Categories**: testing, coverage, integration-test, performance-test, acceptance-criteria

### Phase 2: Code Profile (Remaining)

#### 5. k8s-controller-performance (specialist: performance)

Kubernetes controller/operator performance patterns:
- Reconcile loop efficiency (avoid redundant API calls)
- Informer cache vs. API server calls (when to use each)
- Rate limiting and work queue configuration
- Watch vs. list tradeoffs for large resource sets
- Status update batching (avoid per-field updates)
- Shared informer factory reuse across controllers

**Rationale**: Controllers are the dominant code pattern in Kubernetes-native projects. Without this module, PERF treats controller code like generic Go code and misses controller-specific bottlenecks (e.g., list calls inside reconcile loops).

**Source**: [client-go workqueue](https://pkg.go.dev/k8s.io/client-go/util/workqueue), [controller-runtime caching](https://pkg.go.dev/sigs.k8s.io/controller-runtime/pkg/cache)

**Categories**: controller, reconciler, informer, apiserver, watch

#### 6. database-query-patterns (specialist: performance)

Database interaction patterns:
- N+1 query detection
- Missing index indicators (sequential scan on large tables)
- Connection pool sizing guidelines
- Batch vs. individual operations
- ORM pitfalls (lazy loading, eager loading decisions)
- Transaction scope minimization

**Rationale**: Services with database backends (registries, dashboards) benefit from DB-specific pattern detection. Language-agnostic module.

**Source**: [Use The Index, Luke](https://use-the-index-luke.com/), [SQL Performance Explained](https://sql-performance-explained.com/)

**Categories**: database, query, sql, connection-pool, orm

**Note**: Ship with `enabled: false` by default. Opt-in for projects that use databases heavily. This avoids consuming PERF's token budget on projects that are purely controller-based.

#### 7. go-idioms (specialist: quality)

Effective Go patterns and idioms:
- Error wrapping with fmt.Errorf %w
- Interface segregation (small interfaces, consumer-side definitions)
- Table-driven tests
- Functional options pattern
- Context propagation rules
- Package naming conventions
- Godoc comment format

**Rationale**: Without this module, QUAL sometimes flags idiomatic Go as a code smell (e.g., returning concrete types, small interfaces). This module helps QUAL distinguish intentional patterns from actual quality issues.

**Source**: [Effective Go](https://go.dev/doc/effective_go), [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments)

**Categories**: naming, patterns, error-handling, testing, interfaces

#### 8. error-handling-patterns (specialist: correctness)

Go error handling correctness:
- Error wrapping chains (when to wrap vs. when to create new)
- Sentinel errors vs. typed errors (when to use each)
- Error hierarchy design
- Panic recovery boundaries (only at goroutine roots and HTTP handlers)
- errors.Is vs. errors.As usage
- Error swallowing detection (empty catch, _ = err)

**Rationale**: Error propagation analysis is a major CORR focus area. Without specific patterns, CORR flags "error not checked" but misses subtler issues like incorrect wrapping that breaks errors.Is chains.

**Source**: [Go Blog: Working with Errors](https://go.dev/blog/go1.13-errors), [Go Error Handling](https://go.dev/doc/effective_go#errors)

**Categories**: error-handling, error-propagation, panic, sentinel-error

### Phase 3: Strat Profile

#### 9. estimation-anti-patterns (specialist: feasibility)

Effort estimation anti-patterns and heuristics:
- Common underestimation patterns (testing, documentation, CI/CD, migration)
- Risk-adjusted estimation (best/likely/worst case ranges)
- Complexity multipliers for integration work (cross-team, external API)
- Scope creep indicators that inflate estimates
- Planning fallacy mitigation techniques

**Rationale**: FEAS evaluates effort estimates without reference data. This module gives FEAS concrete anti-patterns to challenge unrealistic estimates.

**Source**: [Software Estimation: Demystifying the Black Art](https://www.construx.com/books/software-estimation-demystifying-the-black-art/) (McConnell), [COCOMO II](https://csse.usc.edu/tools/)

**Note**: This module contains only generic estimation heuristics from public literature. Organization-specific calibration data (team velocity, historical baselines) should be loaded via project-level `.adversarial-review/references/feasibility/` config.

**Categories**: estimation, effort, risk, timeline

#### 10. api-versioning-policy (specialist: all)

API lifecycle management:
- Backward compatibility rules (additive changes only for minor versions)
- Deprecation timeline requirements (minimum notice period)
- Breaking change definitions (behavioral, structural, semantic)
- Migration support expectations (dual-write period, compatibility shim)
- Versioning strategy (URL path vs. header vs. content negotiation)
- API stability levels (alpha/beta/stable graduation criteria)

**Rationale**: Both ARCH and USER evaluate API proposals. Shared reference material ensures consistent standards for what constitutes a breaking change or acceptable deprecation timeline.

**Source**: [Kubernetes API Conventions](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md), [Semantic Versioning](https://semver.org/)

**Categories**: api, versioning, deprecation, backward-compatibility, migration

#### 11. scope-sizing-heuristics (specialist: scope-completeness)

Scope evaluation reference:
- Epic vs. story vs. task sizing guidelines
- Acceptance criteria quality rubric (specific, measurable, testable, achievable)
- Definition of done templates by work type
- Scope creep indicators (vague deliverables, open-ended timelines)
- Right-sizing signals (can it ship independently? is it demoable?)
- Decomposition patterns (vertical slicing vs. horizontal layering)

**Rationale**: SCOP evaluates scope quality but lacks concrete reference for what "well-scoped" looks like. This module provides scoring rubrics and heuristics.

**Source**: [Agile Estimating and Planning](https://www.mountaingoatsoftware.com/books/agile-estimating-and-planning) (Cohn), [INVEST criteria](https://xp123.com/articles/invest-in-good-stories-and-smart-tasks/)

**Categories**: scope, acceptance-criteria, sizing, decomposition, definition-of-done

#### 12. user-migration-patterns (specialist: all)

User-facing change management:
- Breaking change communication templates
- Migration guide requirements (step-by-step, rollback, verification)
- Backward compatibility testing checklist
- Deprecation notice patterns (timeline, alternatives, support commitment)
- API client impact assessment (SDK updates, breaking type changes)
- User documentation update requirements

**Rationale**: USER evaluates migration burden without reference for what's standard. This module provides concrete patterns for evaluating whether a strategy adequately addresses user impact. Useful for all strat specialists as context.

**Source**: [Kubernetes Deprecation Policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/), [API Evolution](https://cloud.google.com/apis/design/compatibility)

**Categories**: migration, backward-compatibility, deprecation, user-impact, documentation

### Removed from Original Proposal

The following modules from the original brainstorm were removed based on adversarial review findings:

| Module | Reason for Removal |
|--------|-------------------|
| **security-compliance-checklist** | Compliance content (FedRAMP, SOC 2) requires specialized expertise to author accurately. Incorrect control mappings are worse than none. Also org-specific: not all deployments target regulated environments. Deferred until a compliance SME can author and own it. |
| **rhoai-component-map** | Organization-specific content (team ownership, internal APIs, tech debt). Volatile data with no sustainable maintenance plan. Users who need component context should load it via `--context`. |
| **estimation-heuristics** (velocity data) | Replaced with `estimation-anti-patterns` (generic). Org-specific velocity/calibration data belongs in project-level config. |

### Existing RHOAI Modules: Migration Plan

The 3 existing strat `all/` modules are RHOAI-specific and should be migrated out of builtins:

| Module | Current Location | Target |
|--------|-----------------|--------|
| `rhoai-auth-patterns` | `profiles/strat/references/all/` | Project-level: `.adversarial-review/references/all/` |
| `rhoai-platform-constraints` | `profiles/strat/references/all/` | Project-level: `.adversarial-review/references/all/` |
| `productization-requirements` | `profiles/strat/references/all/` | Project-level: `.adversarial-review/references/all/` |

**Migration steps:**
1. Move modules to a new `examples/rhoai-references/` directory in the repo
2. Add documentation explaining how to install project-level references
3. Set `enabled: false` in the builtin copies (keep for backward compat during transition)
4. Remove builtin copies in the next minor version

## Implementation Plan

### Phase 1: Core Code Modules (4 modules)

**Modules**: operator-architecture, go-performance-patterns, concurrency-patterns, testing-strategy-checklist

**Prerequisite**: Create new specialist directories (`performance/`, `quality/`, `correctness/` under code profile; `feasibility/`, `testability/` under strat profile).

**Steps:**
1. Create directory structure
2. Write 4 modules with valid frontmatter
3. Run `discover_references.py <specialist> --builtin-dir profiles/code/references` for each and verify discovery
4. Run token count check: `discover_references.py --list-all --token-count --budget-check 350000`
5. Add test fixtures per module (known-good input + expected behavior)
6. Run adversarial-reviewing on a sample Go controller file, compare findings with/without modules

**Acceptance criteria (Phase 1):**
1. Each module has valid YAML frontmatter
2. Each module is discovered by `discover_references.py` for its target specialist
3. Each module is under 2000 tokens (verified by `--token-count`)
4. No budget warnings triggered on default 350K budget
5. Each module contains at least 5 concrete patterns with code examples or decision matrices
6. Before/after test: at least one finding references module content on sample input

### Phase 2: Remaining Code Modules (4 modules)

**Modules**: k8s-controller-performance, database-query-patterns (enabled: false), go-idioms, error-handling-patterns

**Steps**: Same as Phase 1. database-query-patterns ships disabled by default.

**Acceptance criteria**: Same as Phase 1, plus:
7. `database-query-patterns` has `enabled: false` in frontmatter and is only loaded when overridden

### Phase 3: Strat Modules + RHOAI Migration (4 modules + migration)

**Modules**: estimation-anti-patterns, api-versioning-policy, scope-sizing-heuristics, user-migration-patterns

**Migration**: Move RHOAI-specific modules to `examples/rhoai-references/`

**Steps**: Same as Phase 1, plus migration steps above.

**Acceptance criteria**: Same as Phase 1, plus:
7. RHOAI-specific modules no longer load by default for new installations
8. `examples/rhoai-references/` includes installation instructions

### Token Budget Analysis

Per-specialist token load at 1500 tokens/module (calibrated from existing modules averaging 750-1150 tokens):

**Code profile:**

| Specialist | Dedicated Modules | `all` Modules | Est. Total | % of 350K |
|-----------|-------------------|---------------|------------|-----------|
| SEC | 0 new (4 existing ~3262) | 0 | ~3,262 | 0.9% |
| PERF | 3 (go-perf, k8s-ctrl, db-query*) | 0 | ~3,000-4,500 | 0.9-1.3% |
| QUAL | 1 (go-idioms) | 0 | ~1,500 | 0.4% |
| CORR | 2 (concurrency, error-handling) | 0 | ~3,000 | 0.9% |
| ARCH | 1 (operator-arch) | 0 | ~1,500 | 0.4% |

*db-query is `enabled: false` by default, so PERF typically gets 2 modules (~3,000 tokens)

**Strat profile:**

| Specialist | Dedicated Modules | `all` Modules | Est. Total | % of 350K |
|-----------|-------------------|---------------|------------|-----------|
| FEAS | 1 (estimation-anti-patterns) | 2 (api-versioning, user-migration) | ~4,500 | 1.3% |
| ARCH | 0 | 2 | ~3,000 | 0.9% |
| SEC | 0 | 2 | ~3,000 | 0.9% |
| USER | 0 | 2 | ~3,000 | 0.9% |
| SCOP | 1 (scope-sizing) | 2 | ~4,500 | 1.3% |
| TEST | 1 (testing-strategy) | 2 | ~4,500 | 1.3% |

All specialists well under the 3% per-specialist threshold (10,500 tokens). Total new builtin reference content: ~18K tokens, under the 10% total threshold (35,000 tokens). Per-module delimiter wrapping overhead: ~200 tokens/module x 12 = ~2,400 tokens additional.

### Language Considerations

All code profile modules are Go/Kubernetes-specific. This is intentional for Phase 1-2 (Go is the dominant language in the Kubernetes ecosystem). Future phases may add language-specific modules for Python, TypeScript, etc.

A `language` frontmatter field is not implemented yet. For now, agents are expected to recognize when Go-specific patterns don't apply to non-Go code. This is a known limitation documented in the module descriptions.

## Verification

### Per-phase verification:
1. `discover_references.py <specialist> --builtin-dir profiles/<profile>/references` returns expected modules
2. `discover_references.py --list-all --token-count --budget-check 350000` emits no warnings
3. Each module under 2000 tokens
4. Before/after review comparison on sample input shows module content referenced in findings

### CI integration tests:
- Add test cases to `tests/test-discover-references.sh` for new specialist directories
- Add per-module token size assertion
- Add content parity test for any duplicated modules
- Add authoring-time linting: run injection pattern detection on all reference modules

### What "improved review quality" means:
- **True positive gain**: at least one new finding per module that references module-specific content on a curated test input
- **False positive check**: no spurious findings on known-good test inputs when module is enabled
- **Budget compliance**: no warning thresholds exceeded with all modules enabled

## Appendix: Module Opt-Out Mechanisms

Users who don't need specific modules can disable them through the existing layer system:

1. **Project-level override**: Create `.adversarial-review/references/<specialist>/<module-name>.md` with `enabled: false`
2. **User-level override**: Create `~/.adversarial-review/references/<specialist>/<module-name>.md` with `enabled: false`

A simpler `--exclude-references <pattern>` CLI flag is a potential future enhancement but is not in scope for this work.
