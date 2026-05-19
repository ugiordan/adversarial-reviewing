#!/usr/bin/env python3
"""Write agent output to the dispatch output file.

Usage:
    python3 scripts/write_output.py <output_path> <content_file>
    python3 scripts/write_output.py <output_path> -       # read from stdin
    python3 scripts/write_output.py <output_path> --inline "content here"

Agents call this instead of using the Write tool. Works regardless of
sandbox permissions because it runs as a Bash command.

Exit codes:
    0 = success (prints bytes written)
    1 = error (prints error message to stderr)
"""
import os
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: write_output.py <output_path> <content_file|-|--inline content>",
              file=sys.stderr)
        sys.exit(1)

    output_path = sys.argv[1]
    mode = sys.argv[2]

    if mode == "--inline":
        content = " ".join(sys.argv[3:])
    elif mode == "-":
        content = sys.stdin.read()
    else:
        with open(mode) as f:
            content = f.read()

    if not content.strip():
        print("ERROR: empty content, refusing to write empty output", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)

    size = os.path.getsize(output_path)
    print(f"OK: wrote {size} bytes to {output_path}")


if __name__ == "__main__":
    main()
