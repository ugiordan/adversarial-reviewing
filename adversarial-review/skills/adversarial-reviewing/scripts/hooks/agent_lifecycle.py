"""Agent lifecycle hooks: SubagentStart/Stop event recording and reasoning capture."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


def record_agent_start(cache_dir: str, agent_id: str, phase: str,
                       iteration: int, tools: list[str],
                       effort: str, max_turns: int) -> None:
    event = {
        "event": "start",
        "agent": agent_id,
        "phase": phase,
        "iteration": iteration,
        "tools": tools,
        "effort": effort,
        "max_turns": max_turns,
        "timestamp": time.time(),
    }
    events_path = Path(cache_dir) / "agent-events.jsonl"
    with open(events_path, "a") as f:
        f.write(json.dumps(event) + "\n")


def record_agent_stop(cache_dir: str, agent_id: str, phase: str,
                      iteration: int,
                      thinking_blocks: list[dict] = None,
                      tool_calls: list[dict] = None,
                      tokens: dict = None,
                      duration_ms: float = 0) -> None:
    event = {
        "event": "stop",
        "agent": agent_id,
        "phase": phase,
        "iteration": iteration,
        "duration_ms": duration_ms,
        "tokens": tokens or {},
        "timestamp": time.time(),
    }
    events_path = Path(cache_dir) / "agent-events.jsonl"
    with open(events_path, "a") as f:
        f.write(json.dumps(event) + "\n")

    reasoning = {
        "agent": agent_id,
        "phase": phase,
        "iteration": iteration,
        "thinking_blocks": thinking_blocks or [],
        "tool_calls": tool_calls or [],
        "tokens": tokens or {},
        "duration_ms": duration_ms,
    }
    reasoning_dir = Path(cache_dir) / "reasoning"
    reasoning_dir.mkdir(exist_ok=True)
    phase_label = phase.replace("-", "_")
    fname = f"{agent_id}-{phase_label}-iter{iteration}.json"
    path = reasoning_dir / fname
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(reasoning, indent=2))
    tmp.replace(path)
