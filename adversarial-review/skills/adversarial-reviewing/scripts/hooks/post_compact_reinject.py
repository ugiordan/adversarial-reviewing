"""PostCompact hook: re-injects constraints after context compression."""
from __future__ import annotations

import json
import os
import sys


def load_compaction_content(cache_dir: str, agent_id: str,
                            phase: str, iteration: int) -> str:
    fname = f"{agent_id}-{phase}-iter{iteration}.md"
    path = os.path.join(cache_dir, "compaction", fname)
    if os.path.isfile(path):
        with open(path) as f:
            return f.read()
    return ""


if __name__ == "__main__":
    hook_input = json.loads(sys.stdin.read())
    cache_dir = os.environ.get("REVIEW_CACHE_DIR", "")
    agent_id = os.environ.get("REVIEW_AGENT_ID", "")
    phase = os.environ.get("REVIEW_PHASE", "")
    iteration = int(os.environ.get("REVIEW_ITERATION", "1"))

    if not cache_dir or not agent_id:
        sys.exit(0)

    content = load_compaction_content(cache_dir, agent_id, phase, iteration)
    if content:
        print(json.dumps({"context": content}))
