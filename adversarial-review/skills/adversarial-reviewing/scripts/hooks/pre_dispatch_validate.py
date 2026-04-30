"""PreToolUse hook: validates prompt isolation and control fields before agent dispatch."""
from __future__ import annotations

import json
import re
import sys

ALLOWED_TOOLS = {"Read", "Write", "Grep", "Glob"}
VALID_EFFORTS = {"low", "medium", "high", "xhigh", "max"}


def check_prompt_isolation(prompt: str, agent_id: str,
                           all_agent_ids: list[str],
                           cache_dir: str = "") -> dict:
    other_ids = [aid for aid in all_agent_ids if aid != agent_id]
    for other in other_ids:
        if cache_dir:
            pattern = re.compile(
                rf"{re.escape(cache_dir)}/outputs/{re.escape(other)}-(phase1|challenge)-iter\d+\.md"
            )
        else:
            pattern = re.compile(
                rf"outputs/{re.escape(other)}-(phase1|challenge)-iter\d+\.md"
            )
        match = pattern.search(prompt)
        if match:
            return {
                "passed": False,
                "violation": f"Prompt references other agent output: {other} ({match.group()})",
            }
    return {"passed": True}


def check_control_fields(agent_entry: dict) -> dict:
    tools = agent_entry.get("tools", [])
    for tool in tools:
        if tool not in ALLOWED_TOOLS:
            return {
                "passed": False,
                "violation": f"Forbidden tool: {tool}. Allowed: {ALLOWED_TOOLS}",
            }
    effort = agent_entry.get("effort", "medium")
    if effort not in VALID_EFFORTS:
        return {
            "passed": False,
            "violation": f"Invalid effort: {effort}. Allowed: {VALID_EFFORTS}",
        }
    max_turns = agent_entry.get("maxTurns", 15)
    if not isinstance(max_turns, int) or max_turns < 1 or max_turns > 50:
        return {
            "passed": False,
            "violation": f"maxTurns out of range: {max_turns}",
        }
    return {"passed": True}


if __name__ == "__main__":
    hook_input = json.loads(sys.stdin.read())
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Agent":
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})
    prompt = tool_input.get("prompt", "")
    dispatch_path = hook_input.get("metadata", {}).get("dispatch_path", "")

    if not dispatch_path:
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)

    try:
        with open(dispatch_path) as f:
            dispatch = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)

    all_ids = [a["id"] for a in dispatch.get("agents", [])]
    current_agent = tool_input.get("description", "").split(":")[0].strip()

    iso_result = check_prompt_isolation(prompt, current_agent, all_ids)
    if not iso_result["passed"]:
        print(json.dumps({
            "decision": "deny",
            "reason": iso_result["violation"],
        }))
        sys.exit(0)

    for agent in dispatch.get("agents", []):
        if agent["id"] == current_agent:
            ctrl_result = check_control_fields(agent)
            if not ctrl_result["passed"]:
                print(json.dumps({
                    "decision": "deny",
                    "reason": ctrl_result["violation"],
                }))
                sys.exit(0)
            break

    print(json.dumps({"decision": "allow"}))
