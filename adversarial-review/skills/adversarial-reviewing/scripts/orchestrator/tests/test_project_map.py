import os
import pytest
from pathlib import Path

from orchestrator.project_map import (
    build_project_map, _detect_framework, _find_security_relevant_files,
    load_hotspot_patterns, compute_hotspots,
)


@pytest.fixture
def go_repo(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / "go.mod").write_text("module example.com/myapp")
    (d / "Dockerfile").write_text("FROM golang:1.21")
    (d / "Makefile").write_text("build:\n\tgo build")
    (d / "cmd").mkdir()
    (d / "cmd" / "main.go").write_text("package main")
    (d / "internal").mkdir()
    (d / "internal" / "controller").mkdir()
    (d / "internal" / "controller" / "auth.go").write_text("package controller")
    (d / "internal" / "webhook").mkdir()
    (d / "internal" / "webhook" / "handler.go").write_text("package webhook")
    (d / "pkg").mkdir()
    (d / "pkg" / "cert.go").write_text("package pkg")
    (d / "config").mkdir()
    (d / "config" / "rbac").mkdir()
    (d / "config" / "rbac" / "role.yaml").write_text("kind: ClusterRole")
    (d / "api").mkdir()
    (d / "api" / "types.go").write_text("package api")
    return str(d)


@pytest.fixture
def python_repo(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / "setup.py").write_text("from setuptools import setup")
    (d / "requirements.txt").write_text("django==4.2")
    (d / "manage.py").write_text("#!/usr/bin/env python")
    (d / "app").mkdir()
    (d / "app" / "views.py").write_text("")
    (d / "app" / "auth.py").write_text("")
    (d / "app" / "settings.py").write_text("")
    return str(d)


class TestDetectFramework:
    def test_go_k8s_operator(self, go_repo):
        result = _detect_framework(go_repo)
        assert "Go" in result
        assert "operator" in result.lower() or "Kubernetes" in result

    def test_python_django(self, python_repo):
        result = _detect_framework(python_repo)
        assert "Django" in result

    def test_unknown(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        assert "Unknown" in _detect_framework(str(d))

    def test_rust(self, tmp_path):
        d = tmp_path / "repo"
        d.mkdir()
        (d / "Cargo.toml").write_text("[package]")
        (d / "src").mkdir()
        (d / "src" / "main.rs").write_text("fn main() {}")
        assert "Rust" in _detect_framework(str(d))


class TestSecurityRelevantFiles:
    def test_finds_auth_files(self, go_repo):
        files = _find_security_relevant_files(go_repo)
        assert "authentication/authorization" in files
        auth_files = files["authentication/authorization"]
        assert any("auth.go" in f for f in auth_files)

    def test_finds_rbac_files(self, go_repo):
        files = _find_security_relevant_files(go_repo)
        assert "RBAC/permissions" in files

    def test_finds_crypto_files(self, go_repo):
        files = _find_security_relevant_files(go_repo)
        assert "crypto/TLS" in files
        assert any("cert.go" in f for f in files["crypto/TLS"])

    def test_finds_webhook_files(self, go_repo):
        files = _find_security_relevant_files(go_repo)
        assert "webhook/admission" in files


class TestBuildProjectMap:
    def test_go_repo_has_all_sections(self, go_repo):
        result = build_project_map(go_repo)
        assert "## Project Map" in result
        assert "Go" in result
        assert "Directory Structure" in result
        assert "Security-Relevant Files" in result
        assert "Infrastructure Files" in result
        assert "Dockerfile" in result

    def test_python_repo(self, python_repo):
        result = build_project_map(python_repo)
        assert "Django" in result
        assert "auth.py" in result

    def test_empty_dir(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        result = build_project_map(str(d))
        assert "Unknown" in result

    def test_nonexistent_dir(self):
        assert build_project_map("/nonexistent") == ""

    def test_must_examine_instruction(self, go_repo):
        result = build_project_map(go_repo)
        assert "MUST examine" in result


class TestHotspotBackwardCompat:
    def test_load_patterns_from_real_profile(self):
        profile = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "profiles", "code",
        )
        if not os.path.isdir(profile):
            pytest.skip("profiles/code not found")
        patterns = load_hotspot_patterns(profile)
        assert "SEC" in patterns

    def test_load_patterns_missing_file(self, tmp_path):
        assert load_hotspot_patterns(str(tmp_path)) == {}

    def test_compute_hotspots_finds_matches(self, tmp_path):
        """Verify hotspot patterns still work when profile has them."""
        d = tmp_path / "src"
        d.mkdir()
        (d / "main.go").write_text("IsCA := true\n")
        patterns = [{"pattern": "IsCA", "description": "CA check"}]
        result = compute_hotspots(str(d), "SEC", patterns)
        assert "IsCA" in result


class TestProjectMapEdgeCases:
    def test_symlinks_in_source_tree(self, tmp_path):
        """Symlinks should not cause crashes."""
        d = tmp_path / "repo"
        d.mkdir()
        (d / "go.mod").write_text("module test")
        (d / "main.go").write_text("package main")
        link = d / "link_to_nowhere"
        try:
            link.symlink_to("/nonexistent/path")
        except OSError:
            pytest.skip("cannot create symlinks")
        result = build_project_map(str(d))
        assert "Go" in result

    def test_deeply_nested_dirs_capped(self, tmp_path):
        """Directory tree depth should be capped."""
        d = tmp_path / "repo"
        nested = d / "a" / "b" / "c" / "d" / "e" / "f"
        nested.mkdir(parents=True)
        (nested / "deep.go").write_text("package deep")
        (d / "go.mod").write_text("module test")
        result = build_project_map(str(d))
        assert "deep.go" not in result

    def test_binary_files_excluded_from_security_scan(self, tmp_path):
        d = tmp_path / "repo"
        d.mkdir()
        (d / ".hidden_secret").write_text("should be skipped")
        (d / "auth.go").write_text("package auth")
        files = _find_security_relevant_files(str(d))
        all_files = [f for flist in files.values() for f in flist]
        assert not any(".hidden" in f for f in all_files)
        assert any("auth.go" in f for f in all_files)

    def test_skip_dirs_respected(self, tmp_path):
        d = tmp_path / "repo"
        (d / "vendor" / "auth").mkdir(parents=True)
        (d / "vendor" / "auth" / "secret.go").write_text("package auth")
        (d / "src").mkdir()
        (d / "src" / "auth.go").write_text("package src")
        files = _find_security_relevant_files(str(d))
        all_files = [f for flist in files.values() for f in flist]
        assert not any("vendor" in f for f in all_files)
        assert any("auth.go" in f for f in all_files)

    def test_multiple_frameworks_detected(self, tmp_path):
        d = tmp_path / "repo"
        d.mkdir()
        (d / "go.mod").write_text("module test")
        (d / "Dockerfile").write_text("FROM golang")
        (d / "Makefile").write_text("build:")
        result = _detect_framework(str(d))
        assert "Go" in result

    def test_security_keywords_in_directory_names(self, tmp_path):
        """Files inside dirs named 'auth/' should be flagged."""
        from orchestrator.project_map import _find_security_relevant_files
        d = tmp_path / "repo"
        (d / "internal" / "auth").mkdir(parents=True)
        (d / "internal" / "auth" / "handler.go").write_text("package auth")
        files = _find_security_relevant_files(str(d))
        all_files = [f for flist in files.values() for f in flist]
        assert any("handler.go" in f for f in all_files)
