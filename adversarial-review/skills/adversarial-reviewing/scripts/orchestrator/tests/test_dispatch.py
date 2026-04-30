import json
import pytest
from orchestrator.dispatch import (
    write_dispatch, write_dispatch_v3, write_scope_confirmation,
    write_terminal, read_dispatch,
)
from orchestrator.types import DispatchAgent


class TestWriteDispatch:
    def test_writes_agent_dispatch(self, tmp_cache_dir):
        agents = [
            DispatchAgent("SEC", "SEC: iter 1",
                          str(tmp_cache_dir / "prompts/SEC.md"),
                          str(tmp_cache_dir / "outputs/SEC.md")),
        ]
        write_dispatch(tmp_cache_dir, "self-refinement", 1, agents, parallel=True)
        data = json.loads((tmp_cache_dir / "dispatch.json").read_text())
        assert data["dispatch_version"] == "2.0"
        assert data["phase"] == "self-refinement"
        assert len(data["agents"]) == 1
        assert data["parallel"] is True

    def test_writes_retry_flag(self, tmp_cache_dir):
        agents = [
            DispatchAgent("SEC", "SEC: retry",
                          str(tmp_cache_dir / "prompts/SEC.md"),
                          str(tmp_cache_dir / "outputs/SEC.md")),
        ]
        write_dispatch(tmp_cache_dir, "self-refinement", 1, agents, retry=True)
        data = json.loads((tmp_cache_dir / "dispatch.json").read_text())
        assert data["retry"] is True


class TestWriteTerminal:
    def test_writes_done(self, tmp_cache_dir):
        write_terminal(tmp_cache_dir, "/tmp/report.md", "Complete: 5 findings")
        data = json.loads((tmp_cache_dir / "dispatch.json").read_text())
        assert data["done"] is True
        assert data["report_path"] == "/tmp/report.md"


class TestReadDispatch:
    def test_reads_dispatch(self, tmp_cache_dir):
        (tmp_cache_dir / "dispatch.json").write_text(json.dumps({
            "dispatch_version": "1.0", "phase": "test", "agents": [],
        }))
        data = read_dispatch(tmp_cache_dir)
        assert data["phase"] == "test"


class TestDispatchV2:
    def test_writes_control_fields(self, tmp_cache_dir):
        from orchestrator.types import AgentConfig
        agents = [DispatchAgent(
            id="SEC", description="SEC: Test",
            prompt_file="/tmp/p.md", output_file="/tmp/o.md",
        )]
        agent_configs = {"SEC": AgentConfig(
            prefix="SEC", file="sec.md",
            tools=["Read"], effort="high", max_turns=15,
        )}
        write_dispatch(tmp_cache_dir, "self-refinement", 1, agents,
                       agent_configs=agent_configs)
        data = read_dispatch(tmp_cache_dir)
        assert data["dispatch_version"] == "2.0"
        assert data["agents"][0]["tools"] == ["Read"]
        assert data["agents"][0]["effort"] == "high"
        assert data["agents"][0]["maxTurns"] == 15

    def test_v2_without_configs_no_control_fields(self, tmp_cache_dir):
        agents = [DispatchAgent(
            id="SEC", description="SEC: Test",
            prompt_file="/tmp/p.md", output_file="/tmp/o.md",
        )]
        write_dispatch(tmp_cache_dir, "self-refinement", 1, agents)
        data = read_dispatch(tmp_cache_dir)
        assert data["dispatch_version"] == "2.0"
        assert "tools" not in data["agents"][0]

    def test_report_dispatch_has_write_tool(self, tmp_cache_dir):
        from orchestrator.types import AgentConfig
        agents = [DispatchAgent(
            id="REPORT", description="Report Writer",
            prompt_file="/tmp/p.md", output_file="/tmp/o.md",
        )]
        report_config = AgentConfig(
            prefix="REPORT", file="",
            tools=["Read", "Write"], effort="medium", max_turns=8,
        )
        write_dispatch(tmp_cache_dir, "report", 1, agents, parallel=False,
                       agent_configs={"REPORT": report_config})
        data = read_dispatch(tmp_cache_dir)
        assert data["agents"][0]["tools"] == ["Read", "Write"]
        assert data["agents"][0]["maxTurns"] == 8


class TestWriteDispatchV3:
    def test_writes_v3_schema(self, tmp_path):
        agents = [
            {"id": "SEC", "subagent_type": "review-specialist",
             "dispatch_path": str(tmp_path / "dispatch" / "SEC")},
        ]
        write_dispatch_v3(str(tmp_path), "self-refinement", 1, agents)
        data = json.loads((tmp_path / "dispatch.json").read_text())
        assert data["dispatch_version"] == "3.0"
        assert data["agents"][0]["subagent_type"] == "review-specialist"
        assert "prompt_file" not in data["agents"][0]

    def test_v3_parallel_flag(self, tmp_path):
        agents = [
            {"id": "SEC", "subagent_type": "review-specialist",
             "dispatch_path": str(tmp_path / "dispatch" / "SEC")},
            {"id": "PERF", "subagent_type": "review-specialist",
             "dispatch_path": str(tmp_path / "dispatch" / "PERF")},
        ]
        write_dispatch_v3(str(tmp_path), "self-refinement", 1, agents, parallel=True)
        data = json.loads((tmp_path / "dispatch.json").read_text())
        assert data["parallel"] is True
        assert len(data["agents"]) == 2
