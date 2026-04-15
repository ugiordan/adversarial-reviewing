#!/usr/bin/env python3
"""Fetch STRAT issues from Red Hat Jira (RHAISTRAT project).

Pulls strategy documents and saves them as markdown with YAML frontmatter,
ready for adversarial-review's strat profile.

Usage:
    # Fetch single issue
    python3 scripts/fetch-strat.py RHAISTRAT-1

    # Fetch multiple
    python3 scripts/fetch-strat.py RHAISTRAT-1 RHAISTRAT-2

    # JQL search
    python3 scripts/fetch-strat.py --jql "project = RHAISTRAT ORDER BY key ASC" --max 10

    # Custom output directory
    python3 scripts/fetch-strat.py RHAISTRAT-1 --output-dir my-strats/

Environment variables:
    JIRA_SERVER  Jira server URL (e.g. https://issues.redhat.com)
    JIRA_USER    Jira username/email
    JIRA_TOKEN   Jira API token

Exit codes:
    0  Success
    1  API/network/script error
    2  Missing JIRA credentials
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


# -- HTTP layer ---------------------------------------------------------------

def _make_request(url, user, token):
    """GET request with Basic Auth. Returns parsed JSON."""
    credentials = base64.b64encode(f"{user}:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def _api_get(server, path, user, token):
    """Build full Jira REST API v3 URL and GET."""
    url = f"{server.rstrip('/')}/rest/api/3{path}"
    return _make_request(url, user, token)


# -- ADF to markdown ---------------------------------------------------------

def adf_to_markdown(node, list_depth=0):
    """Convert Atlassian Document Format JSON to markdown.

    Handles: doc, text (with marks), paragraph, heading, bulletList,
    orderedList, listItem, codeBlock, blockquote, rule, table, panel,
    expand, hardBreak, inlineCard, emoji.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_markdown(item, list_depth) for item in node)
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type", "")
    content = node.get("content", [])
    attrs = node.get("attrs", {})

    if node_type == "doc":
        return adf_to_markdown(content, list_depth)

    if node_type == "text":
        text = node.get("text", "")
        for mark in node.get("marks", []):
            mt = mark.get("type", "")
            if mt == "strong":
                text = f"**{text}**"
            elif mt == "em":
                text = f"*{text}*"
            elif mt == "code":
                text = f"`{text}`"
            elif mt == "strike":
                text = f"~~{text}~~"
            elif mt == "link":
                href = mark.get("attrs", {}).get("href", "")
                text = f"[{text}]({href})"
        return text

    if node_type == "paragraph":
        inner = adf_to_markdown(content, list_depth)
        return f"{inner}\n\n"

    if node_type == "heading":
        level = attrs.get("level", 1)
        inner = adf_to_markdown(content, list_depth)
        return f"{'#' * level} {inner}\n\n"

    if node_type == "bulletList":
        items = adf_to_markdown(content, list_depth)
        return f"{items}\n" if list_depth == 0 else items

    if node_type == "orderedList":
        result = []
        for idx, item in enumerate(content, 1):
            item_text = adf_to_markdown(
                item.get("content", []), list_depth + 1
            ).strip()
            indent = "  " * list_depth
            result.append(f"{indent}{idx}. {item_text}\n")
        return "".join(result) + ("\n" if list_depth == 0 else "")

    if node_type == "listItem":
        item_parts = []
        for child in content:
            child_type = child.get("type", "")
            if child_type in ("bulletList", "orderedList"):
                item_parts.append(adf_to_markdown(child, list_depth + 1))
            else:
                item_parts.append(
                    adf_to_markdown(child, list_depth).strip()
                )
        indent = "  " * list_depth
        first = item_parts[0] if item_parts else ""
        rest = "".join(item_parts[1:])
        return f"{indent}- {first}\n{rest}"

    if node_type == "codeBlock":
        lang = attrs.get("language", "")
        inner = adf_to_markdown(content, list_depth)
        return f"```{lang}\n{inner}\n```\n\n"

    if node_type == "blockquote":
        inner = adf_to_markdown(content, list_depth)
        lines = inner.strip().split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        return f"{quoted}\n\n"

    if node_type == "rule":
        return "---\n\n"

    if node_type == "table":
        rows = []
        for row_node in content:
            if row_node.get("type") == "tableRow":
                cells = []
                for cell in row_node.get("content", []):
                    cell_text = adf_to_markdown(
                        cell.get("content", []), list_depth
                    ).strip().replace("\n", " ")
                    cells.append(cell_text)
                rows.append(cells)
        if not rows:
            return ""
        col_count = max(len(r) for r in rows)
        lines = []
        for i, row in enumerate(rows):
            row += [""] * (col_count - len(row))
            lines.append("| " + " | ".join(row) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * col_count) + " |")
        return "\n".join(lines) + "\n\n"

    if node_type in ("mediaSingle", "media"):
        return ""

    if node_type == "hardBreak":
        return "\n"

    if node_type == "inlineCard":
        url = attrs.get("url", "")
        return f"[{url}]({url})" if url else ""

    if node_type == "emoji":
        return attrs.get("text", attrs.get("shortName", ""))

    if node_type == "panel":
        inner = adf_to_markdown(content, list_depth)
        lines = inner.strip().split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        return f"{quoted}\n\n"

    if node_type == "expand":
        title = attrs.get("title", "")
        inner = adf_to_markdown(content, list_depth)
        header = f"**{title}**\n\n" if title else ""
        return f"{header}{inner}"

    # Fallback: recurse into content
    return adf_to_markdown(content, list_depth)


# -- Issue fetching -----------------------------------------------------------

def _fetch_issue(server, user, token, key):
    """Fetch a single issue by key. Returns the issue JSON."""
    fields = "summary,description,priority,status"
    path = f"/issue/{key}?fields={fields}"
    return _api_get(server, path, user, token)


def _search_jql(server, user, token, jql, max_results):
    """Search issues via JQL. Returns list of issue dicts."""
    params = urllib.parse.urlencode({
        "jql": jql,
        "fields": "summary,description,priority,status",
        "maxResults": max_results,
    })
    path = f"/search?{params}"
    data = _api_get(server, path, user, token)
    return data.get("issues", [])


# -- Output -------------------------------------------------------------------

def _issue_to_markdown(issue):
    """Convert a Jira issue dict to markdown with YAML frontmatter."""
    fields = issue.get("fields", {})
    key = issue.get("key", "UNKNOWN")
    summary = fields.get("summary", "")

    priority_obj = fields.get("priority")
    priority = priority_obj.get("name", "Major") if isinstance(
        priority_obj, dict) else "Major"

    status_obj = fields.get("status")
    status = status_obj.get("name", "Unknown") if isinstance(
        status_obj, dict) else "Unknown"

    # Convert description
    desc_raw = fields.get("description")
    if isinstance(desc_raw, dict):
        desc_md = adf_to_markdown(desc_raw).strip()
    elif desc_raw is not None:
        desc_md = str(desc_raw).strip()
    else:
        desc_md = ""

    # Build frontmatter
    # Escape any quotes in title for YAML safety
    safe_title = summary.replace('"', '\\"')
    frontmatter = (
        f'---\n'
        f'strat_id: {key}\n'
        f'title: "{safe_title}"\n'
        f'priority: {priority}\n'
        f'status: {status}\n'
        f'source: jira\n'
        f'---\n'
    )

    return frontmatter + desc_md + "\n"


def _save_issue(issue, output_dir):
    """Save an issue as a markdown file. Returns the saved path."""
    key = issue.get("key", "UNKNOWN")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{key}.md")
    content = _issue_to_markdown(issue)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# -- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch STRAT issues from Red Hat Jira (RHAISTRAT project).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "keys", nargs="*",
        help="One or more Jira issue keys (e.g. RHAISTRAT-1 RHAISTRAT-2)",
    )
    parser.add_argument(
        "--jql", default=None,
        help='JQL query string (e.g. "project = RHAISTRAT ORDER BY key ASC")',
    )
    parser.add_argument(
        "--max", type=int, default=50, dest="max_results",
        help="Max results for JQL search (default: 50)",
    )
    parser.add_argument(
        "--output-dir", default="test-data/strats/",
        help="Directory to save fetched strats (default: test-data/strats/)",
    )
    args = parser.parse_args()

    if not args.keys and not args.jql:
        parser.error("Provide issue keys or --jql query")

    # Check credentials
    server = os.environ.get("JIRA_SERVER")
    user = os.environ.get("JIRA_USER")
    token = os.environ.get("JIRA_TOKEN")

    if not all([server, user, token]):
        print(
            "Error: JIRA_SERVER, JIRA_USER, and JIRA_TOKEN environment "
            "variables are required.",
            file=sys.stderr,
        )
        sys.exit(2)

    issues = []
    errors = 0

    # Fetch by key
    for key in (args.keys or []):
        try:
            print(f"Fetching {key}...", file=sys.stderr)
            issue = _fetch_issue(server, user, token, key)
            issues.append(issue)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            print(f"Error fetching {key}: HTTP {e.code}: {error_body}",
                  file=sys.stderr)
            errors += 1
        except Exception as e:
            print(f"Error fetching {key}: {e}", file=sys.stderr)
            errors += 1

    # Fetch by JQL
    if args.jql:
        try:
            print(f"Searching: {args.jql}", file=sys.stderr)
            jql_issues = _search_jql(
                server, user, token, args.jql, args.max_results
            )
            print(f"Found {len(jql_issues)} issues", file=sys.stderr)
            issues.extend(jql_issues)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            print(f"JQL search error: HTTP {e.code}: {error_body}",
                  file=sys.stderr)
            errors += 1
        except Exception as e:
            print(f"JQL search error: {e}", file=sys.stderr)
            errors += 1

    # Save results
    for issue in issues:
        path = _save_issue(issue, args.output_dir)
        print(path)  # stdout: saved paths
        print(f"Saved {issue.get('key')}", file=sys.stderr)

    if errors > 0 and not issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
