import pytest
from unittest.mock import patch, MagicMock
from orchestrator.cache import init_cache, populate_code, populate_templates, CacheError


class TestInitCache:
    @patch("orchestrator.cache._run_manage_cache")
    def test_returns_cache_dir(self, mock_run):
        mock_run.return_value = {
            "cache_dir": "/tmp/cache-abc123",
            "session_hex": "abc123",
        }
        result = init_cache("abc123", "/skill/dir", "code")
        assert result["cache_dir"] == "/tmp/cache-abc123"
        mock_run.assert_called_once()

    @patch("orchestrator.cache._run_manage_cache")
    def test_error_raises(self, mock_run):
        mock_run.side_effect = CacheError("init failed")
        with pytest.raises(CacheError):
            init_cache("abc123", "/skill/dir", "code")
