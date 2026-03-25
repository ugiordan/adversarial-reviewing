# Triage Input Schema

## For `--triage file:<path>` Source

The input file must contain a JSON array of comment objects:

```json
[
  {
    "file": "path/to/file.go",
    "line": 42,
    "comment": "This function has a race condition on the shared counter",
    "author": "reviewer-name",
    "category": "correctness"
  },
  {
    "comment": "Consider using the Builder pattern for this complex constructor",
    "author": "senior-dev",
    "category": "design"
  }
]
```

## Field Definitions

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `comment` | **Yes** | string | The review comment text |
| `file` | No | string or null | Repo-relative file path. Null/omitted for general comments. |
| `line` | No | integer or null | Line number. Null/omitted for file-level or general comments. |
| `author` | No | string | Comment author name. Defaults to `"unknown"`. |
| `category` | No | string | One of: `correctness`, `security`, `performance`, `design`, `style`, `unknown`. Defaults to `"unknown"`. |

## Notes

- Only `comment` is required. All other fields default to null/unknown.
- File paths should be repo-relative (e.g., `src/auth/login.ts`, not absolute paths).
- The parser assigns sequential `EXT-NNN` IDs to each comment.
