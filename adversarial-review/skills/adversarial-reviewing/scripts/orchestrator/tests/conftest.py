# scripts/orchestrator/tests/conftest.py
import os
import sys
import pytest

hooks_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "hooks"))
if hooks_dir not in sys.path:
    sys.path.insert(0, hooks_dir)


@pytest.fixture(autouse=True)
def _clear_fsm_caches():
    from orchestrator import fsm
    fsm._profile_config_cache.clear()
    fsm._templates_cache.clear()
    yield
    fsm._profile_config_cache.clear()
    fsm._templates_cache.clear()


@pytest.fixture
def tmp_cache_dir(tmp_path):
    cache = tmp_path / "cache-test"
    cache.mkdir()
    (cache / "prompts").mkdir()
    (cache / "outputs").mkdir()
    return cache


@pytest.fixture
def skill_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@pytest.fixture
def code_profile_dir(skill_dir):
    return os.path.join(skill_dir, "profiles", "code")
