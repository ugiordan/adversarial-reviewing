#!/usr/bin/env python3
"""Extract structured votes from challenge agent markdown outputs."""
import json
import re
import sys
from pathlib import Path


def parse_challenge_output(text):
    """Extract Agree/Challenge/Abstain positions from challenge markdown."""
    votes = {}
    pattern = re.compile(
        r"(?:Finding|##)\s+(\S+-\d+).*?\[(AGREE|CHALLENGE|ABSTAIN)\]",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(text):
        finding_id = m.group(1).upper()
        position = m.group(2).capitalize()
        votes[finding_id] = {"position": position}
    return votes


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_challenge_responses.py <output1.md> [output2.md ...]",
              file=sys.stderr)
        sys.exit(1)

    all_votes = {}
    for path in sys.argv[1:]:
        if not Path(path).exists():
            continue
        text = Path(path).read_text()
        agent_id = Path(path).parent.name.split("-", 1)[-1] if "-" in Path(path).parent.name else Path(path).parent.name
        votes = parse_challenge_output(text)
        for fid, vote in votes.items():
            all_votes.setdefault(fid, []).append({"agent": agent_id, **vote})

    result = {"findings": [
        {"id": fid, "votes": votes}
        for fid, votes in sorted(all_votes.items())
    ]}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
