"""Tests for detection_judge parsing, dedup, and filtering."""

import pytest
from eval.judges.detection_judge import (
    _finding_dedup_key,
    _extract_findings,
    _parse_structured_format,
    _parse_markdown_format,
    _parse_narrative_format,
    _parse_table_format,
    _parse_findings_from_text,
    _find_dismissed_ranges,
)


class TestFindingDedupKey:
    def test_returns_loc_key_when_lines_present(self):
        f = {"file": "pkg/auth/cipher.go", "lines": "48-82", "finding_id": "SEC-001"}
        key, basename, first_line = _finding_dedup_key(f)
        assert key == "loc:cipher.go:48"
        assert basename == "cipher.go"
        assert first_line == 48

    def test_returns_id_key_when_no_lines(self):
        f = {"file": "pkg/auth/cipher.go", "lines": "", "finding_id": "SEC-001"}
        key, basename, first_line = _finding_dedup_key(f)
        assert key == "id:SEC-001"
        assert first_line is None

    def test_returns_id_key_when_no_file(self):
        f = {"file": "", "lines": "48", "finding_id": "SEC-001"}
        key, _, first_line = _finding_dedup_key(f)
        assert key == "id:SEC-001"

    def test_anon_key_when_no_id_or_lines(self):
        f = {"file": "", "lines": ""}
        key, _, _ = _finding_dedup_key(f)
        assert key.startswith("_anon_")

    def test_handles_comma_separated_lines(self):
        f = {"file": "main.go", "lines": "10,20,30", "finding_id": "X-1"}
        key, _, first_line = _finding_dedup_key(f)
        assert key == "loc:main.go:10"
        assert first_line == 10

    def test_handles_dash_range_lines(self):
        f = {"file": "main.go", "lines": "100-200", "finding_id": "X-1"}
        key, _, first_line = _finding_dedup_key(f)
        assert key == "loc:main.go:100"
        assert first_line == 100


class TestExtractFindings:
    def test_dedup_by_exact_location(self):
        content_a = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "File: pkg/cipher.go\n"
            "Lines: 48-82\n"
            "Title: Weak cipher\n"
            "Evidence: Uses CFB mode\n"
        )
        content_b = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "File: pkg/cipher.go\n"
            "Lines: 48-82\n"
            "Title: Weak cipher mode\n"
            "Evidence: CFB no auth\n"
        )
        outputs = {"files": {"iter1.md": content_a, "iter2.md": content_b}}
        findings = _extract_findings(outputs)
        assert len(findings) == 1

    def test_dedup_by_proximity(self):
        content_a = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "File: pkg/cipher.go\n"
            "Lines: 48-82\n"
            "Title: Weak cipher\n"
            "Evidence: Uses CFB mode\n"
        )
        content_b = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "File: pkg/cipher.go\n"
            "Lines: 45-85\n"
            "Title: Weak cipher mode\n"
            "Evidence: CFB no auth\n"
        )
        outputs = {"files": {"iter1.md": content_a, "iter2.md": content_b}}
        findings = _extract_findings(outputs)
        assert len(findings) == 1

    def test_no_dedup_different_files(self):
        content_a = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "File: pkg/cipher.go\n"
            "Lines: 48\n"
            "Title: Weak cipher\n"
            "Evidence: Uses CFB\n"
        )
        content_b = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "File: pkg/auth.go\n"
            "Lines: 48\n"
            "Title: Weak auth\n"
            "Evidence: No auth check\n"
        )
        outputs = {"files": {"iter1.md": content_a, "challenge.md": content_b}}
        findings = _extract_findings(outputs)
        assert len(findings) == 2

    def test_no_dedup_distant_lines(self):
        content_a = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "File: main.go\n"
            "Lines: 10\n"
            "Title: Issue A\n"
            "Evidence: Evidence A\n"
        )
        content_b = (
            "Finding ID: SEC-002\n"
            "Severity: Important\n"
            "File: main.go\n"
            "Lines: 100\n"
            "Title: Issue B\n"
            "Evidence: Evidence B\n"
        )
        outputs = {"files": {"a.md": content_a, "b.md": content_b}}
        findings = _extract_findings(outputs)
        assert len(findings) == 2

    def test_excludes_report_files_when_agent_findings_exist(self):
        agent = (
            "Finding ID: SEC-001\nSeverity: Critical\n"
            "File: a.go\nLines: 10\nTitle: Real\nEvidence: Real\n"
        )
        report = (
            "Finding ID: SEC-001\nSeverity: Critical\n"
            "File: a.go\nLines: 10\nTitle: Summary\nEvidence: Summary\n\n"
            "Finding ID: SEC-002\nSeverity: Important\n"
            "File: b.go\nLines: 20\nTitle: Extra\nEvidence: Extra\n"
        )
        outputs = {"files": {"SEC-output.md": agent, "REPORT.md": report}}
        findings = _extract_findings(outputs)
        assert len(findings) == 1
        assert findings[0]["title"] == "Real"

    def test_falls_back_to_report_when_no_agent_findings(self):
        report = (
            "Finding ID: SEC-001\nSeverity: Critical\n"
            "File: a.go\nLines: 10\nTitle: From report\nEvidence: Evidence\n"
        )
        outputs = {"files": {"REPORT.md": report}}
        findings = _extract_findings(outputs)
        assert len(findings) == 1
        assert findings[0]["title"] == "From report"


class TestParseStructuredFormat:
    def test_basic_parsing(self):
        text = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "File: pkg/auth.go\n"
            "Lines: 48-82\n"
            "Title: Weak cipher\n"
            "Evidence: Uses CFB mode without authentication\n"
        )
        findings = _parse_structured_format(text)
        assert len(findings) == 1
        f = findings[0]
        assert f["finding_id"] == "SEC-001"
        assert f["severity"] == "Critical"
        assert f["file"] == "pkg/auth.go"
        assert f["lines"] == "48-82"
        assert f["title"] == "Weak cipher"

    def test_extracts_lines_field(self):
        text = (
            "Finding ID: CORR-003\n"
            "Severity: Important\n"
            "File: internal/controller.go\n"
            "Lines: 123-145\n"
            "Title: Race condition\n"
            "Evidence: Concurrent access\n"
        )
        findings = _parse_structured_format(text)
        assert len(findings) == 1
        assert findings[0]["lines"] == "123-145"

    def test_handles_bold_markdown_fields(self):
        text = (
            "**Finding ID:** SEC-002\n"
            "**Severity:** Important\n"
            "**File:** pkg/tls.go\n"
            "**Lines:** 50\n"
            "**Title:** Missing cert validation\n"
            "**Evidence:** InsecureSkipVerify\n"
        )
        findings = _parse_structured_format(text)
        assert len(findings) == 1
        assert findings[0]["finding_id"] == "SEC-002"

    def test_multiple_findings(self):
        text = (
            "Finding ID: SEC-001\nSeverity: Critical\n"
            "Title: Issue A\nEvidence: Ev A\n\n"
            "Finding ID: SEC-002\nSeverity: Important\n"
            "Title: Issue B\nEvidence: Ev B\n"
        )
        findings = _parse_structured_format(text)
        assert len(findings) == 2


class TestParseMarkdownFormat:
    def test_basic_parsing(self):
        text = (
            "### SEC-001: Weak cipher mode\n"
            "**Severity:** Critical\n"
            "**File:** `pkg/cipher.go`\n"
            "Evidence here\n"
        )
        findings = _parse_markdown_format(text)
        assert len(findings) == 1
        assert findings[0]["finding_id"] == "SEC-001"
        assert findings[0]["title"] == "Weak cipher mode"
        assert findings[0]["severity"] == "Critical"

    def test_skips_dismissed(self):
        text = (
            "### SEC-001: Real finding\n"
            "**Severity:** Critical\n\n"
            "## Dismissed Findings\n"
            "### SEC-002: Not real DISMISSED\n"
            "**Severity:** Minor\n"
        )
        findings = _parse_markdown_format(text)
        assert len(findings) == 1
        assert findings[0]["finding_id"] == "SEC-001"

    def test_skips_withdrawn(self):
        text = "### SEC-001: WITHDRAWN due to false positive\n**Severity:** Minor\n"
        findings = _parse_markdown_format(text)
        assert len(findings) == 0

    def test_skips_confirmed_verdicts(self):
        text = (
            "### SEC-001: CONFIRMED\n"
            "**Severity:** Critical\n\n"
            "### SEC-002: ADJUST SEVERITY from Critical to Important\n"
            "**Severity:** Important\n"
        )
        findings = _parse_markdown_format(text)
        assert len(findings) == 0

    def test_maps_severity(self):
        text = "### F-001: Test finding\n**Severity:** High\nEvidence\n"
        findings = _parse_markdown_format(text)
        assert len(findings) == 1
        assert findings[0]["severity"] == "Important"


class TestParseTableFormat:
    def test_basic_table_row(self):
        text = "| SEC-001 | Critical | pkg/auth.go:48 | Weak cipher |\n"
        findings = _parse_table_format(text)
        assert len(findings) == 1
        assert findings[0]["finding_id"] == "SEC-001"
        assert findings[0]["file"] == "pkg/auth.go"
        assert findings[0]["title"] == "Weak cipher"

    def test_skips_header_rows(self):
        text = (
            "| ID | Severity | File | Description |\n"
            "| --- | --- | --- | --- |\n"
            "| SEC-001 | Critical | `auth.go` | Issue |\n"
        )
        findings = _parse_table_format(text)
        assert len(findings) == 1

    def test_skips_confirmed_status_rows(self):
        text = "| SEC-001 | CONFIRMED | Important | High |\n"
        findings = _parse_table_format(text)
        assert len(findings) == 0

    def test_skips_withdrawn_status_rows(self):
        text = "| SEC-001 | WITHDRAWN | Important | Speculative |\n"
        findings = _parse_table_format(text)
        assert len(findings) == 0

    def test_skips_rows_without_file_path(self):
        text = "| SEC-001 | Minor | | Some desc |\n"
        findings = _parse_table_format(text)
        assert len(findings) == 0

    def test_skips_confirmed_descriptions(self):
        text = "| CORR-002 | Important | Minor | CONFIRMED finding |\n"
        findings = _parse_table_format(text)
        assert len(findings) == 0


class TestParseNarrativeFormat:
    def test_basic_parsing(self):
        text = (
            "### 1. Race condition (Critical) [SEC-001 + CORR-003]\n"
            "**File:** `pkg/auth.go`:48\n"
            "Description of the issue\n"
        )
        findings = _parse_narrative_format(text)
        assert len(findings) == 1
        assert findings[0]["finding_id"] == "SEC-001"
        assert findings[0]["severity"] == "Critical"

    def test_maps_severity(self):
        text = "### Buffer overflow (High) [SEC-001]\n**File:** `buf.go`\n"
        findings = _parse_narrative_format(text)
        assert len(findings) == 1
        assert findings[0]["severity"] == "Important"

    def test_skips_confirmed(self):
        text = "### CONFIRMED finding (Critical) [SEC-001]\n**File:** `a.go`\n"
        findings = _parse_narrative_format(text)
        assert len(findings) == 0


class TestParseFindingsFromText:
    def test_returns_parser_with_most_findings(self):
        text = (
            "Finding ID: SEC-001\n"
            "Severity: Critical\n"
            "Title: Issue A\n"
            "Evidence: Ev A\n\n"
            "Finding ID: SEC-002\n"
            "Severity: Important\n"
            "Title: Issue B\n"
            "Evidence: Ev B\n"
        )
        findings = _parse_findings_from_text(text)
        assert len(findings) == 2

    def test_returns_empty_for_no_findings(self):
        text = "This is just regular text with no findings."
        findings = _parse_findings_from_text(text)
        assert len(findings) == 0


class TestFindDismissedRanges:
    def test_identifies_dismissed_section(self):
        text = "## Active\nstuff\n## Dismissed Findings\nold\n## Other\nmore"
        ranges = _find_dismissed_ranges(text)
        assert len(ranges) == 1
        start, end = ranges[0]
        assert "Dismissed" in text[start:end]
        assert "Other" not in text[start:end]

    def test_no_dismissed_section(self):
        text = "## Active\nstuff\n## Summary\nmore"
        ranges = _find_dismissed_ranges(text)
        assert len(ranges) == 0
