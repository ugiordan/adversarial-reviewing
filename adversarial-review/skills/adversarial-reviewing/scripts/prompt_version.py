#!/usr/bin/env python3
"""Prompt versioning tool for adversarial-review agent prompts.

Computes content-based version hashes for agent prompt files and manages
version metadata via YAML frontmatter.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)


def parse_frontmatter(content: str) -> tuple[Optional[dict], str]:
    """Split file content into frontmatter dict and body.

    Returns (None, content) if no frontmatter is present.
    """
    m = FRONTMATTER_RE.match(content)
    if not m:
        return None, content

    fm_text = m.group(1)
    body = content[m.end():]

    # Simple YAML key: value parser (no dependency on pyyaml)
    fm: dict = {}
    for line in fm_text.strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            fm[key.strip()] = val
    return fm, body


def compute_hash(body: str) -> str:
    """SHA-256 of the prompt body with leading/trailing whitespace stripped."""
    return hashlib.sha256(body.strip().encode("utf-8")).hexdigest()


def file_last_modified(path: Path) -> str:
    """ISO date of file's last modification time."""
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def collect_md_files(target: Path) -> list[Path]:
    """Collect .md files from a path (single file or recursive directory scan)."""
    if target.is_file():
        if target.suffix == ".md":
            return [target]
        return []
    if target.is_dir():
        return sorted(target.rglob("*.md"))
    return []


# --- Subcommands ---


def cmd_compute(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if not target.exists():
        print(f"Error: {target} does not exist", file=sys.stderr)
        return 1

    files = collect_md_files(target)
    if not files:
        print(f"No .md files found at {target}", file=sys.stderr)
        return 1

    results = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        h = compute_hash(body)
        version = fm.get("version", "unversioned") if fm else "unversioned"
        results.append({
            "file": str(f),
            "version": version,
            "content_hash": h,
            "last_modified": file_last_modified(f),
        })

    print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    path = Path(args.prompt_file)
    if not path.is_file():
        print(f"Error: {path} is not a file", file=sys.stderr)
        return 1

    content = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)

    if fm is None:
        print(f"No frontmatter found in {path}")
        return 2

    stored_hash = fm.get("content_hash", "")
    actual_hash = compute_hash(body)

    if stored_hash == actual_hash:
        print(f"MATCH: {path}")
        print(f"  hash: {actual_hash}")
        return 0
    else:
        print(f"MISMATCH: {path}")
        print(f"  stored:  {stored_hash}")
        print(f"  actual:  {actual_hash}")
        return 1


def cmd_stamp(args: argparse.Namespace) -> int:
    path = Path(args.prompt_file)
    if not path.is_file():
        print(f"Error: {path} is not a file", file=sys.stderr)
        return 1

    content = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)
    content_hash = compute_hash(body)
    last_modified = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    if fm is not None:
        # Update existing frontmatter
        version = args.version if args.version else fm.get("version", "1.0")
        fm["version"] = version
        fm["content_hash"] = content_hash
        fm["last_modified"] = last_modified
    else:
        version = args.version if args.version else "1.0"
        fm = {
            "version": version,
            "content_hash": content_hash,
            "last_modified": last_modified,
        }

    # Build frontmatter block
    fm_block = "---\n"
    fm_block += f'version: "{fm["version"]}"\n'
    fm_block += f'content_hash: "{fm["content_hash"]}"\n'
    fm_block += f'last_modified: "{fm["last_modified"]}"\n'
    fm_block += "---\n"

    new_content = fm_block + body
    path.write_text(new_content, encoding="utf-8")
    print(f"Stamped {path} (version={version}, hash={content_hash[:16]}...)")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    target = Path(args.dir)
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        return 1

    files = collect_md_files(target)
    if not files:
        print(f"No .md files found in {target}", file=sys.stderr)
        return 1

    prompts = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        h = compute_hash(body)
        version = fm.get("version", "unversioned") if fm else "unversioned"
        prompts.append({
            "file": f.name,
            "version": version,
            "content_hash": h,
            "last_modified": file_last_modified(f),
        })

    manifest = {
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompts": prompts,
    }

    output = json.dumps(manifest, indent=2)
    print(output)

    # Also write to manifest.json in the target directory
    manifest_path = target / "manifest.json"
    manifest_path.write_text(output + "\n", encoding="utf-8")
    print(f"\nManifest written to {manifest_path}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prompt versioning tool for adversarial-review agent prompts"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # compute
    p_compute = sub.add_parser("compute", help="Compute version hash for prompt file(s)")
    p_compute.add_argument("path", help="Prompt file or directory to process")

    # verify
    p_verify = sub.add_parser("verify", help="Verify content_hash in frontmatter matches actual content")
    p_verify.add_argument("prompt_file", help="Prompt file to verify")

    # stamp
    p_stamp = sub.add_parser("stamp", help="Add or update version frontmatter in a prompt file")
    p_stamp.add_argument("prompt_file", help="Prompt file to stamp")
    p_stamp.add_argument("--version", default=None, help="Version string (default: 1.0 for new, keep existing for updates)")

    # manifest
    p_manifest = sub.add_parser("manifest", help="Generate version manifest for all agent prompts in a directory")
    p_manifest.add_argument("dir", help="Directory containing agent prompt .md files")

    args = parser.parse_args()
    handlers = {
        "compute": cmd_compute,
        "verify": cmd_verify,
        "stamp": cmd_stamp,
        "manifest": cmd_manifest,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
