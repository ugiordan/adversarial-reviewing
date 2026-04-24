# Development Setup

## Prerequisites

- bash 4.0+
- python3
- git
- [ShellCheck](https://www.shellcheck.net/) (for linting)

## Clone the repo

```bash
git clone https://github.com/ugiordan/adversarial-reviewing.git
cd adversarial-reviewing
```

## Repository structure

```
adversarial-reviewing/
  .claude-plugin/           # Marketplace metadata
  .cursor/rules/            # Cursor IDE rules
  .github/workflows/        # CI (test.yml)
  adversarial-review/       # Plugin package
    .claude-plugin/
      plugin.json           # Plugin manifest
    commands/
      adversarial-reviewing.md # Command definition
    skills/adversarial-reviewing/
      SKILL.md              # Main orchestration procedure
      profiles/             # Code and strategy profiles
      phases/               # Phase procedures
      protocols/            # Operational protocols
      scripts/              # Validation and utility scripts
      tests/                # Test suite
      references/           # Knowledge base modules
      templates/            # Output templates (legacy)
  docs/                     # Documentation and specs
  AGENTS.md                 # Universal agent prompts
  README.md
  Makefile
```

## Running tests

```bash
cd adversarial-review/skills/adversarial-reviewing
bash tests/run-all-tests.sh
```

The test suite covers:

- Output validation (structure, injection detection)
- Triage validation
- Convergence detection
- Budget tracking
- Deduplication
- Reference module discovery
- Cache management
- Context fetching
- Diff and impact graph
- Comment parsing
- Guardrail enforcement
- Single-agent pipeline integration

## Linting

ShellCheck runs in CI. To run locally:

```bash
shellcheck scripts/*.sh tests/test-*.sh
```

Suppressed checks: SC2329, SC2317 (unreachable code in test functions), SC1091 (source paths).

## CI pipeline

The `.github/workflows/test.yml` workflow:

1. **Test job**: Runs `tests/run-all-tests.sh`, asserts 0 failures
2. **ShellCheck job**: Lints all bash scripts

## Local testing with Claude Code

To test changes locally before pushing:

1. Build and install the plugin from your working copy:

    ```bash
    rsync -a adversarial-review/ \
      $HOME/.claude/plugins/cache/ugiordan-adversarial-reviewing/adversarial-review/1.0.0/
    ```

2. Start a new Claude Code session
3. Run `/adversarial-reviewing` against test code

## Writing tests

Test scripts follow the pattern:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../scripts/some-script.sh"

test_some_behavior() {
  local result
  result=$(some_function "input")
  [[ "$result" == "expected" ]] || { echo "FAIL: test_some_behavior"; return 1; }
  echo "PASS: test_some_behavior"
}

test_some_behavior
```

Add new test files to `tests/` and they'll be picked up by `run-all-tests.sh` automatically.
