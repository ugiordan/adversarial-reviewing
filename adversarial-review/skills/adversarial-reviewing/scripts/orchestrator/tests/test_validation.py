import hashlib
import pytest
from orchestrator.validation import (
    check_outputs_exist, check_delimiters, check_prompt_hashes,
    check_output_sizes, ComplianceResult,
)
from orchestrator.types import Delimiters


class TestCheckOutputsExist:
    def test_all_exist(self, tmp_cache_dir):
        (tmp_cache_dir / "outputs" / "SEC-iter1.md").write_text("content")
        (tmp_cache_dir / "outputs" / "CORR-iter1.md").write_text("content")
        files = [str(tmp_cache_dir / "outputs" / f) for f in
                 ["SEC-iter1.md", "CORR-iter1.md"]]
        result = check_outputs_exist(files)
        assert result.passed

    def test_missing_file(self, tmp_cache_dir):
        files = [str(tmp_cache_dir / "outputs" / "SEC-iter1.md")]
        result = check_outputs_exist(files)
        assert not result.passed
        assert "missing" in result.error.lower()


class TestCheckDelimiters:
    def test_valid_delimiters(self, tmp_path):
        delims = Delimiters(begin="===START===", end="===END===", hex="abc")
        f = tmp_path / "output.md"
        f.write_text("===START===\nfindings here\n===END===\n")
        result = check_delimiters(str(f), delims)
        assert result.passed

    def test_missing_delimiters(self, tmp_path):
        delims = Delimiters(begin="===START===", end="===END===", hex="abc")
        f = tmp_path / "output.md"
        f.write_text("findings without delimiters")
        result = check_delimiters(str(f), delims)
        assert not result.passed


class TestCheckPromptHashes:
    def test_matching_hashes(self, tmp_path):
        f = tmp_path / "prompt.md"
        f.write_text("agent prompt content")
        expected_hash = "sha256:" + hashlib.sha256(b"agent prompt content").hexdigest()
        result = check_prompt_hashes({str(f): expected_hash})
        assert result.passed

    def test_tampered_prompt(self, tmp_path):
        f = tmp_path / "prompt.md"
        f.write_text("modified content")
        result = check_prompt_hashes({str(f): "sha256:wronghash"})
        assert not result.passed
        assert "tamper" in result.error.lower()


class TestCheckOutputSizes:
    def test_normal_size(self, tmp_path):
        f = tmp_path / "output.md"
        f.write_text("x" * 1000)
        result = check_output_sizes([str(f)])
        assert result.passed
        assert result.warnings == 0

    def test_small_output_warns(self, tmp_path):
        f = tmp_path / "output.md"
        f.write_text("tiny")
        result = check_output_sizes([str(f)])
        assert result.passed
        assert result.warnings > 0


class TestCheckFindingStructure:
    def test_valid_findings(self):
        from orchestrator.validation import check_finding_structure
        output = (
            "### SEC-001: SQL Injection\n"
            "**Severity:** Important\n"
            "**Confidence:** High\n"
            "**Evidence:** User input passed unsanitized\n"
        )
        result = check_finding_structure(output)
        assert result.passed
        assert result.findings_count == 1

    def test_multiple_findings(self):
        from orchestrator.validation import check_finding_structure
        output = (
            "### SEC-001: SQL Injection\ndetails\n"
            "### SEC-002: XSS\ndetails\n"
            "### SEC-003: CSRF\ndetails\n"
        )
        result = check_finding_structure(output)
        assert result.passed
        assert result.findings_count == 3

    def test_no_findings_marker(self):
        from orchestrator.validation import check_finding_structure
        result = check_finding_structure("NO_FINDINGS_REPORTED")
        assert result.passed
        assert result.findings_count == 0

    def test_missing_structure(self):
        from orchestrator.validation import check_finding_structure
        result = check_finding_structure("Just some random text about the code")
        assert not result.passed
        assert result.findings_count == 0
        assert len(result.warnings) > 0


class TestCheckComparativeReasoning:
    def test_has_comparative_however(self):
        from orchestrator.validation import check_comparative_reasoning
        text = "However, this could also be a false positive because..."
        assert check_comparative_reasoning(text)

    def test_has_comparative_alternatively(self):
        from orchestrator.validation import check_comparative_reasoning
        text = "Alternatively, the developer may have intended this behavior."
        assert check_comparative_reasoning(text)

    def test_missing_comparative(self):
        from orchestrator.validation import check_comparative_reasoning
        text = "This is definitely a bug. Fix it immediately."
        assert not check_comparative_reasoning(text)

    def test_false_positive_term(self):
        from orchestrator.validation import check_comparative_reasoning
        text = "This appears to be a false positive due to static analysis limitations."
        assert check_comparative_reasoning(text)
