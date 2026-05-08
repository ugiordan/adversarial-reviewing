import json
import os
import re
import sys
from pathlib import Path
from ..subprocess_utils import run_script, run_python_script, ScriptError

ResolutionError = ScriptError


def _parse_vote_position(content: str) -> str:
    """Extract vote position (Agree/Challenge/Abstain) from agent output."""
    content_lower = content.lower()
    if "challenge" in content_lower:
        return "Challenge"
    if "agree" in content_lower:
        return "Agree"
    if "abstain" in content_lower:
        return "Abstain"
    return "Abstain"


def _build_votes_json(cache_dir: str) -> str | None:
    """Build votes.json from challenge round outputs. Returns path or None."""
    outputs_dir = os.path.join(cache_dir, "outputs")
    if not os.path.isdir(outputs_dir):
        return None

    votes = []
    challenge_pattern = re.compile(r"^(\w+)-challenge-iter(\d+)\.md$")
    for fname in sorted(os.listdir(outputs_dir)):
        m = challenge_pattern.match(fname)
        if not m:
            continue
        agent_id = m.group(1)
        iteration = int(m.group(2))
        fpath = os.path.join(outputs_dir, fname)
        try:
            content = Path(fpath).read_text()
        except (OSError, UnicodeDecodeError):
            continue
        position = _parse_vote_position(content)
        votes.append({
            "agent": agent_id,
            "iteration": iteration,
            "position": position,
            "file": fname,
        })

    if not votes:
        return None

    votes_path = os.path.join(cache_dir, "votes.json")
    Path(votes_path).write_text(json.dumps(votes, indent=2))
    return votes_path


def run_resolution(cache_dir: str, skill_dir: str) -> dict:
    outputs_dir = os.path.join(cache_dir, "outputs")
    dedup_script = os.path.join(skill_dir, "scripts", "deduplicate.sh")

    if not os.path.isfile(dedup_script):
        raise FileNotFoundError(f"deduplicate.sh not found at {dedup_script}")

    result = run_script(dedup_script, [outputs_dir], timeout=30)

    # Best-effort: resolve votes from challenge round
    try:
        votes_path = _build_votes_json(cache_dir)
        if votes_path:
            resolve_script = os.path.join(skill_dir, "scripts", "resolve-votes.py")
            if os.path.isfile(resolve_script):
                vote_result = run_python_script(
                    resolve_script, [votes_path], timeout=30,
                )
                if vote_result:
                    result.update(vote_result)
    except (ScriptError, FileNotFoundError, OSError) as e:
        print(json.dumps({
            "warning": "resolve_votes_skipped",
            "message": f"resolve-votes.py: {e}",
        }), file=sys.stderr)

    # Best-effort: cross-specialist deduplication
    try:
        if os.path.isfile(dedup_script):
            run_script(dedup_script, ["--cross-specialist", outputs_dir], timeout=30)
    except (ScriptError, OSError) as e:
        print(json.dumps({
            "warning": "cross_specialist_dedup_skipped",
            "message": f"deduplicate.sh --cross-specialist: {e}",
        }), file=sys.stderr)

    return result
