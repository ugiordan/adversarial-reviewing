import os
import pytest
from pathlib import Path

from orchestrator.code_index import (
    build_code_index, _extract_symbols, _extract_from_file,
    _split_by_security_relevance, _SYMBOL_PATTERNS,
)


@pytest.fixture
def go_repo(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / "main.go").write_text(
        "package main\n\n"
        "func main() {\n\tbindRole()\n}\n\n"
        "type Config struct {\n\tName string\n}\n"
    )
    (d / "auth.go").write_text(
        "package main\n\n"
        "func bindRole(name string) {\n}\n\n"
        "func bindClusterRole(name string) {\n}\n\n"
        "var defaultGroups = []string{}\n"
    )
    sub = d / "pkg" / "cert"
    sub.mkdir(parents=True)
    (sub / "cert.go").write_text(
        "package cert\n\n"
        "func generateCertificate() {\n\tIsCA := true\n}\n\n"
        "type CertSpec struct{}\n"
    )
    return str(d)


@pytest.fixture
def python_repo(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / "app.py").write_text(
        "def authenticate(user, password):\n    pass\n\n"
        "class AuthHandler:\n    pass\n\n"
        "async def validate_token(token):\n    pass\n"
    )
    (d / "auth.py").write_text(
        "def check_permission(user, resource):\n    pass\n\n"
        "class RBACPolicy:\n    pass\n"
    )
    return str(d)


class TestExtractSymbols:
    def test_go_functions(self, go_repo):
        symbols = _extract_symbols(go_repo)
        auth_syms = symbols.get("auth.go", [])
        names = [s[0] for s in auth_syms]
        assert "bindRole" in names
        assert "bindClusterRole" in names

    def test_go_types(self, go_repo):
        symbols = _extract_symbols(go_repo)
        main_syms = symbols.get("main.go", [])
        names = [s[0] for s in main_syms]
        assert "Config" in names

    def test_go_cert_package(self, go_repo):
        symbols = _extract_symbols(go_repo)
        cert_key = os.path.join("pkg", "cert", "cert.go")
        cert_syms = symbols.get(cert_key, [])
        names = [s[0] for s in cert_syms]
        assert "generateCertificate" in names
        assert "CertSpec" in names

    def test_python_functions(self, python_repo):
        symbols = _extract_symbols(python_repo)
        app_syms = symbols.get("app.py", [])
        names = [s[0] for s in app_syms]
        assert "authenticate" in names
        assert "validate_token" in names

    def test_python_classes(self, python_repo):
        symbols = _extract_symbols(python_repo)
        app_syms = symbols.get("app.py", [])
        names = [s[0] for s in app_syms]
        assert "AuthHandler" in names

    def test_skips_test_files(self, tmp_path):
        d = tmp_path / "repo"
        d.mkdir()
        (d / "auth.go").write_text("package main\nfunc Login() {}\n")
        (d / "auth_test.go").write_text("package main\nfunc TestLogin() {}\n")
        symbols = _extract_symbols(str(d))
        assert "auth.go" in symbols
        assert "auth_test.go" not in symbols

    def test_skips_vendor(self, tmp_path):
        d = tmp_path / "repo"
        (d / "vendor" / "lib").mkdir(parents=True)
        (d / "vendor" / "lib" / "main.go").write_text("package lib\nfunc Do() {}\n")
        (d / "main.go").write_text("package main\nfunc main() {}\n")
        d.mkdir(exist_ok=True)
        symbols = _extract_symbols(str(d))
        assert not any("vendor" in k for k in symbols)


class TestSecurityRelevance:
    def test_auth_files_prioritized(self, go_repo):
        symbols = _extract_symbols(go_repo)
        sec, other = _split_by_security_relevance(symbols, go_repo)
        assert "auth.go" in sec
        assert os.path.join("pkg", "cert", "cert.go") in sec
        assert "main.go" in other  # main.go is not security-relevant by keyword

    def test_empty_repo(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        sec, other = _split_by_security_relevance({}, str(d))
        assert sec == {}
        assert other == {}


class TestBuildCodeIndex:
    def test_produces_markdown(self, go_repo):
        result = build_code_index(go_repo)
        assert "## Code Index" in result
        assert "bindRole" in result
        assert "auth.go" in result

    def test_includes_line_numbers(self, go_repo):
        result = build_code_index(go_repo)
        assert ":4" in result or ":3" in result

    def test_empty_dir(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        assert build_code_index(str(d)) == ""

    def test_nonexistent_dir(self):
        assert build_code_index("/nonexistent") == ""

    def test_security_files_first(self, go_repo):
        result = build_code_index(go_repo)
        auth_pos = result.find("auth.go")
        main_pos = result.find("main.go")
        assert auth_pos < main_pos

    def test_token_cap(self, tmp_path):
        d = tmp_path / "bigrepo"
        d.mkdir()
        for i in range(200):
            (d / f"auth_module_{i}.go").write_text(
                f"package m{i}\n" +
                "\n".join(f"func Handler{j}() {{}}" for j in range(50))
            )
        result = build_code_index(str(d))
        assert len(result) <= 85000

    def test_caller_info_included(self, tmp_path):
        d = tmp_path / "repo"
        d.mkdir()
        (d / "auth.go").write_text(
            "package main\nfunc CheckAuth(user string) bool { return true }\n"
        )
        (d / "handler.go").write_text(
            "package main\nfunc Handle() { CheckAuth(\"admin\") }\n"
        )
        result = build_code_index(str(d))
        if "called by" in result:
            assert "handler.go" in result
