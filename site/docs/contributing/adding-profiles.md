# Adding Profiles

This guide covers creating a new review profile (e.g., a `docs` profile for documentation review or an `api` profile for API specification review).

## Profile components

A profile consists of:

1. **config.yml**: Agent definitions, presets, defaults
2. **Agent prompts**: One markdown file per specialist
3. **Templates**: Finding, challenge-response, and report templates
4. **References** (optional): Knowledge base modules
5. **Devil's advocate**: Challenge agent for single-specialist mode

## Step 1: Create the directory structure

```bash
mkdir -p profiles/myprofile/{agents,templates,references}
```

## Step 2: Write config.yml

```yaml
name: myprofile
description: Description of what this profile reviews

agents:
  - tag: SPEC1
    name: Specialist One
    file: specialist-one.md
    flag: --specialist-one
  - tag: SPEC2
    name: Specialist Two
    file: specialist-two.md
    flag: --specialist-two
  # Add more specialists as needed

quick_preset:
  agents: [SPEC1]
  iterations: 2
  budget: 150000

thorough_preset:
  agents: all
  iterations: 3
  budget: 800000

default:
  iterations: 2
  budget: 350000
```

## Step 3: Write agent prompts

Each agent prompt must include:

1. **Role definition**: What the specialist does
2. **Focus areas**: Specific things to check
3. **Inoculation instructions**: Anti-injection directives
4. **Finding template**: The exact output format
5. **Severity guidance**: What counts as Critical/Important/Minor
6. **Confidence guidance**: When to assign High/Medium/Low
7. **Self-refinement instructions**: How to verify findings before finalizing
8. **Evidence requirements**: What counts as good vs. bad evidence
9. **No findings output**: Exact string when nothing is found
10. **Context document safety**: How to handle `--context` input

Use an existing agent (e.g., `profiles/code/agents/security-auditor.md`) as a template.

## Step 4: Write templates

### Finding template

Define the exact format for findings. Must include at minimum:

- Finding ID (with specialist tag prefix)
- Specialist name
- Severity and confidence
- Evidence (with minimum length)
- Recommended fix

### Challenge response template

Format for Phase 2 challenges. Must include:

- Which finding is being challenged
- Challenge type (False Positive, Severity Inflation, etc.)
- Argument and evidence

### Report template

Structure for the Phase 4 output. Should include:

- Executive summary
- Findings by severity
- Agreement classifications
- Remediation roadmap (if applicable)

## Step 5: Add the devil's advocate

Create `agents/devils-advocate.md` for your profile. The devil's advocate:

- Does not produce findings
- Challenges existing findings from Phase 1
- Must include architecture context handling (if your profile supports `--context`)

## Step 6: Wire it up

1. Update `profile-config.sh` to recognize the new profile
2. Update SKILL.md to accept the new `--profile` flag value
3. Update `validate-output.sh` to validate your finding format
4. Add specialist flags to the flag parser

## Step 7: Add reference modules (optional)

```bash
mkdir -p profiles/myprofile/references/all/
```

Write modules with YAML frontmatter (name, description, specialist, version). See [Reference Modules](../guides/reference-modules.md).

## Step 8: Test

1. Run existing tests to make sure nothing broke: `bash tests/run-all-tests.sh`
2. Test the new profile end-to-end against sample documents
3. Verify validation catches malformed output from your specialists
