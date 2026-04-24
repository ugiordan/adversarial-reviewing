# Installation

Adversarial Review supports three installation paths with different security guarantees.

## Claude Code Plugin (recommended)

The full multi-agent architecture with enforced isolation requires Claude Code's Agent tool.

### Option A: Plugin commands

From inside a Claude Code session:

```bash
# One-time marketplace registration
/plugin marketplace add ugiordan/adversarial-reviewing

# Install globally (works in every project)
/plugin install adversarial-reviewing@ugiordan-adversarial-reviewing
```

After installation, start a new session. The skill activates automatically when relevant, or invoke directly via `/adversarial-reviewing`.

To update later:

```bash
/plugin update adversarial-reviewing
```

### Option B: Manual setup

If `/plugin` commands are unavailable:

1. Clone the marketplace repo:

    ```bash
    git clone https://github.com/ugiordan/adversarial-reviewing.git \
      $HOME/.claude/plugins/marketplaces/ugiordan-adversarial-reviewing
    ```

2. Copy the plugin to the cache:

    ```bash
    mkdir -p $HOME/.claude/plugins/cache/ugiordan-adversarial-reviewing/adversarial-review/1.0.0
    rsync -a $HOME/.claude/plugins/marketplaces/ugiordan-adversarial-reviewing/adversarial-review/ \
      $HOME/.claude/plugins/cache/ugiordan-adversarial-reviewing/adversarial-review/1.0.0/
    cp $HOME/.claude/plugins/marketplaces/ugiordan-adversarial-reviewing/.claude-plugin/marketplace.json \
      $HOME/.claude/plugins/cache/ugiordan-adversarial-reviewing/adversarial-review/1.0.0/.claude-plugin/
    ```

3. Add to `~/.claude/settings.json`:

    ```json
    {
      "enabledPlugins": {
        "adversarial-reviewing@ugiordan-adversarial-reviewing": true
      },
      "extraKnownMarketplaces": {
        "ugiordan-adversarial-reviewing": {
          "source": {
            "source": "git",
            "url": "https://github.com/ugiordan/adversarial-reviewing.git"
          }
        }
      }
    }
    ```

4. Add to `~/.claude/plugins/installed_plugins.json` (inside the `"plugins"` object):

    ```json
    "adversarial-reviewing@ugiordan-adversarial-reviewing": [
      {
        "scope": "user",
        "installPath": "<HOME>/.claude/plugins/cache/ugiordan-adversarial-reviewing/adversarial-review/1.0.0",
        "version": "1.0.0",
        "installedAt": "<ISO-8601-timestamp>",
        "lastUpdated": "<ISO-8601-timestamp>",
        "gitCommitSha": "<current-commit-sha>"
      }
    ]
    ```

## Cursor (degraded single-agent mode)

Cursor cannot spawn isolated sub-agents. The plugin adapts to a sequential persona mode where the agent role-plays each specialist one at a time. Both code and strategy profiles work, but without enforced isolation between specialists.

```bash
# Clone the repo
git clone https://github.com/ugiordan/adversarial-reviewing.git $HOME/.adversarial-review

# Copy rules to your project
mkdir -p .cursor/rules
cp $HOME/.adversarial-review/.cursor/rules/adversarial-reviewing.mdc .cursor/rules/
```

!!! note "Limitations in Cursor mode"
    - No enforcement boundary between specialist personas (isolation is advisory)
    - Mediated communication is advisory only (no programmatic sanitization)
    - Output validation depends entirely on agent compliance
    - Both profiles work, but findings may be less independent than in Claude Code's isolated multi-agent mode

## AGENTS.md (universal)

For any AI tool that supports AGENTS.md or similar context injection:

```bash
# Clone the repo
git clone https://github.com/ugiordan/adversarial-reviewing.git $HOME/.adversarial-review
```

Reference or inline `AGENTS.md` in your AI tool's context. Feature set depends on the tool's capabilities.

## Dependencies

- `bash` 4.0+
- `python3` (JSON serialization and unicode normalization)
- `git` (for `--diff` change-impact analysis)
- GitHub MCP tools (optional, for `--triage pr:<N>`)
- Claude Code Agent tool (for full multi-agent feature set)
- No npm or pip packages required
