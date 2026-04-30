import os
import pytest
from pathlib import Path
from orchestrator.prompt import _cache_navigation, _generate_compaction_content


class TestScopedNavigation:
    def test_only_shows_own_outputs(self, tmp_path):
        outputs = tmp_path / "outputs"
        outputs.mkdir()
        (outputs / "SEC-phase1-iter1.md").write_text("sec findings")
        (outputs / "CORR-phase1-iter1.md").write_text("corr findings")
        (outputs / "QUAL-phase1-iter1.md").write_text("qual findings")

        nav = _cache_navigation(str(tmp_path), "/src", agent_id="SEC")
        assert "SEC-phase1-iter1.md" in nav
        assert "CORR-phase1-iter1.md" not in nav
        assert "QUAL-phase1-iter1.md" not in nav

    def test_shows_all_own_iterations(self, tmp_path):
        outputs = tmp_path / "outputs"
        outputs.mkdir()
        (outputs / "SEC-phase1-iter1.md").write_text("iter1")
        (outputs / "SEC-phase1-iter2.md").write_text("iter2")
        (outputs / "SEC-challenge-iter1.md").write_text("challenge")

        nav = _cache_navigation(str(tmp_path), "/src", agent_id="SEC")
        assert "SEC-phase1-iter1.md" in nav
        assert "SEC-phase1-iter2.md" in nav
        assert "SEC-challenge-iter1.md" in nav

    def test_no_agent_id_shows_no_outputs(self, tmp_path):
        outputs = tmp_path / "outputs"
        outputs.mkdir()
        (outputs / "SEC-phase1-iter1.md").write_text("findings")

        nav = _cache_navigation(str(tmp_path), "/src")
        assert "SEC-phase1-iter1.md" not in nav


class TestCompactionContent:
    def test_generates_compact_constraints(self):
        content = _generate_compaction_content(
            agent_role="Find security vulnerabilities that matter in production.",
            delimiter_instructions="===START=== / ===END===",
            phase="self-refinement",
            iteration=2,
            target="/src/myproject",
        )
        assert "security vulnerabilities" in content
        assert "===START===" in content
        assert "self-refinement" in content
        assert len(content) < 3000

    def test_contains_key_constraints(self):
        content = _generate_compaction_content(
            agent_role="Test role",
            delimiter_instructions="delims",
            phase="challenge-round",
            iteration=1,
            target="/src",
        )
        assert "finding template" in content
        assert "counter-argument" in content
        assert "other reviewers" in content
        assert "untrusted input" in content
