# scripts/orchestrator/tests/test_config.py
import json
import pytest
from orchestrator.config import (
    parse_args, resolve_config, read_profile_config, _parse_config_yml,
    DEFAULT_BUDGET, QUICK_BUDGET, THOROUGH_BUDGET, SPECIALIST_FLAG_MAP,
)


class TestParseArgs:
    def test_minimal(self):
        args = parse_args(["--profile", "code", "/path/to/target"])
        assert args.profile == "code"
        assert args.target == "/path/to/target"

    def test_quick_preset(self):
        args = parse_args(["--quick", "/path"])
        assert args.quick is True

    def test_thorough_preset(self):
        args = parse_args(["--thorough", "/path"])
        assert args.thorough is True

    def test_no_budget(self):
        args = parse_args(["--no-budget", "/path"])
        assert args.no_budget is True


class TestReadProfileConfig:
    def test_reads_code_profile(self, code_profile_dir):
        cfg = read_profile_config(code_profile_dir)
        assert cfg["name"] == "code"
        assert len(cfg["agents"]) == 5
        assert cfg["agents"][0]["prefix"] == "SEC"
        assert cfg["quick_specialists"] == ["SEC", "CORR"]

    def test_missing_config_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_profile_config(str(tmp_path))


class TestResolveConfig:
    def test_default_profile(self, skill_dir):
        args = parse_args(["--profile", "code", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.profile == "code"
        assert len(cfg.agents) == 5
        assert cfg.max_iterations == 3
        # Budget comes from profiles/code/defaults.json which has budget: 0
        assert cfg.budget_limit == 0

    def test_quick_preset(self, skill_dir):
        args = parse_args(["--quick", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert [a.prefix for a in cfg.agents] == ["SEC", "CORR"]
        assert cfg.max_iterations == 2
        assert cfg.budget_limit == QUICK_BUDGET

    def test_security_only(self, skill_dir):
        args = parse_args(["--security", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert [a.prefix for a in cfg.agents] == ["SEC"]

    def test_thorough_preset(self, skill_dir):
        args = parse_args(["--thorough", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert len(cfg.agents) == 5  # all agents
        assert cfg.max_iterations == 5
        assert cfg.budget_limit == THOROUGH_BUDGET

    def test_no_budget_flag(self, skill_dir):
        args = parse_args(["--no-budget", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.budget_limit == 0
        assert cfg.flags.get("no_budget") is True

    def test_flags_captured(self, skill_dir):
        args = parse_args(["--save", "--delta", "--normalize", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.flags.get("save") is True
        assert cfg.flags.get("delta") is True
        assert cfg.flags.get("normalize") is True

    def test_context_flag(self, skill_dir):
        args = parse_args(["--context", "arch=path1", "--context", "docs=path2", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.flags.get("context") == ["arch=path1", "docs=path2"]

    def test_fix_flag_passes_through(self, skill_dir):
        args = parse_args(["--fix", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.flags.get("fix") is True

    def test_budget_override(self, skill_dir):
        args = parse_args(["--budget", "500000", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.budget_limit == 500000

    def test_specialist_flag_security(self, skill_dir):
        args = parse_args(["--security", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert [a.prefix for a in cfg.agents] == ["SEC"]
        assert cfg.specialist_flags == ["security"]

    def test_specialist_flags_combined(self, skill_dir):
        args = parse_args(["--security", "--performance", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        prefixes = sorted(a.prefix for a in cfg.agents)
        assert prefixes == ["PERF", "SEC"]

    def test_specialist_with_quick(self, skill_dir):
        args = parse_args(["--quick", "--security", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert [a.prefix for a in cfg.agents] == ["SEC"]
        assert cfg.max_iterations == 2
        assert cfg.budget_limit == QUICK_BUDGET

    def test_topic_flag(self, skill_dir):
        args = parse_args(["--topic", "my-topic", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.topic == "my-topic"

    def test_new_flags_captured(self, skill_dir):
        args = parse_args([
            "--force", "--strict-scope", "--gap-analysis",
            "--list-references", "--update-references",
            "/tmp/target",
        ])
        cfg = resolve_config(args, skill_dir)
        assert cfg.flags.get("force") is True
        assert cfg.flags.get("strict_scope") is True
        assert cfg.flags.get("gap_analysis") is True
        assert cfg.flags.get("list_references") is True
        assert cfg.flags.get("update_references") is True

    def test_range_and_triage_flags(self, skill_dir):
        args = parse_args(["--range", "abc..def", "--triage", "coderabbit", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.flags.get("range") == "abc..def"
        assert cfg.flags.get("triage") == "coderabbit"

    def test_arch_context_flag(self, skill_dir):
        args = parse_args(["--profile", "strat", "--arch-context", "repo@main", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        assert cfg.flags.get("arch_context") == "repo@main"


class TestParseConfigYml:
    def test_scalar_values(self):
        content = "name: code\nversion: 1\nenabled: true\n"
        result = _parse_config_yml(content)
        assert result["name"] == "code"
        assert result["version"] == "1"
        assert result["enabled"] is True

    def test_false_boolean(self):
        result = _parse_config_yml("debug: false\n")
        assert result["debug"] is False

    def test_inline_list(self):
        result = _parse_config_yml("agents: [SEC, CORR, QUAL]\n")
        assert result["agents"] == ["SEC", "CORR", "QUAL"]

    def test_multiline_list(self):
        content = "items:\n  - alpha\n  - beta\n  - gamma\n"
        result = _parse_config_yml(content)
        assert result["items"] == ["alpha", "beta", "gamma"]

    def test_list_of_dicts(self):
        content = (
            "agents:\n"
            "  - prefix: SEC\n"
            "    file: security-auditor.md\n"
            "  - prefix: CORR\n"
            "    file: correctness-verifier.md\n"
        )
        result = _parse_config_yml(content)
        assert len(result["agents"]) == 2
        assert result["agents"][0]["prefix"] == "SEC"
        assert result["agents"][0]["file"] == "security-auditor.md"
        assert result["agents"][1]["prefix"] == "CORR"

    def test_quoted_values_unquoted(self):
        content = 'name: "my-profile"\nversion: \'1.0\'\n'
        result = _parse_config_yml(content)
        assert result["name"] == "my-profile"
        assert result["version"] == "1.0"

    def test_comments_ignored(self):
        content = "# comment\nname: code\n# another comment\n"
        result = _parse_config_yml(content)
        assert result["name"] == "code"
        assert len(result) == 1

    def test_empty_content(self):
        assert _parse_config_yml("") == {}
        assert _parse_config_yml("  \n\n") == {}

    def test_nested_dict(self):
        content = "templates:\n  finding: finding-template.md\n  report: report-template.md\n"
        result = _parse_config_yml(content)
        assert result["templates"]["finding"] == "finding-template.md"
        assert result["templates"]["report"] == "report-template.md"

    def test_all_keyword(self):
        result = _parse_config_yml("scope: all\n")
        assert result["scope"] == "all"

    def test_empty_list(self):
        content = "agents:\nnext_key: value\n"
        result = _parse_config_yml(content)
        assert result["agents"] == []
        assert result["next_key"] == "value"

    def test_inline_list_in_dict_item(self):
        content = (
            "agents:\n"
            "  - prefix: SEC\n"
            "    tools: [Read, Grep]\n"
            "    maxTurns: 15\n"
        )
        result = _parse_config_yml(content)
        assert result["agents"][0]["tools"] == ["Read", "Grep"]
        assert result["agents"][0]["maxTurns"] == "15"


class TestAgentControlFields:
    def test_reads_tools_from_config(self, skill_dir):
        args = parse_args(["--profile", "code", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        sec = next(a for a in cfg.agents if a.prefix == "SEC")
        assert sec.tools == ["Read"]
        assert sec.effort == "high"
        assert sec.max_turns == 20

    def test_default_tools_when_missing(self, skill_dir):
        args = parse_args(["--profile", "code", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        for agent in cfg.agents:
            assert "Read" in agent.tools
            assert agent.effort in ("low", "medium", "high", "xhigh", "max")
            assert 1 <= agent.max_turns <= 50

    def test_quick_preset_preserves_control_fields(self, skill_dir):
        args = parse_args(["--quick", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        for agent in cfg.agents:
            assert agent.tools == ["Read"]
            assert agent.effort in ("medium", "high")

    def test_perf_agent_control_fields(self, skill_dir):
        args = parse_args(["--profile", "code", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        perf = next(a for a in cfg.agents if a.prefix == "PERF")
        assert perf.tools == ["Read"]
        assert perf.effort == "high"
        assert perf.max_turns == 12

    def test_corr_agent_control_fields(self, skill_dir):
        args = parse_args(["--profile", "code", "/tmp/target"])
        cfg = resolve_config(args, skill_dir)
        corr = next(a for a in cfg.agents if a.prefix == "CORR")
        assert corr.effort == "medium"
        assert corr.max_turns == 15


class TestFlagCompatibility:
    def test_delta_reuse_cache_incompatible(self):
        with pytest.raises(SystemExit):
            parse_args(["--delta", "--reuse-cache", "abc123", "/tmp/target"])

    def test_no_budget_and_budget_incompatible(self):
        with pytest.raises(SystemExit):
            parse_args(["--no-budget", "--budget", "100000", "/tmp/target"])

    def test_converge_requires_fix(self):
        with pytest.raises(SystemExit):
            parse_args(["--converge", "/tmp/target"])

    def test_converge_with_fix_ok(self):
        args = parse_args(["--converge", "--fix", "/tmp/target"])
        assert args.converge is True
        assert args.fix is True

    def test_dry_run_requires_fix(self):
        with pytest.raises(SystemExit):
            parse_args(["--dry-run", "/tmp/target"])

    def test_dry_run_with_fix_ok(self):
        args = parse_args(["--dry-run", "--fix", "/tmp/target"])
        assert args.dry_run is True

    def test_review_only_confirm_incompatible(self):
        with pytest.raises(SystemExit):
            parse_args(["--review-only", "--confirm", "/tmp/target"])

    def test_arch_context_code_profile_incompatible(self):
        # Default profile is code, --arch-context should fail
        with pytest.raises(SystemExit):
            parse_args(["--arch-context", "repo@main", "/tmp/target"])

    def test_principles_code_profile_incompatible(self):
        with pytest.raises(SystemExit):
            parse_args(["--principles", "be strict", "/tmp/target"])

    def test_quick_and_thorough_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            parse_args(["--quick", "--thorough", "/tmp/target"])

    def test_security_and_quick_combinable(self):
        # --security is a specialist flag, not a mode flag; can combine with --quick
        args = parse_args(["--security", "--quick", "/tmp/target"])
        assert args.security is True
        assert args.quick is True
