from __future__ import annotations

import json
from pathlib import Path
from .types import AgentConfig, DispatchAgent


def write_dispatch(cache_dir: str | Path, phase: str, iteration: int,
                   agents: list[DispatchAgent], parallel: bool = True,
                   retry: bool = False,
                   agent_configs: dict[str, AgentConfig] = None,
                   hooks: dict = None) -> None:
    agent_data = []
    for a in agents:
        entry = {
            "id": a.id, "description": a.description,
            "prompt_file": a.prompt_file, "output_file": a.output_file,
        }
        if agent_configs and a.id in agent_configs:
            cfg = agent_configs[a.id]
            entry["tools"] = cfg.tools
            entry["effort"] = cfg.effort
            entry["maxTurns"] = cfg.max_turns
        agent_data.append(entry)

    data = {
        "dispatch_version": "2.0",
        "phase": phase,
        "iteration": iteration,
        "parallel": parallel,
        "agents": agent_data,
    }
    if retry:
        data["retry"] = True
    if hooks:
        data["hooks"] = hooks
    _write_json(cache_dir, data)


def write_scope_confirmation(cache_dir: str | Path, message_file: str) -> None:
    _write_json(cache_dir, {
        "dispatch_version": "1.0",
        "phase": "confirm-scope",
        "action": "ask_user",
        "message_file": message_file,
    })


def write_terminal(cache_dir: str | Path, report_path: str, summary: str) -> None:
    _write_json(cache_dir, {
        "dispatch_version": "1.0",
        "done": True,
        "report_path": report_path,
        "summary": summary,
    })


def write_dispatch_v3(
    cache_dir: str | Path,
    phase: str,
    iteration: int,
    agents: list[dict],
    parallel: bool = True,
) -> None:
    """Write dispatch.json with v3.0 schema (subagent dispatch)."""
    dispatch = {
        "dispatch_version": "3.0",
        "phase": phase,
        "iteration": iteration,
        "parallel": parallel,
        "agents": agents,
    }
    dispatch_path = Path(cache_dir) / "dispatch.json"
    with open(dispatch_path, "w") as f:
        json.dump(dispatch, f, indent=2)
        f.write("\n")


def read_dispatch(cache_dir: str | Path) -> dict:
    path = Path(cache_dir) / "dispatch.json"
    return json.loads(path.read_text())


def _write_json(cache_dir: str | Path, data: dict) -> None:
    path = Path(cache_dir) / "dispatch.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)
