"""Tests for validate_findings.py schema validation and severity ceiling enforcement."""

import os
import sys
import json
import pytest

# Insert the scripts directory so we can import validate_findings
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from validate_findings import (
    validate_finding,
    parse_findings,
    validate_file,
    SEVERITY_CEILING,
    SEVERITY_ORDER,
    REQUIRED_FIELDS,
    VALID_SEVERITIES,
    VALID_SOURCE_TRUST,
    FINDING_ID_PATTERN,
)


def _make_finding(**overrides):
    """Helper: build a valid finding dict, overriding specific fields."""
    base = {
        "finding_id": "SEC-001",
        "severity": "Critical",
        "source_trust": "External",
        "file": "cmd/main.go",
        "title": "SQL injection in user input handler",
        "evidence": "User-supplied query parameter is concatenated into SQL string at line 42.",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestValidateFinding
# ---------------------------------------------------------------------------


class TestValidateFinding:
    def test_valid_finding(self):
        """All fields present, correct types, severity within ceiling."""
        ok, errors = validate_finding(_make_finding())
        assert ok is True
        assert errors == []

    def test_missing_required_field(self):
        """Missing source_trust should produce an error."""
        finding = _make_finding()
        del finding["source_trust"]
        ok, errors = validate_finding(finding)
        assert ok is False
        assert any("source_trust" in e for e in errors)

    def test_missing_multiple_fields(self):
        """Missing several required fields should report all of them."""
        finding = {"finding_id": "SEC-001"}
        ok, errors = validate_finding(finding)
        assert ok is False
        # Should flag each missing field
        assert len(errors) >= 4  # severity, source_trust, file, title, evidence

    def test_invalid_severity(self):
        """severity='Extreme' is not in the allowed enum or aliases."""
        ok, errors = validate_finding(_make_finding(severity="Extreme"))
        assert ok is False
        assert any("severity" in e.lower() for e in errors)

    def test_severity_alias_high(self):
        """severity='High' is an alias that normalizes to 'Important'."""
        finding = _make_finding(severity="High")
        ok, errors = validate_finding(finding)
        assert ok is True
        assert errors == []
        assert finding["severity"] == "Important"

    def test_severity_alias_moderate(self):
        """severity='Moderate' is an alias that normalizes to 'Minor'."""
        finding = _make_finding(severity="Moderate")
        ok, errors = validate_finding(finding)
        assert ok is True
        assert errors == []
        assert finding["severity"] == "Minor"

    def test_severity_ceiling_enforced(self):
        """severity=Critical with source_trust=Internal violates ceiling (Minor max)."""
        ok, errors = validate_finding(
            _make_finding(severity="Critical", source_trust="Internal")
        )
        assert ok is False
        assert any("ceiling" in e.lower() or "exceeds" in e.lower() for e in errors)

    def test_severity_at_ceiling(self):
        """severity=Important with source_trust=Privileged is exactly at ceiling, should pass."""
        ok, errors = validate_finding(
            _make_finding(severity="Important", source_trust="Privileged")
        )
        assert ok is True
        assert errors == []

    def test_severity_below_ceiling(self):
        """severity=Minor with source_trust=External is well below ceiling, should pass."""
        ok, errors = validate_finding(
            _make_finding(severity="Minor", source_trust="External")
        )
        assert ok is True
        assert errors == []

    def test_invalid_finding_id_format(self):
        """finding_id='bad-id' does not match ^[A-Z]+-\\d{3}$ pattern."""
        ok, errors = validate_finding(_make_finding(finding_id="bad-id"))
        assert ok is False
        assert any("finding_id" in e.lower() or "format" in e.lower() for e in errors)

    def test_valid_finding_id_formats(self):
        """SEC-001, PERF-012, ARCH-100 should all pass."""
        for fid in ["SEC-001", "PERF-012", "ARCH-100"]:
            ok, errors = validate_finding(_make_finding(finding_id=fid))
            assert ok is True, f"{fid} should be valid but got errors: {errors}"

    def test_invalid_source_trust(self):
        """source_trust='Public' is not in the allowed enum."""
        ok, errors = validate_finding(_make_finding(source_trust="Public"))
        assert ok is False
        assert any("source_trust" in e.lower() for e in errors)

    def test_empty_evidence_fails(self):
        """evidence must not be empty."""
        ok, errors = validate_finding(_make_finding(evidence=""))
        assert ok is False
        assert any("evidence" in e.lower() for e in errors)

    def test_empty_title_fails(self):
        """title must not be empty."""
        ok, errors = validate_finding(_make_finding(title=""))
        assert ok is False
        assert any("title" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# TestSeverityCeiling
# ---------------------------------------------------------------------------


class TestSeverityCeiling:
    def test_external_allows_critical(self):
        ok, errors = validate_finding(
            _make_finding(severity="Critical", source_trust="External")
        )
        assert ok is True

    def test_authenticated_allows_critical(self):
        ok, errors = validate_finding(
            _make_finding(severity="Critical", source_trust="Authenticated")
        )
        assert ok is True

    def test_privileged_caps_at_important(self):
        """Privileged ceiling is Important. Critical should fail."""
        ok, errors = validate_finding(
            _make_finding(severity="Critical", source_trust="Privileged")
        )
        assert ok is False
        assert any("ceiling" in e.lower() or "exceeds" in e.lower() for e in errors)

    def test_privileged_allows_important(self):
        ok, errors = validate_finding(
            _make_finding(severity="Important", source_trust="Privileged")
        )
        assert ok is True

    def test_privileged_allows_minor(self):
        ok, errors = validate_finding(
            _make_finding(severity="Minor", source_trust="Privileged")
        )
        assert ok is True

    def test_internal_caps_at_minor(self):
        """Internal ceiling is Minor. Critical and Important should fail."""
        for sev in ["Critical", "Important"]:
            ok, errors = validate_finding(
                _make_finding(severity=sev, source_trust="Internal")
            )
            assert ok is False, f"{sev} with Internal should fail"

    def test_internal_allows_minor(self):
        ok, errors = validate_finding(
            _make_finding(severity="Minor", source_trust="Internal")
        )
        assert ok is True

    def test_na_allows_critical(self):
        ok, errors = validate_finding(
            _make_finding(severity="Critical", source_trust="N/A")
        )
        assert ok is True

    def test_na_allows_all_severities(self):
        for sev in ["Critical", "Important", "Minor"]:
            ok, errors = validate_finding(
                _make_finding(severity=sev, source_trust="N/A")
            )
            assert ok is True, f"N/A should allow {sev}"


# ---------------------------------------------------------------------------
# TestParseFindings
# ---------------------------------------------------------------------------


class TestParseFindings:
    def test_parse_structured_findings(self):
        text = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "Source Trust: External\n"
            "File: cmd/main.go\n"
            "Title: SQL injection\n"
            "Evidence: Unsanitized input at line 42\n"
        )
        findings = parse_findings(text)
        assert len(findings) == 1
        assert findings[0]["finding_id"] == "SEC-001"
        assert findings[0]["severity"] == "Critical"
        assert findings[0]["source_trust"] == "External"

    def test_parse_multiple_findings(self):
        text = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "Source Trust: External\n"
            "File: cmd/main.go\n"
            "Title: SQL injection\n"
            "Evidence: Unsanitized input\n"
            "\n"
            "Finding ID: PERF-001\n"
            "Severity: Minor\n"
            "Source Trust: Internal\n"
            "File: pkg/cache.go\n"
            "Title: Unbounded cache growth\n"
            "Evidence: No eviction policy\n"
        )
        findings = parse_findings(text)
        assert len(findings) == 2
        assert findings[0]["finding_id"] == "SEC-001"
        assert findings[1]["finding_id"] == "PERF-001"

    def test_parse_no_findings(self):
        text = "This is just a paragraph of text with no structured findings."
        findings = parse_findings(text)
        assert findings == []

    def test_parse_tolerates_extra_whitespace(self):
        text = (
            "  Finding ID:   SEC-001  \n"
            "  Severity:  Important \n"
            "  Source Trust: Authenticated \n"
            "  File:  src/handler.py \n"
            "  Title: XSS in template \n"
            "  Evidence:  User data rendered unescaped \n"
        )
        findings = parse_findings(text)
        assert len(findings) == 1
        assert findings[0]["finding_id"] == "SEC-001"
        assert findings[0]["severity"] == "Important"

    def test_parse_with_multiline_evidence(self):
        text = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "Source Trust: External\n"
            "File: cmd/main.go\n"
            "Title: SQL injection\n"
            "Evidence: Line 42 concatenates user input.\n"
            "  The query string is built without parameterization.\n"
        )
        findings = parse_findings(text)
        assert len(findings) == 1
        assert "parameterization" in findings[0]["evidence"]


# ---------------------------------------------------------------------------
# TestValidateFile
# ---------------------------------------------------------------------------


class TestValidateFile:
    def test_validate_valid_file(self, tmp_path):
        f = tmp_path / "findings.md"
        f.write_text(
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "Source Trust: External\n"
            "File: cmd/main.go\n"
            "Title: SQL injection\n"
            "Evidence: Unsanitized input at line 42\n"
        )
        result = validate_file(str(f))
        assert result["valid"] is True
        assert result["total"] == 1
        assert result["errors"] == 0

    def test_validate_file_with_errors(self, tmp_path):
        f = tmp_path / "findings.md"
        f.write_text(
            "Finding ID: bad-format\n"
            "Severity: High\n"
            "Source Trust: External\n"
            "File: cmd/main.go\n"
            "Title: Something\n"
            "Evidence: Some evidence\n"
        )
        result = validate_file(str(f))
        assert result["valid"] is False
        assert result["errors"] > 0

    def test_validate_nonexistent_file(self):
        result = validate_file("/nonexistent/path/findings.md")
        assert result["valid"] is False
        assert "error" in result

    def test_validate_empty_file(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        result = validate_file(str(f))
        assert result["total"] == 0


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_schema_command(self):
        """The schema subcommand should print valid JSON to stdout."""
        import subprocess

        script = os.path.join(scripts_dir, "validate_findings.py")
        proc = subprocess.run(
            [sys.executable, script, "schema"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        schema = json.loads(proc.stdout)
        assert "required_fields" in schema
        assert "severity_ceiling" in schema

    def test_validate_command_valid(self, tmp_path):
        """validate subcommand exits 0 on valid findings."""
        import subprocess

        f = tmp_path / "valid.md"
        f.write_text(
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "Source Trust: External\n"
            "File: cmd/main.go\n"
            "Title: SQL injection\n"
            "Evidence: Unsanitized input at line 42\n"
        )
        script = os.path.join(scripts_dir, "validate_findings.py")
        proc = subprocess.run(
            [sys.executable, script, "validate", str(f)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0

    def test_validate_command_invalid(self, tmp_path):
        """validate subcommand exits 1 on invalid findings."""
        import subprocess

        f = tmp_path / "invalid.md"
        f.write_text(
            "Finding ID: bad\n"
            "Severity: High\n"
            "Source Trust: External\n"
            "File: cmd/main.go\n"
            "Title: Something\n"
            "Evidence: Evidence text\n"
        )
        script = os.path.join(scripts_dir, "validate_findings.py")
        proc = subprocess.run(
            [sys.executable, script, "validate", str(f)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1
