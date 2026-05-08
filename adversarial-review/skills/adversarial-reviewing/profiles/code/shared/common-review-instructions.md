## Output Instructions

Read dispatch-config.yaml to find your output_path. Write ALL your findings
to that file using the Write tool. Use the finding template format. If you
produce no findings, write "NO_FINDINGS_REPORTED" to the output file.

You MUST write your output file. Do not rely on anyone else to save your work.

## Severity Classification

Use these definitions precisely. Do not default to "Important" for everything.

- **Critical**: Actively exploitable by external/unauthenticated attackers.
  Direct path to privilege escalation, data breach, or RCE. Requires
  immediate fix. Example: operator precedence bug that bypasses auth checks
  for all authenticated users.
- **Important**: Exploitable by authenticated users or requires specific
  conditions. Weakens security posture significantly but not directly
  exploitable without prerequisites. Example: wildcard RBAC verbs granting
  implicit escalate/bind, missing input validation on user-facing fields.
- **Minor**: Defense-in-depth gaps, code quality issues with security
  implications, or issues requiring privileged access to exploit. Example:
  unpinned container images, annotation typos, missing file permissions,
  OAuth auto-grant on internal services.

When in doubt between two levels, pick the LOWER one. False upgrades
(marking Minor as Important) waste triage time. False downgrades get
caught in challenge rounds.

## Discovery Phase

**Step 1: Read the code index** in source-files.md. It contains real symbol
definitions from static analysis (file:line locations). You can cite these
directly as evidence for findings.

**Step 2: Read project-map.md** for project structure and security-relevant
files highlighted by naming convention.

**Step 3: Investigate.** For security-relevant symbols in the index, use Read
to examine the full function body. The index shows WHERE things are defined;
you need to read the actual code to assess WHETHER there's a vulnerability.

**Step 4: Search beyond the index.** Use Grep to find patterns the index
doesn't cover (string literals, config values, hardcoded secrets, YAML
manifests, Dockerfiles).

**Step 5: Coverage check.** Verify you examined every security-relevant file
in project-map.md. Check for unexplored directories.

**Evidence rules:**
- Index entries ARE valid evidence (static analysis output)
- If the index doesn't cover your concern, Read the actual file
- If you can't find evidence anywhere, say "suspected but unverified"
- NEVER fabricate file paths, line numbers, or code

Pay special attention to API type definition files (*_types.go, *_types.ts).
These define the input validation boundary.

## Self-Refinement Instructions (MANDATORY)

After producing your initial findings:

1. Count how many detection patterns from your agent instructions you actually
   grepped for. If fewer than 80%, go back and grep the remainder.
2. List the directories in the source root you have NOT examined. Use Glob
   to enumerate them. Read at least the top-level files in each unexplored
   directory.
3. Re-read your Pre-Submission Verification section. Execute every grep
   listed there that you haven't already run.
4. Review your findings: What did you miss? What's a false positive?
5. Only then submit your findings.

## Evidence Requirements

Every finding MUST be backed by concrete code evidence:
- Cite the specific file, function, and line where the issue occurs
- For behavioral claims ("X writes to Y", "Z is called without validation"),
  trace the actual execution path through the code and cite each step
- If you cannot find concrete code evidence for a concern, it is
  ASSUMPTION-BASED. You must either:
  (a) Investigate further until you find evidence, or
  (b) Withdraw the finding

Do NOT report findings based on what code "might" do, what libraries
"typically" do, or what "could" happen in theory. Only report what the
actual code demonstrably does.

## Unverified External References

When your analysis depends on definitions outside the reviewed scope (SCCs, CRDs, external manifests, controllers in other repos, configs referenced by path but not present in cache):

1. **Flag the dependency**: State explicitly: "This finding depends on [resource] defined outside the reviewed scope."
2. **Do not infer behavior**: If you haven't read the actual definition, state what the reviewed code assumes about the resource. Note the assumption is unverified. Do not present inferences about external resources as established facts.
3. **Set Confidence: Low** for findings whose severity depends on the behavior of an unverified external resource.

Common signals of external dependencies:
- RBAC rules with `resourceNames:` referencing objects not in the cache
- File paths pointing outside the reviewed directory
- Imports/dependencies from other repositories
- References to cluster-scoped resources (SCCs, NetworkPolicies, ClusterRoles) whose definitions you haven't read
- Kustomize overlays or bases referencing external directories

A finding built on "external resource X does Y" when you haven't read X's definition is assumption-based. Apply the Evidence Requirements rules: investigate further or withdraw.

### Kubernetes Deployment Chain Awareness

When reviewing Kubernetes manifests (NetworkPolicy, RBAC, Deployments, Services):

- **NetworkPolicies are additive.** Multiple policies selecting the same pods produce a union of allowed traffic. A component-level policy that omits port 8080 does NOT block port 8080 if another policy in the namespace (deployed by an operator, platform controller, or Helm chart) allows it. Never conclude "port X is blocked" from a single policy without verifying no other policies apply.
- **Operator-managed components inherit the operator's security posture.** If the component is deployed by an operator, the operator may deploy namespace-level resources (NetworkPolicy, ResourceQuota, RBAC) that override or supplement the component's own manifests. Signals: `app.kubernetes.io/managed-by` labels, CRD references, Kustomize overlays referencing parent directories.
- **Never conclude a vulnerability is mitigated by a control you cannot inspect.** If your analysis says "this is protected by NetworkPolicy" or "RBAC prevents this", verify the protective control is within the reviewed code. If not, the mitigation is unverified. Set Confidence: Low and note what you could and could not verify.

## No Findings

If you find no issues, your output must contain exactly: NO_FINDINGS_REPORTED

## Diff-Aware Review Instructions (active when --diff is used)

You are reviewing a CODE CHANGE, not static code. Your primary task is to
identify issues INTRODUCED or EXPOSED by this change.

Focus on:
1. **Side effects of the diff**: What behavior changes when this code runs?
   What state mutations are skipped, reordered, or altered?
2. **Caller impact**: Review the CHANGE IMPACT GRAPH. For each caller of a
   changed function, ask: does the caller still work correctly with the new
   behavior?
3. **Early returns and guard clauses**: If the diff adds an early return,
   what code after it is now conditionally skipped? Is that skip always safe?
4. **Implicit contracts**: Does the change violate any implicit contract
   that callers depend on?
5. **Missing propagation**: If the change adds new behavior, do all callers
   handle it?

Do NOT limit your review to the changed lines. The diff tells you WHERE to
look; the impact graph tells you WHAT ELSE to check.

## Triage Mode Instructions (active when --triage is used)

You are EVALUATING external review comments, not performing an independent review.

For each external comment:
1. Read the comment carefully
2. Read the referenced code (and surrounding context)
3. Determine: is this comment technically correct?
4. Assign a verdict: Fix, No-Fix, or Investigate
5. Assign a confidence level (High / Medium / Low)
6. Explain your reasoning with code evidence

IMPORTANT: Do not rubber-stamp external comments. Apply the same adversarial
rigor you would to your own findings.

You may also raise NEW findings if you discover issues while evaluating
comments that the external reviewer missed. Use the standard finding template
with Source: Triage-Discovery.
