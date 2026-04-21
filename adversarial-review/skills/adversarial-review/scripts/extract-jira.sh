#!/usr/bin/env bash
# Extract Jira ticket and normalize into strategy template format.
# Usage: extract-jira.sh --key <JIRA_KEY> --template <template_path>
# Output: Rendered template on stdout
# Errors: JSON errors on stderr

set -euo pipefail

key=""
template=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --key)
      key="$2"
      shift 2
      ;;
    --template)
      template="$2"
      shift 2
      ;;
    *)
      echo "{\"error\": \"Unknown argument: $1\"}" >&2
      exit 1
      ;;
  esac
done

# Validate required arguments
if [[ -z "$key" ]]; then
  echo "{\"error\": \"Missing required argument: --key\"}" >&2
  exit 1
fi

if [[ -z "$template" ]]; then
  echo "{\"error\": \"Missing required argument: --template\"}" >&2
  exit 1
fi

# Check that acli is available
if ! command -v acli &> /dev/null; then
  echo "{\"error\": \"acli CLI not found. Install atlassian-cli from npm.\"}" >&2
  exit 1
fi

# Check that template exists
if [[ ! -f "$template" ]]; then
  echo "{\"error\": \"Template file not found: $template\"}" >&2
  exit 1
fi

# Fetch ticket from Jira
if ! jira_json=$(acli jira workitem view "$key" --fields '*all' --json 2>&1); then
  echo "{\"error\": \"Failed to fetch Jira ticket $key\", \"details\": $(echo "$jira_json" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}" >&2
  exit 1
fi

# Cache raw JSON if CACHE_DIR is set
if [[ -n "${CACHE_DIR:-}" ]]; then
  mkdir -p "$CACHE_DIR/strategy"
  echo "$jira_json" > "$CACHE_DIR/strategy/jira-raw.json"
fi

# Parse JSON and fill template using inline Python script
echo "$jira_json" | python3 - "$key" "$template" <<'PYTHON_EOF'
import json
import re
import sys

def extract_acceptance_criteria(description):
    """Extract acceptance criteria section from description."""
    if not description:
        return []

    # Patterns to match AC sections in various formats
    patterns = [
        r'(?:^|\n)#+\s*Acceptance\s+Criteria\s*\n(.*?)(?=\n#+|\Z)',  # Markdown heading
        r'(?:^|\n)Acceptance\s+Criteria:?\s*\n(.*?)(?=\n[A-Z][a-z]+:|\Z)',  # Plain text heading
        r'(?:^|\n)#+\s*AC\s*\n(.*?)(?=\n#+|\Z)',  # Short form heading
        r'(?:^|\n)AC:?\s*\n(.*?)(?=\n[A-Z][a-z]+:|\Z)',  # Short form plain text
        r'(?:^|\n)h\d+\.\s*Acceptance\s+Criteria\s*\n(.*?)(?=\nh\d+\.|\Z)',  # Confluence wiki heading
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            criteria_text = match.group(1).strip()
            # Parse numbered or bulleted list
            criteria = []
            for line in criteria_text.split('\n'):
                line = line.strip()
                # Match numbered (1., 1), etc.) or bulleted (-, *, +) lists
                if re.match(r'^(?:\d+[\.\)]|-|\*|\+)\s+', line):
                    criteria.append(re.sub(r'^(?:\d+[\.\)]|-|\*|\+)\s+', '', line))
            return criteria if criteria else [criteria_text]

    return []

def strip_acceptance_criteria(description):
    """Remove acceptance criteria section from description to avoid duplication."""
    if not description:
        return ""

    patterns = [
        r'(?:^|\n)#+\s*Acceptance\s+Criteria\s*\n.*?(?=\n#+|\Z)',
        r'(?:^|\n)Acceptance\s+Criteria:?\s*\n.*?(?=\n[A-Z][a-z]+:|\Z)',
        r'(?:^|\n)#+\s*AC\s*\n.*?(?=\n#+|\Z)',
        r'(?:^|\n)AC:?\s*\n.*?(?=\n[A-Z][a-z]+:|\Z)',
        r'(?:^|\n)h\d+\.\s*Acceptance\s+Criteria\s*\n.*?(?=\nh\d+\.|\Z)',
    ]

    result = description
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE)

    return result.strip()

def extract_questions_from_comments(comments):
    """Extract questions (sentences with ?) from comments."""
    questions = []
    if not comments:
        return questions

    for comment in comments:
        body = comment.get('body', '')
        author = comment.get('author', {}).get('displayName', 'Unknown')

        # Split by sentence boundaries and find questions
        sentences = re.split(r'[.!]\s+', body)
        for sentence in sentences:
            if '?' in sentence:
                question = sentence.strip()
                if question:
                    questions.append(f"{question} (owner: {author})")

    return questions

def format_list_items(items, placeholder_pattern):
    """Format a list of items, or return placeholder if empty."""
    if not items:
        return placeholder_pattern

    result = []
    for i, item in enumerate(items, 1):
        # Clean up the item
        item = item.strip()
        # If item already starts with number, use as-is, otherwise add number
        if re.match(r'^\d+\.', item):
            result.append(item)
        else:
            result.append(f"{i}. {item}")

    return '\n'.join(result)

def format_bullet_items(items, placeholder_pattern):
    """Format bulleted items, or return placeholder if empty."""
    if not items:
        return placeholder_pattern

    return '\n'.join(f"- {item.strip()}" for item in items)

def main():
    if len(sys.argv) != 3:
        print(json.dumps({"error": "Usage: script <key> <template_path>"}), file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1]
    template_path = sys.argv[2]

    # Read JSON from stdin
    jira_json = sys.stdin.read()

    # Parse JSON
    try:
        data = json.loads(jira_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON from acli: {e}"}), file=sys.stderr)
        sys.exit(1)

    # Handle both single ticket and array response
    if isinstance(data, list):
        if len(data) == 0:
            print(json.dumps({"error": f"No ticket found for key {key}"}), file=sys.stderr)
            sys.exit(1)
        ticket = data[0]
    else:
        ticket = data

    # Extract fields
    fields = ticket.get('fields', {})
    summary = fields.get('summary', 'Untitled')
    description = fields.get('description', '')
    priority = fields.get('priority', {})
    priority_name = priority.get('name', 'Not set') if priority else 'Not set'
    labels = fields.get('labels', [])
    components = fields.get('components', [])
    component_names = [c.get('name', '') for c in components if c.get('name')]
    issue_links = fields.get('issuelinks', [])
    comments = fields.get('comment', {}).get('comments', []) if fields.get('comment') else []

    # Extract acceptance criteria
    acceptance_criteria = extract_acceptance_criteria(description)

    # Strip AC from description for problem statement
    problem_statement = strip_acceptance_criteria(description)
    if not problem_statement:
        problem_statement = "{What problem does this solve? What is the current state? What is the desired state?}"

    # Extract dependencies from linked issues
    dependencies = []
    for link in issue_links:
        link_type = link.get('type', {}).get('name', 'Related')
        outward = link.get('outwardIssue')
        inward = link.get('inwardIssue')

        if outward:
            dep_key = outward.get('key', '')
            dep_summary = outward.get('fields', {}).get('summary', '')
            dep_status = outward.get('fields', {}).get('status', {}).get('name', 'Unknown')
            dependencies.append(f"{dep_key} ({link_type}): {dep_summary} (status: {dep_status})")
        elif inward:
            dep_key = inward.get('key', '')
            dep_summary = inward.get('fields', {}).get('summary', '')
            dep_status = inward.get('fields', {}).get('status', {}).get('name', 'Unknown')
            dependencies.append(f"{dep_key} ({link_type}): {dep_summary} (status: {dep_status})")

    # Extract questions from comments
    questions = extract_questions_from_comments(comments)

    # Build constraints from priority and labels
    constraints = []
    if priority_name and priority_name != 'Not set':
        constraints.append(f"Priority: {priority_name}")
    if labels:
        constraints.append(f"Labels: {', '.join(labels)}")
    if component_names:
        constraints.append(f"Components: {', '.join(component_names)}")

    # Read template
    try:
        with open(template_path, 'r') as f:
            template = f.read()
    except FileNotFoundError:
        print(json.dumps({"error": f"Template file not found: {template_path}"}), file=sys.stderr)
        sys.exit(1)

    # Fill template
    # Replace title
    template = template.replace('{TITLE}', summary)

    # Replace summary section
    summary_text = f"This strategy addresses {key}: {summary}. Priority: {priority_name}."
    template = re.sub(
        r'\{One paragraph describing what this strategy proposes and why\.\}',
        summary_text,
        template
    )

    # Replace problem statement
    template = re.sub(
        r'\{What problem does this solve\? What is the current state\? What is the desired state\?\}',
        problem_statement,
        template
    )

    # Replace goals (use numbered list or placeholder)
    # First remove the description line
    template = re.sub(
        r'\{Numbered list of concrete, measurable goals this strategy aims to achieve\.\}\n\n',
        '',
        template
    )

    goals_placeholder = "1. {Goal 1}\n2. {Goal 2}"
    if acceptance_criteria:
        # Use first few ACs as goals if no explicit goals section
        goals = acceptance_criteria[:3] if len(acceptance_criteria) > 3 else acceptance_criteria
        template = re.sub(
            re.escape(goals_placeholder),
            format_list_items(goals, goals_placeholder),
            template
        )

    # Replace acceptance criteria
    # First remove the description line
    template = re.sub(
        r'\{Numbered list of testable acceptance criteria\. Each AC must be specific enough that a test engineer can verify it\.\}\n\n',
        '',
        template
    )

    ac_placeholder = "1. {AC 1}\n2. {AC 2}"
    template = re.sub(
        re.escape(ac_placeholder),
        format_list_items(acceptance_criteria, ac_placeholder),
        template
    )

    # Replace dependencies
    # First remove the description line
    template = re.sub(
        r'\{List of dependencies: other strategies, external services, infrastructure requirements, team capabilities\.\}\n\n',
        '',
        template
    )

    dep_placeholder = "- {Dependency 1}: {description and status}\n- {Dependency 2}: {description and status}"
    template = re.sub(
        re.escape(dep_placeholder),
        format_bullet_items(dependencies, dep_placeholder),
        template
    )

    # Replace constraints
    # First remove the description line
    template = re.sub(
        r'\{Technical, organizational, or timeline constraints that bound the solution space\.\}\n\n',
        '',
        template
    )

    constraints_placeholder = "- {Constraint 1}\n- {Constraint 2}"
    template = re.sub(
        re.escape(constraints_placeholder),
        format_bullet_items(constraints, constraints_placeholder),
        template
    )

    # Replace open questions
    # First remove the description line
    template = re.sub(
        r'\{Unresolved questions extracted from comments, ambiguities, or missing information\. Each question should identify who can answer it\.\}\n\n',
        '',
        template
    )

    questions_placeholder = "- {Question 1} (owner: {who})\n- {Question 2} (owner: {who})"
    template = re.sub(
        re.escape(questions_placeholder),
        format_bullet_items(questions, questions_placeholder),
        template
    )

    # Output rendered template
    print(template)

if __name__ == '__main__':
    main()
PYTHON_EOF
