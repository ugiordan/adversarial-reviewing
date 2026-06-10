"""Tests for pattern_scan.py: extraction, pre-scan, checklist generation."""

import os
import pytest
import yaml

from ..pattern_scan import (
    extract_patterns,
    run_prescan,
    generate_checklist,
    format_pattern_hits_md,
    save_prescan,
    load_prescan,
    PatternDef,
    PatternHit,
    ScanResult,
    _should_skip,
)


# ---------------------------------------------------------------------------
# Sample agent instructions (subset of security-auditor.md)
# ---------------------------------------------------------------------------

SAMPLE_SEC_INSTRUCTIONS = """\
# Security Auditor (SEC)

## Destination

Find security vulnerabilities.

## Detection Patterns

Beyond OWASP Top 10, check for these patterns:

**Crypto and entropy:**
- Cipher modes without authentication: CFB, CTR, OFB. Look for `NewCFBEncrypter`, `NewCTR`, `NewOFB` without accompanying HMAC/GCM.
- SHA1/MD5 password hashing: `{SHA}` prefix in htpasswd, `sha1.New()`, `md5.New()` for password storage.
- Weak TLS: `InsecureSkipVerify: true` or `MinVersion` not set.

**RBAC over-privilege:**
- `verbs=*` on RBAC resources implicitly grants `escalate` and `bind`.
- `aggregate-to-edit` or `aggregate-to-admin` labels silently expand built-in roles.

**Committed secrets:**
- Base64-encoded values in Kubernetes Secret YAML committed to git.
- API keys in `config/monitoring/`.

## File Triage Strategy

When more files are listed...
"""

SAMPLE_NO_PATTERNS = """\
# Performance Analyst

## Destination

Find performance issues.

## Constraints

No detection patterns here.
"""


# ---------------------------------------------------------------------------
# TestExtractPatterns
# ---------------------------------------------------------------------------


class TestExtractPatterns:
    def test_extracts_crypto_patterns(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "NewCFBEncrypter" in grep_strings
        assert "NewCTR" in grep_strings
        assert "NewOFB" in grep_strings

    def test_extracts_sha1_patterns(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "{SHA}" in grep_strings
        assert "sha1.New()" in grep_strings
        assert "md5.New()" in grep_strings

    def test_extracts_tls_patterns(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "InsecureSkipVerify: true" in grep_strings

    def test_extracts_rbac_patterns(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "verbs=*" in grep_strings
        assert "aggregate-to-edit" in grep_strings
        assert "aggregate-to-admin" in grep_strings

    def test_extracts_secrets_patterns(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "config/monitoring/" in grep_strings

    def test_assigns_categories(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        categories = {p.category for p in patterns}
        assert "Crypto and entropy" in categories
        assert "RBAC over-privilege" in categories
        assert "Committed secrets" in categories

    def test_generates_stable_ids(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        ids = [p.id for p in patterns]
        assert len(ids) == len(set(ids)), "Pattern IDs must be unique"
        for pid in ids:
            assert "_" in pid, f"Pattern ID should contain category slug: {pid}"

    def test_no_detection_section_returns_empty(self):
        patterns = extract_patterns(SAMPLE_NO_PATTERNS, "PERF")
        assert patterns == []

    def test_filters_too_broad_patterns(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "[0]" not in grep_strings
        assert "true" not in grep_strings

    def test_total_pattern_count(self):
        patterns = extract_patterns(SAMPLE_SEC_INSTRUCTIONS, "SEC")
        assert len(patterns) >= 8, f"Expected 8+ patterns, got {len(patterns)}"

    def test_extracts_from_real_sec_agent(self):
        """Extract from the actual security-auditor.md file."""
        sec_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "profiles", "code", "agents", "security-auditor.md",
        )
        if not os.path.isfile(sec_path):
            pytest.skip("security-auditor.md not found")
        with open(sec_path) as f:
            content = f.read()
        patterns = extract_patterns(content, "SEC")
        assert len(patterns) >= 10, f"Expected 10+ patterns, got {len(patterns)}"
        grep_strings = [p.grep_pattern for p in patterns]
        assert "NewCFBEncrypter" in grep_strings
        assert "InsecureSkipVerify: true" in grep_strings
        assert "aggregate-to-edit" in grep_strings


# ---------------------------------------------------------------------------
# TestRunPrescan
# ---------------------------------------------------------------------------


class TestRunPrescan:
    def test_finds_hits_in_source(self, tmp_path):
        (tmp_path / "cipher.go").write_text(
            'package crypto\n'
            'func encrypt() {\n'
            '    stream := cipher.NewCFBEncrypter(block, iv)\n'
            '}\n'
        )
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB mode"),
            PatternDef(id="crypto_2", category="Crypto", grep_pattern="sha1.New", description="SHA1"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert len(results) == 2
        assert results[0].status == "hits_found"
        assert len(results[0].hits) == 1
        assert results[0].hits[0].file == "cipher.go"
        assert results[0].hits[0].line == 3
        assert results[1].status == "no_hits"

    def test_skips_test_files(self, tmp_path):
        (tmp_path / "cipher_test.go").write_text(
            'package crypto\n'
            'func TestEncrypt() {\n'
            '    stream := cipher.NewCFBEncrypter(block, iv)\n'
            '}\n'
        )
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert results[0].status == "no_hits"

    def test_skips_vendor_dir(self, tmp_path):
        vendor = tmp_path / "vendor" / "lib"
        vendor.mkdir(parents=True)
        (vendor / "crypto.go").write_text('cipher.NewCFBEncrypter(block, iv)\n')
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert results[0].status == "no_hits"

    def test_caps_hits_per_pattern(self, tmp_path):
        lines = []
        for i in range(20):
            lines.append(f'line {i}: InsecureSkipVerify: true\n')
        (tmp_path / "config.go").write_text("".join(lines))
        patterns = [
            PatternDef(id="tls_1", category="TLS", grep_pattern="InsecureSkipVerify: true", description="TLS skip"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert len(results[0].hits) <= 10

    def test_empty_source_dir(self, tmp_path):
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert results[0].status == "no_hits"

    def test_no_patterns(self, tmp_path):
        results = run_prescan(str(tmp_path), [])
        assert results == []


# ---------------------------------------------------------------------------
# TestShouldSkip
# ---------------------------------------------------------------------------


class TestShouldSkip:
    def test_skips_test_go(self):
        assert _should_skip("pkg/crypto_test.go") is True

    def test_skips_test_py(self):
        assert _should_skip("tests/test_main_test.py") is True

    def test_skips_vendor(self):
        assert _should_skip("vendor/github.com/pkg/foo.go") is True

    def test_skips_testdata(self):
        assert _should_skip("pkg/testdata/fixture.yaml") is True

    def test_allows_regular_file(self):
        assert _should_skip("pkg/crypto/cipher.go") is False

    def test_allows_yaml(self):
        assert _should_skip("config/rbac/role.yaml") is False


# ---------------------------------------------------------------------------
# TestGenerateChecklist
# ---------------------------------------------------------------------------


class TestGenerateChecklist:
    def test_generates_valid_structure(self):
        results = [
            ScanResult(
                pattern=PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB mode"),
                hits=[PatternHit(file="cipher.go", line=45, content="cipher.NewCFBEncrypter(block, iv)")],
            ),
            ScanResult(
                pattern=PatternDef(id="crypto_2", category="Crypto", grep_pattern="sha1.New", description="SHA1 hashing"),
                hits=[],
            ),
        ]
        checklist = generate_checklist(results, "SEC")
        assert checklist["agent"] == "SEC"
        assert len(checklist["patterns"]) == 2
        assert checklist["patterns"][0]["status"] == "hits_found"
        assert checklist["patterns"][1]["status"] == "no_hits"
        assert len(checklist["patterns"][0]["hits"]) == 1
        assert checklist["patterns"][0]["hits"][0]["file"] == "cipher.go"

    def test_serializes_to_yaml(self):
        results = [
            ScanResult(
                pattern=PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
                hits=[PatternHit(file="cipher.go", line=45, content="code")],
            ),
        ]
        checklist = generate_checklist(results, "SEC")
        yaml_str = yaml.safe_dump(checklist, default_flow_style=False)
        loaded = yaml.safe_load(yaml_str)
        assert loaded["agent"] == "SEC"
        assert loaded["patterns"][0]["id"] == "crypto_1"


# ---------------------------------------------------------------------------
# TestFormatPatternHitsMd
# ---------------------------------------------------------------------------


class TestFormatPatternHitsMd:
    def test_formats_hits(self):
        results = [
            ScanResult(
                pattern=PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB mode"),
                hits=[
                    PatternHit(file="cipher.go", line=45, content="cipher.NewCFBEncrypter(block, iv)"),
                    PatternHit(file="cipher.go", line=78, content="cipher.NewCFBDecrypter(block, iv)"),
                ],
            ),
        ]
        md = format_pattern_hits_md(results)
        assert "## Pre-Scan Pattern Hits" in md
        assert "cipher.go:45" in md
        assert "cipher.go:78" in md
        assert "NewCFBEncrypter" in md
        assert "MUST investigate" in md

    def test_empty_when_no_hits(self):
        results = [
            ScanResult(
                pattern=PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
                hits=[],
            ),
        ]
        md = format_pattern_hits_md(results)
        assert md == ""

    def test_multiple_categories(self):
        results = [
            ScanResult(
                pattern=PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
                hits=[PatternHit(file="cipher.go", line=45, content="code")],
            ),
            ScanResult(
                pattern=PatternDef(id="tls_1", category="TLS", grep_pattern="InsecureSkipVerify", description="TLS skip"),
                hits=[PatternHit(file="config.go", line=10, content="InsecureSkipVerify: true")],
            ),
        ]
        md = format_pattern_hits_md(results)
        assert "crypto_1" in md
        assert "tls_1" in md
        assert "cipher.go:45" in md
        assert "config.go:10" in md


# ---------------------------------------------------------------------------
# Edge Case Tests: Extract Patterns
# ---------------------------------------------------------------------------


class TestExtractPatternsEdgeCases:
    def test_empty_string(self):
        assert extract_patterns("", "SEC") == []

    def test_detection_section_at_eof(self):
        """Detection Patterns section with no following ## section."""
        text = (
            "## Detection Patterns\n\n"
            "**Category:**\n"
            "- Look for `SomePattern` in code\n"
        )
        patterns = extract_patterns(text, "SEC")
        assert len(patterns) == 1
        assert patterns[0].grep_pattern == "SomePattern"

    def test_backtick_inside_code_block(self):
        """Triple-backtick code blocks should still extract inner backticks."""
        text = (
            "## Detection Patterns\n\n"
            "**Crypto:**\n"
            "- Uses `NewCFBEncrypter` for encryption\n"
            "```\n"
            "example code\n"
            "```\n"
        )
        patterns = extract_patterns(text, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "NewCFBEncrypter" in grep_strings

    def test_pattern_with_shell_metacharacters(self):
        """Patterns with | & $ should still be extracted (grep --fixed-strings handles them)."""
        text = (
            "## Detection Patterns\n\n"
            "**Misc:**\n"
            "- Check for `resp.Allowed = true` pattern\n"
            "- Check for `cmd | shell` pipes\n"
        )
        patterns = extract_patterns(text, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "resp.Allowed = true" in grep_strings
        assert "cmd | shell" in grep_strings

    def test_unicode_pattern(self):
        text = (
            "## Detection Patterns\n\n"
            "**i18n:**\n"
            "- Check for `ошибка_авторизации` in logs\n"
        )
        patterns = extract_patterns(text, "SEC")
        assert len(patterns) == 1
        assert patterns[0].grep_pattern == "ошибка_авторизации"

    def test_very_long_backtick_content_skipped(self):
        """Backtick content over 80 chars with spaces should be skipped (likely a sentence, not a grep pattern)."""
        text = (
            "## Detection Patterns\n\n"
            "**Misc:**\n"
            "- `" + "a " * 50 + "` is too long\n"
            "- `shortPattern` is fine\n"
        )
        patterns = extract_patterns(text, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "shortPattern" in grep_strings
        assert len(patterns) == 1

    def test_multiple_backticks_on_same_line(self):
        text = (
            "## Detection Patterns\n\n"
            "**Crypto:**\n"
            "- Use `sha1.New()` or `md5.New()` for hashing\n"
        )
        patterns = extract_patterns(text, "SEC")
        grep_strings = [p.grep_pattern for p in patterns]
        assert "sha1.New()" in grep_strings
        assert "md5.New()" in grep_strings

    def test_no_backtick_patterns_in_section(self):
        text = (
            "## Detection Patterns\n\n"
            "Check for common issues.\n"
            "No backtick patterns here.\n"
        )
        patterns = extract_patterns(text, "SEC")
        assert patterns == []


# ---------------------------------------------------------------------------
# Edge Case Tests: Run Prescan
# ---------------------------------------------------------------------------


class TestRunPrescanEdgeCases:
    def test_nonexistent_source_dir(self):
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
        ]
        results = run_prescan("/nonexistent/path/that/doesnt/exist", patterns)
        assert results[0].status == "no_hits"

    def test_binary_files_ignored(self, tmp_path):
        """Binary files should not produce valid grep output."""
        (tmp_path / "binary.go").write_bytes(b"\x00\x01\x02NewCFBEncrypter\xff\xfe")
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        # grep may or may not match binary; either is acceptable
        assert isinstance(results[0].hits, list)

    def test_symlink_to_file(self, tmp_path):
        real = tmp_path / "real.go"
        real.write_text("NewCFBEncrypter\n")
        link = tmp_path / "link.go"
        link.symlink_to(real)
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert results[0].status == "hits_found"

    def test_broken_symlink(self, tmp_path):
        link = tmp_path / "broken.go"
        link.symlink_to(tmp_path / "nonexistent.go")
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert results[0].status == "no_hits"

    def test_file_with_colons_in_content(self, tmp_path):
        """Grep output splitting on : must handle content with colons."""
        (tmp_path / "config.yaml").write_text(
            "tls:\n  insecureSkipVerify: true\n  cert: /path/to/cert\n"
        )
        patterns = [
            PatternDef(id="tls_1", category="TLS", grep_pattern="insecureSkipVerify: true", description="TLS"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert results[0].status == "hits_found"
        assert ":" in results[0].hits[0].content

    def test_grep_special_chars_fixed_strings(self, tmp_path):
        """Patterns with regex metacharacters work due to --fixed-strings."""
        (tmp_path / "code.go").write_text('verbs=* on RBAC\n')
        patterns = [
            PatternDef(id="rbac_1", category="RBAC", grep_pattern="verbs=*", description="Wildcard"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert results[0].status == "hits_found"

    def test_skips_pkg_mod(self, tmp_path):
        """pkg/mod/ paths (Go module cache) should be filtered out."""
        mod_dir = tmp_path / "pkg" / "mod" / "example.com"
        mod_dir.mkdir(parents=True)
        (mod_dir / "crypto.go").write_text("NewCFBEncrypter\n")
        patterns = [
            PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
        ]
        results = run_prescan(str(tmp_path), patterns)
        assert results[0].status == "no_hits"


# ---------------------------------------------------------------------------
# Edge Case Tests: Save/Load Prescan
# ---------------------------------------------------------------------------


class TestSaveLoadPrescan:
    def test_roundtrip(self, tmp_path):
        results = {
            "SEC": [
                ScanResult(
                    pattern=PatternDef(id="crypto_1", category="Crypto", grep_pattern="NewCFBEncrypter", description="CFB"),
                    hits=[PatternHit(file="cipher.go", line=45, content="code")],
                ),
            ],
        }
        path = save_prescan(results, str(tmp_path))
        assert os.path.isfile(path)
        loaded = load_prescan(str(tmp_path))
        assert "SEC" in loaded
        assert loaded["SEC"]["patterns"][0]["id"] == "crypto_1"
        assert loaded["SEC"]["patterns"][0]["status"] == "hits_found"

    def test_load_missing_file(self, tmp_path):
        loaded = load_prescan(str(tmp_path))
        assert loaded is None

    def test_load_corrupt_yaml(self, tmp_path):
        (tmp_path / "pattern-scan.yaml").write_text("{{invalid yaml: [")
        loaded = load_prescan(str(tmp_path))
        assert loaded is None or loaded == {}

    def test_load_non_dict_yaml(self, tmp_path):
        (tmp_path / "pattern-scan.yaml").write_text("- just\n- a\n- list\n")
        loaded = load_prescan(str(tmp_path))
        # Should return None or empty dict, not a list
        assert loaded is None or isinstance(loaded, dict)

    def test_save_empty_results(self, tmp_path):
        path = save_prescan({}, str(tmp_path))
        assert os.path.isfile(path)
        loaded = load_prescan(str(tmp_path))
        assert loaded == {}


# ---------------------------------------------------------------------------
# Edge Case Tests: FSM Integration (_get_agent_prescan)
# ---------------------------------------------------------------------------


class TestGetAgentPrescan:
    """Test _get_agent_prescan from fsm.py with malformed inputs."""

    def _call(self, prescan_data, agent_prefix):
        from ..fsm import _get_agent_prescan
        return _get_agent_prescan(prescan_data, agent_prefix)

    def test_prescan_data_is_none(self):
        md, yaml_str = self._call(None, "SEC")
        assert md == ""
        assert yaml_str == ""

    def test_prescan_data_is_list(self):
        md, yaml_str = self._call(["not", "a", "dict"], "SEC")
        assert md == ""
        assert yaml_str == ""

    def test_agent_not_in_prescan(self):
        md, yaml_str = self._call({"PERF": {"agent": "PERF", "patterns": []}}, "SEC")
        assert md == ""
        assert yaml_str == ""

    def test_agent_data_is_string(self):
        md, yaml_str = self._call({"SEC": "not a dict"}, "SEC")
        assert md == ""
        assert yaml_str == ""

    def test_patterns_is_none(self):
        md, yaml_str = self._call({"SEC": {"agent": "SEC", "patterns": None}}, "SEC")
        assert md == ""
        assert yaml_str == ""

    def test_patterns_is_string(self):
        md, yaml_str = self._call({"SEC": {"agent": "SEC", "patterns": "wrong type"}}, "SEC")
        assert md == ""
        assert yaml_str == ""

    def test_pattern_entry_is_string(self):
        md, yaml_str = self._call(
            {"SEC": {"agent": "SEC", "patterns": ["not a dict", "another string"]}},
            "SEC",
        )
        # Should not crash, should produce empty hits
        assert isinstance(md, str)
        assert isinstance(yaml_str, str)

    def test_hit_missing_file_key(self):
        md, yaml_str = self._call(
            {"SEC": {"agent": "SEC", "patterns": [{
                "id": "test_1", "grep": "pattern", "category": "cat",
                "status": "hits_found",
                "hits": [{"line": 1, "content": "code"}],
            }]}},
            "SEC",
        )
        assert "?" in md  # Missing file replaced with ?

    def test_hit_is_not_dict(self):
        md, yaml_str = self._call(
            {"SEC": {"agent": "SEC", "patterns": [{
                "id": "test_1", "grep": "pattern", "category": "cat",
                "status": "hits_found",
                "hits": ["not a dict", 42],
            }]}},
            "SEC",
        )
        # Should not crash
        assert isinstance(md, str)
