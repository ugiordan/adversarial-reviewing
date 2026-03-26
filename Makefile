SKILL_DIR := adversarial-review/skills/adversarial-review

.PHONY: test lint install help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

test: ## Run all tests
	@bash $(SKILL_DIR)/tests/run-all-tests.sh

lint: ## Run ShellCheck on all scripts
	@shellcheck -x -e SC2329 -e SC1091 $(SKILL_DIR)/scripts/*.sh
	@shellcheck -x -e SC1091 $(SKILL_DIR)/tests/test-*.sh $(SKILL_DIR)/tests/run-all-tests.sh
	@echo "ShellCheck passed."

install: ## Install plugin to Claude Code cache
	@mkdir -p $(HOME)/.claude/plugins/cache/ugiordan-adversarial-review/.claude-plugin
	@rsync -a adversarial-review/ $(HOME)/.claude/plugins/cache/ugiordan-adversarial-review/
	@cp .claude-plugin/marketplace.json $(HOME)/.claude/plugins/cache/ugiordan-adversarial-review/.claude-plugin/
	@echo "Installed to ~/.claude/plugins/cache/ugiordan-adversarial-review/"
