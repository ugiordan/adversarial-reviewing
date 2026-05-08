import os
import pytest
from pathlib import Path
from unittest.mock import patch

from orchestrator.hotspots import (
    load_hotspot_patterns, compute_hotspots, _parse_patterns_fallback,
)


@pytest.fixture
def profile_dir(tmp_path):
    d = tmp_path / "profiles" / "code"
    d.mkdir(parents=True)
    return str(d)


@pytest.fixture
def source_dir(tmp_path):
    d = tmp_path / "source"
    d.mkdir()
    (d / "main.go").write_text('package main\nfunc main() {\n\tIsCA := true\n}\n')
    (d / "auth.go").write_text('func check() {\n\tif system:authenticated {\n\t}\n}\n')
    sub = d / "pkg"
    sub.mkdir()
    (sub / "cert.go").write_text('cert.IsCA = true\nInsecureSkipVerify: false\n')
    return str(d)


class TestLoadHotspotPatterns:
    def test_loads_real_profile(self):
        profile = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "profiles", "code",
        )
        if not os.path.isdir(profile):
            pytest.skip("profiles/code not found")
        patterns = load_hotspot_patterns(profile)
        assert "SEC" in patterns
        assert len(patterns["SEC"]) >= 5
        assert all("pattern" in p for p in patterns["SEC"])

    def test_missing_file_returns_empty(self, profile_dir):
        assert load_hotspot_patterns(profile_dir) == {}

    def test_parses_yaml_structure(self, profile_dir):
        Path(os.path.join(profile_dir, "hotspot-patterns.yaml")).write_text(
            "SEC:\n  - pattern: IsCA\n    description: CA check\n"
            "CORR:\n  - pattern: panic\n    description: panics\n"
        )
        patterns = load_hotspot_patterns(profile_dir)
        assert "SEC" in patterns
        assert "CORR" in patterns
        assert patterns["SEC"][0]["pattern"] == "IsCA"


class TestParseFallback:
    def test_parses_without_yaml(self, tmp_path):
        f = tmp_path / "patterns.yaml"
        f.write_text(
            "SEC:\n  - pattern: IsCA\n    description: CA check\n"
            "  - pattern: verbs\n    description: RBAC\n"
        )
        result = _parse_patterns_fallback(str(f))
        assert len(result["SEC"]) == 2
        assert result["SEC"][0]["pattern"] == "IsCA"


class TestComputeHotspots:
    def test_finds_matches(self, source_dir):
        patterns = [
            {"pattern": "IsCA", "description": "CA certificates"},
        ]
        result = compute_hotspots(source_dir, "SEC", patterns)
        assert "IsCA" in result
        assert "main.go" in result or "cert.go" in result

    def test_no_matches_returns_empty(self, source_dir):
        patterns = [
            {"pattern": "NONEXISTENT_PATTERN_XYZ", "description": "nothing"},
        ]
        result = compute_hotspots(source_dir, "SEC", patterns)
        assert result == ""

    def test_empty_patterns_returns_empty(self, source_dir):
        assert compute_hotspots(source_dir, "SEC", []) == ""

    def test_missing_source_root_returns_empty(self):
        patterns = [{"pattern": "x", "description": "x"}]
        assert compute_hotspots("/nonexistent/path", "SEC", patterns) == ""

    def test_includes_priority_files_table(self, source_dir):
        patterns = [
            {"pattern": "IsCA", "description": "CA"},
            {"pattern": "system:authenticated", "description": "auth"},
        ]
        result = compute_hotspots(source_dir, "SEC", patterns)
        assert "Priority files" in result
        assert "Hits" in result

    def test_respects_max_results(self, tmp_path):
        d = tmp_path / "bigdir"
        d.mkdir()
        for i in range(100):
            (d / f"file{i}.go").write_text(f"match_me line {i}\n" * 5)
        patterns = [{"pattern": "match_me", "description": "test"}]
        result = compute_hotspots(str(d), "TEST", patterns, max_per_pattern=10)
        lines = [l for l in result.splitlines() if l.startswith("- `")]
        assert len(lines) <= 10


class TestLanguageDetection:
    def test_detect_go(self, tmp_path):
        from orchestrator.config import detect_language
        d = tmp_path / "repo"
        d.mkdir()
        for i in range(10):
            (d / f"file{i}.go").write_text("package main")
        assert detect_language(str(d)) == "go"

    def test_detect_python(self, tmp_path):
        from orchestrator.config import detect_language
        d = tmp_path / "repo"
        d.mkdir()
        for i in range(10):
            (d / f"file{i}.py").write_text("import os")
        assert detect_language(str(d)) == "python"

    def test_detect_empty(self, tmp_path):
        from orchestrator.config import detect_language
        d = tmp_path / "empty"
        d.mkdir()
        assert detect_language(str(d)) == ""

    def test_detect_mixed_dominant(self, tmp_path):
        from orchestrator.config import detect_language
        d = tmp_path / "repo"
        d.mkdir()
        for i in range(8):
            (d / f"file{i}.go").write_text("package main")
        for i in range(3):
            (d / f"file{i}.py").write_text("import os")
        assert detect_language(str(d)) == "go"
