import pytest
from unittest.mock import patch
from orchestrator.convergence import check_convergence


class TestCheckConvergence:
    @patch("orchestrator.convergence.run_script")
    def test_converged(self, mock_run):
        mock_run.return_value = {"converged": True, "delta": 0}
        converged, data = check_convergence("/tmp/curr", "/tmp/prev", "/skill")
        assert converged is True

    @patch("orchestrator.convergence.run_script")
    def test_not_converged(self, mock_run):
        mock_run.return_value = {"converged": False, "delta": 3}
        converged, data = check_convergence("/tmp/curr", "/tmp/prev", "/skill")
        assert converged is False
