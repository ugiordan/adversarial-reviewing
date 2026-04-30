import os
import pytest
from pathlib import Path
from orchestrator.prompt import compose_prompt, prepare_dispatch_directory


class TestComposePrompt:
    def test_base_composition(self, code_profile_dir, tmp_cache_dir):
        prompt = compose_prompt(
            agent_prefix="SEC",
            agent_file="security-auditor.md",
            profile_dir=code_profile_dir,
            cache_dir=str(tmp_cache_dir),
            source_root="/tmp/source",
            phase="self-refinement",
            iteration=1,
            flags={},
        )
        assert "Security Auditor" in prompt or "security" in prompt.lower()
        assert str(tmp_cache_dir) in prompt

    def test_includes_finding_template(self, code_profile_dir, tmp_cache_dir):
        prompt = compose_prompt(
            agent_prefix="SEC",
            agent_file="security-auditor.md",
            profile_dir=code_profile_dir,
            cache_dir=str(tmp_cache_dir),
            source_root="/tmp/source",
            phase="self-refinement",
            iteration=1,
            flags={},
        )
        assert "Finding ID" in prompt or "finding" in prompt.lower()

    def test_no_delimiter_in_prompt(self, code_profile_dir, tmp_cache_dir):
        prompt = compose_prompt(
            agent_prefix="SEC",
            agent_file="security-auditor.md",
            profile_dir=code_profile_dir,
            cache_dir=str(tmp_cache_dir),
            source_root="/tmp/source",
            phase="self-refinement",
            iteration=1,
            flags={},
        )
        assert "===REVIEW_TARGET" not in prompt
        assert "BEGIN_DELIMITER" not in prompt


class TestPrepareDispatchDirectory:
    def test_creates_all_required_files(self, tmp_path):
        dispatch_path = prepare_dispatch_directory(
            cache_dir=str(tmp_path),
            agent_id="SEC",
            phase="self-refinement",
            iteration=1,
            agent_instructions="# Security Auditor\nFind vulnerabilities.",
            common_instructions="# Common\nUse finding template.",
            finding_template="Finding ID: ...",
            source_files="# Source\npackage main",
        )
        dp = Path(dispatch_path)
        assert (dp / "dispatch-config.yaml").exists()
        assert (dp / "agent-instructions.md").exists()
        assert (dp / "common-instructions.md").exists()
        assert (dp / "finding-template.md").exists()
        assert (dp / "source-files.md").exists()
        assert (dp / "output.md").exists()
        assert not (dp / "prior-findings.md").exists()

    def test_dispatch_config_content(self, tmp_path):
        import yaml
        dispatch_path = prepare_dispatch_directory(
            cache_dir=str(tmp_path), agent_id="SEC",
            phase="self-refinement", iteration=1,
            agent_instructions="t", common_instructions="t",
            finding_template="t", source_files="t",
        )
        config = yaml.safe_load((Path(dispatch_path) / "dispatch-config.yaml").read_text())
        assert config["dispatch_version"] == "3.0"
        assert config["agent_id"] == "SEC"
        assert config["phase"] == "self-refinement"
        assert config["iteration"] == 1

    def test_prior_findings_written_when_provided(self, tmp_path):
        dispatch_path = prepare_dispatch_directory(
            cache_dir=str(tmp_path), agent_id="SEC",
            phase="self-refinement", iteration=2,
            agent_instructions="t", common_instructions="t",
            finding_template="t", source_files="t",
            prior_findings="# Prior\nSEC-001: found something",
        )
        assert (Path(dispatch_path) / "prior-findings.md").exists()
        content = (Path(dispatch_path) / "prior-findings.md").read_text()
        assert "SEC-001" in content

    def test_dispatch_path_format(self, tmp_path):
        dispatch_path = prepare_dispatch_directory(
            cache_dir=str(tmp_path), agent_id="PERF",
            phase="challenge", iteration=3,
            agent_instructions="t", common_instructions="t",
            finding_template="t", source_files="t",
        )
        assert "PERF-challenge-iter3" in dispatch_path
