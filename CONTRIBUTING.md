# Contributing to Adversarial Review

Thank you for considering contributing to Adversarial Review.

## Getting Started

1. Fork and clone the repository
2. Run the test suite to verify your setup:
   ```bash
   cd adversarial-review/skills/adversarial-review
   bash tests/run-all-tests.sh
   ```
3. Create a feature branch from `main`

## Development

### Requirements

- bash 4.0+
- python3 (for JSON serialization and unicode normalization)
- git
- [ShellCheck](https://www.shellcheck.net/) (for linting shell scripts)

### Project Structure

- `scripts/` — Shell scripts that handle all programmatic validation (security-critical)
- `agents/` — Specialist agent prompts
- `phases/` — Orchestration phase procedures
- `protocols/` — Internal protocol definitions
- `references/` — Reference modules for cross-checking
- `templates/` — Data exchange format templates
- `tests/` — Test scripts and fixtures

### Running Tests

```bash
cd adversarial-review/skills/adversarial-review
bash tests/run-all-tests.sh
```

All tests must pass before submitting a PR.

### Linting

```bash
shellcheck adversarial-review/skills/adversarial-review/scripts/*.sh
```

### Writing Tests

Tests use a lightweight bash testing framework in `tests/`. Each test file follows the pattern:

```bash
run_test "descriptive test name" '
    # setup
    # action
    # assertion using grep, diff, or exit codes
'
```

Add tests in the appropriate `test-*.sh` file, or create a new one and register it in `tests/run-all-tests.sh`.

## Submitting Changes

1. Ensure all tests pass
2. Ensure ShellCheck passes on any modified scripts
3. Write clear commit messages describing the "why"
4. Open a Pull Request against `main`

### What Makes a Good PR

- **Focused scope** — one logical change per PR
- **Tests included** — new features and bug fixes should have tests
- **Docs updated** — if your change affects user-facing behavior, update README.md, SKILL.md, or relevant phase/protocol docs
- **No unrelated changes** — avoid bundling cleanup with feature work

## Reporting Bugs

Open an issue on GitHub with:
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, bash version, python version)

## Security Vulnerabilities

See [SECURITY.md](SECURITY.md) for reporting security issues.

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 License.
