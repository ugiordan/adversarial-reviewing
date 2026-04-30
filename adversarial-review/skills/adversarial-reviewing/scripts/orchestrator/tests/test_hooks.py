import json
import os
import sys
import pytest

# Add hooks directory to path for imports
hooks_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "hooks"))
if hooks_dir not in sys.path:
    sys.path.insert(0, hooks_dir)


class TestPreDispatchValidation:
    def test_detects_cross_agent_reference(self):
        from pre_dispatch_validate import check_prompt_isolation
        prompt = "Review the code.\nSee outputs/CORR-phase1-iter1.md for details."
        result = check_prompt_isolation(prompt, agent_id="SEC",
                                        all_agent_ids=["SEC", "CORR", "QUAL"])
        assert not result["passed"]
        assert "CORR" in result["violation"]

    def test_detects_cross_agent_with_cache_dir(self):
        from pre_dispatch_validate import check_prompt_isolation
        prompt = "See /tmp/cache/outputs/CORR-phase1-iter1.md"
        result = check_prompt_isolation(prompt, agent_id="SEC",
                                        all_agent_ids=["SEC", "CORR"],
                                        cache_dir="/tmp/cache")
        assert not result["passed"]

    def test_allows_own_references(self):
        from pre_dispatch_validate import check_prompt_isolation
        prompt = "Review the code.\nSee outputs/SEC-phase1-iter1.md for prior work."
        result = check_prompt_isolation(prompt, agent_id="SEC",
                                        all_agent_ids=["SEC", "CORR", "QUAL"])
        assert result["passed"]

    def test_no_false_positive_on_source_paths(self):
        from pre_dispatch_validate import check_prompt_isolation
        prompt = "Review /workspace/SEC-team/project/file.py"
        result = check_prompt_isolation(prompt, agent_id="QUAL",
                                        all_agent_ids=["SEC", "QUAL"])
        assert result["passed"]

    def test_validates_control_fields(self):
        from pre_dispatch_validate import check_control_fields
        agent_entry = {
            "id": "SEC", "tools": ["Read"], "effort": "high", "maxTurns": 15,
        }
        result = check_control_fields(agent_entry)
        assert result["passed"]

    def test_rejects_forbidden_tools(self):
        from pre_dispatch_validate import check_control_fields
        agent_entry = {
            "id": "SEC", "tools": ["Read", "Bash"], "effort": "high", "maxTurns": 15,
        }
        result = check_control_fields(agent_entry)
        assert not result["passed"]
        assert "Bash" in result["violation"]

    def test_rejects_invalid_effort(self):
        from pre_dispatch_validate import check_control_fields
        agent_entry = {
            "id": "SEC", "tools": ["Read"], "effort": "ultra", "maxTurns": 15,
        }
        result = check_control_fields(agent_entry)
        assert not result["passed"]

    def test_rejects_out_of_range_max_turns(self):
        from pre_dispatch_validate import check_control_fields
        agent_entry = {
            "id": "SEC", "tools": ["Read"], "effort": "high", "maxTurns": 100,
        }
        result = check_control_fields(agent_entry)
        assert not result["passed"]

    def test_no_cross_reference_with_challenge_files(self):
        from pre_dispatch_validate import check_prompt_isolation
        prompt = "Review. Check outputs/QUAL-challenge-iter2.md"
        result = check_prompt_isolation(prompt, agent_id="SEC",
                                        all_agent_ids=["SEC", "QUAL"])
        assert not result["passed"]


class TestPostOutputValidation:
    def test_detects_finding_template(self):
        from post_output_validate import check_finding_structure
        output = (
            "### SEC-001: SQL Injection\n"
            "**Severity:** Important\n"
            "**Confidence:** High\n"
            "**Evidence:** User input passed to query\n"
        )
        result = check_finding_structure(output)
        assert result["has_findings"]
        assert result["has_severity"]
        assert result["has_confidence"]
        assert result["has_evidence"]

    def test_detects_no_findings_marker(self):
        from post_output_validate import check_finding_structure
        output = "NO_FINDINGS_REPORTED"
        result = check_finding_structure(output)
        assert result["has_findings"] is False
        assert result["valid_no_findings"]

    def test_detects_comparative_reasoning(self):
        from post_output_validate import check_comparative_reasoning
        output = (
            "However, this could also be a parameterized query that is safe.\n"
        )
        result = check_comparative_reasoning(output)
        assert result["has_comparative"]

    def test_flags_missing_comparative_reasoning(self):
        from post_output_validate import check_comparative_reasoning
        output = "This is definitely a vulnerability.\n"
        result = check_comparative_reasoning(output)
        assert not result["has_comparative"]


class TestPostCompactReinject:
    def test_reads_compaction_file(self, tmp_path):
        from post_compact_reinject import load_compaction_content
        compaction_dir = tmp_path / "compaction"
        compaction_dir.mkdir()
        (compaction_dir / "SEC-self-refinement-iter1.md").write_text(
            "## Context Recovery\n**Your role:** Security auditor"
        )
        content = load_compaction_content(
            str(tmp_path), agent_id="SEC",
            phase="self-refinement", iteration=1,
        )
        assert "Security auditor" in content

    def test_returns_empty_when_missing(self, tmp_path):
        from post_compact_reinject import load_compaction_content
        content = load_compaction_content(
            str(tmp_path), agent_id="SEC",
            phase="self-refinement", iteration=1,
        )
        assert content == ""


class TestAgentLifecycle:
    def test_writes_start_event(self, tmp_path):
        from agent_lifecycle import record_agent_start
        record_agent_start(
            str(tmp_path), agent_id="SEC", phase="self-refinement",
            iteration=1, tools=["Read"], effort="high", max_turns=15,
        )
        events_path = tmp_path / "agent-events.jsonl"
        assert events_path.exists()
        event = json.loads(events_path.read_text().strip())
        assert event["agent"] == "SEC"
        assert event["event"] == "start"
        assert event["tools"] == ["Read"]

    def test_writes_stop_event(self, tmp_path):
        from agent_lifecycle import record_agent_stop
        reasoning_dir = tmp_path / "reasoning"
        reasoning_dir.mkdir()
        record_agent_stop(
            str(tmp_path), agent_id="SEC", phase="self-refinement",
            iteration=1,
            thinking_blocks=[{"turn": 1, "thinking": "Analyzing auth flow"}],
            tool_calls=[{"turn": 1, "tool": "Read", "input": {"file_path": "auth.py"}, "result_length": 500}],
            tokens={"input": 5000, "output": 2000, "thinking": 3000},
            duration_ms=15000,
        )
        events_path = tmp_path / "agent-events.jsonl"
        assert events_path.exists()
        event = json.loads(events_path.read_text().strip())
        assert event["event"] == "stop"

    def test_writes_reasoning_log(self, tmp_path):
        from agent_lifecycle import record_agent_stop
        record_agent_stop(
            str(tmp_path), agent_id="SEC", phase="self-refinement",
            iteration=1,
            thinking_blocks=[{"turn": 1, "thinking": "Analyzing auth flow"}],
            tool_calls=[{"turn": 1, "tool": "Read", "input": {"file_path": "auth.py"}, "result_length": 500}],
            tokens={"input": 5000, "output": 2000, "thinking": 3000},
            duration_ms=15000,
        )
        path = tmp_path / "reasoning" / "SEC-self_refinement-iter1.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["agent"] == "SEC"
        assert data["thinking_blocks"][0]["thinking"] == "Analyzing auth flow"
        assert data["tokens"]["thinking"] == 3000

    def test_multiple_events_append(self, tmp_path):
        from agent_lifecycle import record_agent_start, record_agent_stop
        record_agent_start(str(tmp_path), "SEC", "self-refinement", 1, ["Read"], "high", 15)
        record_agent_stop(str(tmp_path), "SEC", "self-refinement", 1, duration_ms=5000)
        events = (tmp_path / "agent-events.jsonl").read_text().strip().split("\n")
        assert len(events) == 2
        assert json.loads(events[0])["event"] == "start"
        assert json.loads(events[1])["event"] == "stop"
