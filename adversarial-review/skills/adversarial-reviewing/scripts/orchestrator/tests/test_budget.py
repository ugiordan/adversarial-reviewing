import pytest
from unittest.mock import patch
from orchestrator.budget import init_budget, add_consumption, get_status, BudgetError


class TestInitBudget:
    @patch("orchestrator.budget._run_track_budget")
    def test_returns_state(self, mock_run):
        mock_run.return_value = {
            "limit": 350000, "consumed": 0,
            "remaining": 350000, "exceeded": False,
        }
        result = init_budget(350000, "/tmp/cache")
        assert result["limit"] == 350000

class TestAddConsumption:
    @patch("orchestrator.budget._run_track_budget")
    def test_adds_chars(self, mock_run):
        mock_run.return_value = {
            "consumed": 50000, "remaining": 300000, "exceeded": False,
        }
        result = add_consumption(50000, "/tmp/cache")
        assert result["consumed"] == 50000

class TestGetStatus:
    @patch("orchestrator.budget._run_track_budget")
    def test_returns_status(self, mock_run):
        mock_run.return_value = {
            "consumed": 100000, "remaining": 250000, "exceeded": False,
        }
        result = get_status("/tmp/cache")
        assert not result["exceeded"]
