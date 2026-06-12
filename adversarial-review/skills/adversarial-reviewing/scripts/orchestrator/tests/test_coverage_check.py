"""Tests for coverage_check.py: programmatic pattern coverage verification."""

import os
import yaml
import pytest

from ..coverage_check import check_coverage


class TestCheckCoverage:
    def _setup(self, tmp_path, patterns, output_text):
        checklist = {"agent": "SEC", "patterns": patterns}
        (tmp_path / "detection-checklist.yaml").write_text(
            yaml.safe_dump(checklist, default_flow_style=False)
        )
        (tmp_path / "output.md").write_text(output_text)
        return str(tmp_path)

    def test_all_addressed(self, tmp_path):
        dispatch = self._setup(tmp_path, [
            {"id": "crypto_1", "grep": "NewCFBEncrypter", "category": "Crypto",
             "status": "hits_found", "hits": [{"file": "cipher.go", "line": 45}]},
        ], "Finding ID: SEC-001\nFile: cipher.go\nTitle: CFB mode\nEvidence: NewCFBEncrypter\n")
        result = check_coverage(dispatch, "SEC")
        assert result["addressed"] == 1
        assert result["gaps"] == []
        assert result["gap_report_md"] == ""

    def test_gap_detected(self, tmp_path):
        dispatch = self._setup(tmp_path, [
            {"id": "crypto_1", "grep": "NewCFBEncrypter", "category": "Crypto",
             "status": "hits_found", "hits": [{"file": "cipher.go", "line": 45}]},
            {"id": "tls_1", "grep": "InsecureSkipVerify", "category": "TLS",
             "status": "hits_found", "hits": [{"file": "config.go", "line": 10}]},
        ], "Finding ID: SEC-001\nFile: cipher.go\nTitle: CFB\nEvidence: found\n")
        result = check_coverage(dispatch, "SEC")
        assert result["addressed"] == 1
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["pattern_id"] == "tls_1"
        assert "GAP" in result["gap_report_md"]

    def test_no_hits_skipped(self, tmp_path):
        dispatch = self._setup(tmp_path, [
            {"id": "crypto_1", "grep": "NewCFBEncrypter", "category": "Crypto",
             "status": "no_hits", "hits": []},
        ], "NO_FINDINGS_REPORTED")
        result = check_coverage(dispatch, "SEC")
        assert result["total_patterns"] == 0

    def test_grep_string_mention_counts(self, tmp_path):
        dispatch = self._setup(tmp_path, [
            {"id": "tls_1", "grep": "InsecureSkipVerify", "category": "TLS",
             "status": "hits_found", "hits": [{"file": "config.go", "line": 10}]},
        ], "Coverage: InsecureSkipVerify checked, not an issue\n")
        result = check_coverage(dispatch, "SEC")
        assert result["addressed"] == 1
        assert result["gaps"] == []

    def test_missing_files(self, tmp_path):
        result = check_coverage(str(tmp_path), "SEC")
        assert result["total_patterns"] == 0

    def test_gap_report_format(self, tmp_path):
        dispatch = self._setup(tmp_path, [
            {"id": "pprof_1", "grep": "pprof", "category": "deprecated",
             "status": "hits_found",
             "hits": [{"file": "config.go", "line": 22}, {"file": "flags.go", "line": 30}]},
        ], "Finding ID: SEC-001\nFile: other.go\nTitle: Unrelated\nEvidence: x\n")
        result = check_coverage(dispatch, "SEC")
        assert len(result["gaps"]) == 1
        md = result["gap_report_md"]
        assert "Programmatically Verified" in md
        assert "config.go:22" in md
        assert "flags.go:30" in md
        assert "pprof_1" in md
