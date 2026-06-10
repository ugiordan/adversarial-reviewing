"""Direct agent dispatch via claude CLI.

Replaces the Claude Code relay pattern with deterministic subprocess
calls. Each agent gets its own claude session via --print mode.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 1800
_RETRY_DELAY = 10
_MAX_RETRIES = 1


def dispatch_agents(
    dispatch: dict,
    skill_dir: str,
    model: str = "claude-opus-4-6",
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, int]:
    """Dispatch all agents from a dispatch.json entry.

    Returns {agent_id: exit_code} for each agent.
    """
    agents = dispatch.get("agents", [])
    if not agents:
        return {}

    parallel = dispatch.get("parallel", False)
    results = {}

    if parallel and len(agents) > 1:
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            futures = {
                pool.submit(
                    _dispatch_one, agent, skill_dir, model, timeout,
                ): agent["id"]
                for agent in agents
            }
            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    results[agent_id] = future.result()
                except Exception as e:
                    logger.error("Agent %s failed: %s", agent_id, e)
                    results[agent_id] = 1
    else:
        for agent in agents:
            results[agent["id"]] = _dispatch_one(
                agent, skill_dir, model, timeout,
            )

    return results


def _dispatch_one(
    agent_entry: dict,
    skill_dir: str,
    model: str,
    timeout: int,
) -> int:
    """Dispatch a single agent with retry logic."""
    agent_id = agent_entry["id"]
    dispatch_path = agent_entry["dispatch_path"]
    subagent_type = agent_entry.get("subagent_type", "review-specialist")

    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            logger.info("Retrying %s (attempt %d)", agent_id, attempt + 1)
            time.sleep(_RETRY_DELAY)

        rc = _run_claude_agent(
            agent_id, subagent_type, dispatch_path,
            skill_dir, model, timeout,
        )
        if rc == 0:
            return 0

        output_file = os.path.join(dispatch_path, "output.md")
        if os.path.isfile(output_file) and os.path.getsize(output_file) > 100:
            logger.warning(
                "%s exited %d but output.md has content, accepting",
                agent_id, rc,
            )
            return 0

    logger.error("%s failed after %d attempts", agent_id, _MAX_RETRIES + 1)
    return 1


def _run_claude_agent(
    agent_id: str,
    subagent_type: str,
    dispatch_path: str,
    skill_dir: str,
    model: str,
    timeout: int,
) -> int:
    """Run a single claude CLI session for an agent."""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        logger.error("claude CLI not found on PATH")
        return 1

    agent_def_path = _find_agent_def(skill_dir, subagent_type)
    if not agent_def_path:
        logger.error("Agent definition not found for %s in %s", subagent_type, skill_dir)
        return 1

    source_root = ""
    config_path = os.path.join(dispatch_path, "dispatch-config.yaml")
    if os.path.isfile(config_path):
        try:
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            source_root = cfg.get("source_root", "")
        except Exception:
            pass

    plugin_root = _find_plugin_root(skill_dir)

    cmd = [
        claude_bin, "--print",
        "--model", model,
        "--verbose",
        "--output-format", "stream-json",
        "--plugin-dir", plugin_root,
        "--agent", subagent_type,
        "--add-dir", dispatch_path,
        "--dangerously-skip-permissions",
    ]

    if source_root and os.path.isdir(source_root):
        cmd.extend(["--add-dir", source_root])

    prompt = dispatch_path

    logger.info("Dispatching %s (%s) -> %s", agent_id, subagent_type, dispatch_path)

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=dispatch_path,
        )
        proc.stdin.write(prompt.encode("utf-8"))
        proc.stdin.close()

        stdout, stderr = proc.communicate(timeout=timeout)

        stdout_path = os.path.join(dispatch_path, "agent-stdout.log")
        Path(stdout_path).write_bytes(stdout)

        if stderr:
            stderr_path = os.path.join(dispatch_path, "agent-stderr.log")
            Path(stderr_path).write_bytes(stderr)

        if proc.returncode != 0:
            logger.warning(
                "%s exited with code %d. stderr: %s",
                agent_id, proc.returncode,
                stderr.decode("utf-8", errors="replace")[:500],
            )

        return proc.returncode

    except subprocess.TimeoutExpired:
        logger.error("%s timed out after %ds", agent_id, timeout)
        proc.kill()
        proc.wait()
        return 1
    except OSError as e:
        logger.error("%s failed to launch: %s", agent_id, e)
        return 1


def _find_agent_def(skill_dir: str, subagent_type: str) -> str | None:
    """Find agent definition file by searching up from skill_dir."""
    candidates = [
        os.path.join(skill_dir, "agents", f"{subagent_type}.md"),
    ]
    d = skill_dir
    for _ in range(5):
        parent = os.path.dirname(d)
        if parent == d:
            break
        candidates.append(os.path.join(parent, "agents", f"{subagent_type}.md"))
        d = parent

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _find_plugin_root(skill_dir: str) -> str:
    """Find the plugin root directory (contains agents/ and skills/)."""
    d = skill_dir
    for _ in range(5):
        if os.path.isdir(os.path.join(d, "agents")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return skill_dir


def read_dispatch(cache_dir: str) -> dict:
    """Read dispatch.json from cache directory."""
    path = os.path.join(cache_dir, "dispatch.json")
    if not os.path.isfile(path):
        return {}
    with open(path) as f:
        return json.loads(f.read())


def is_done(dispatch: dict) -> bool:
    """Check if the dispatch indicates the review is complete."""
    return dispatch.get("done", False)
