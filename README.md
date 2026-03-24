# Adversarial Review

Multi-agent adversarial code review with isolated specialists, programmatic validation, and consensus-based findings. This plugin orchestrates independent security, reliability, and performance specialists who debate findings through a structured protocol, ensuring only validated, high-confidence issues are surfaced.

## Installation

### Claude Code Plugin (Global)

Add the marketplace and install the plugin globally:

```bash
claude marketplace add --git https://github.com/ugiordan/adversarial-review.git
claude plugin add adversarial-review --scope user
```

Once installed, invoke via the skill:
```bash
claude skill adversarial-review [files...]
```

### Cursor

Clone the repository to `$HOME/.adversarial-review`:

```bash
git clone https://github.com/ugiordan/adversarial-review.git $HOME/.adversarial-review
```

Copy `.cursor/rules/adversarial-review.mdc` to your project's `.cursor/rules/` directory.

**Note:** Cursor runs in degraded single-agent mode. Agent isolation and mediated communication are not available.

### AGENTS.md

Clone the repository and reference or inline the `AGENTS.md` file in your AI tool's context:

```bash
git clone https://github.com/ugiordan/adversarial-review.git
```

Reference the `AGENTS.md` file as needed for your tool.

**Note:** Feature set depends on tool capabilities. Agent isolation and programmatic validation may not be available.

## Security Properties

| Property | Claude Code | Cursor | AGENTS.md |
|----------|-------------|--------|-----------|
| Agent isolation | Enforced | Not available | Depends on tool |
| Mediated communication | Enforced | Advisory | Advisory |
| Output validation | Enforced | Advisory | Advisory |

## Dependencies

- bash 4.0+
- python3
- Claude Code Agent tool (for full feature set)
- No npm or pip dependencies

## License

Apache-2.0
