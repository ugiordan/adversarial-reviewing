#!/usr/bin/env bash
# Deduplicate findings by file + overlapping line range + same specialist category.
# Usage: deduplicate.sh <findings_file> [--cross-specialist]
# --cross-specialist: flag cross-specialist overlaps as co-located instead of merging
# Output: deduplicated findings to stdout
# Exit 0 on success.

set -euo pipefail

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not found" >&2
    exit 2
fi

FINDINGS_FILE="${1:?Usage: deduplicate.sh <findings_file> [--cross-specialist]}"
CROSS_SPECIALIST="${2:-}"

if [[ ! -f "$FINDINGS_FILE" ]]; then
    echo "Error: File not found: $FINDINGS_FILE" >&2
    exit 1
fi

# Parse findings into structured records using python3 for reliable parsing
python3 - "$FINDINGS_FILE" "$CROSS_SPECIALIST" << 'PYEOF'
import sys
import re

findings_file = sys.argv[1]
cross_specialist_flag = sys.argv[2] if len(sys.argv) > 2 else ""

with open(findings_file) as f:
    content = f.read()

# Handle zero-finding input
if 'NO_FINDINGS_REPORTED' in content and not re.search(r'Finding ID: [A-Z]+-\d+', content):
    print('NO_FINDINGS_REPORTED')
    sys.exit(0)

# Parse finding blocks
blocks = re.split(r'(?=Finding ID: [A-Z]+-\d+)', content)
blocks = [b.strip() for b in blocks if b.strip() and re.match(r'Finding ID:', b.strip())]

findings = []
for block in blocks:
    fid = re.search(r'Finding ID: ([A-Z]+-\d+)', block)
    specialist = re.search(r'Specialist: (.+)', block)
    severity = re.search(r'Severity: (\w+)', block)
    file_path = re.search(r'File: (.+)', block)
    lines = re.search(r'Lines: (\d+)(?:-(\d+))?', block)

    if fid and file_path and lines:
        findings.append({
            'id': fid.group(1),
            'specialist': specialist.group(1).strip() if specialist else '',
            'severity': severity.group(1) if severity else '',
            'file': file_path.group(1).strip(),
            'line_start': int(lines.group(1)),
            'line_end': int(lines.group(2)) if lines.group(2) else int(lines.group(1)),
            'block': block,
            'merged': False,
            'co_located': []
        })

severity_rank = {'Critical': 3, 'Important': 2, 'Minor': 1}

# Deduplicate
merged_ids = set()
co_located_pairs = []

for i, a in enumerate(findings):
    if a['id'] in merged_ids:
        continue
    for j, b in enumerate(findings):
        if i >= j or b['id'] in merged_ids:
            continue
        # Check file + line overlap
        if a['file'] == b['file']:
            overlap = a['line_start'] <= b['line_end'] and b['line_start'] <= a['line_end']
            if overlap:
                # Same specialist category = merge
                a_cat = a['id'].split('-')[0]
                b_cat = b['id'].split('-')[0]
                if a_cat == b_cat:
                    # Merge: keep higher severity, expand line range
                    if severity_rank.get(b['severity'], 0) > severity_rank.get(a['severity'], 0):
                        a['severity'] = b['severity']
                    a['line_start'] = min(a['line_start'], b['line_start'])
                    a['line_end'] = max(a['line_end'], b['line_end'])
                    a['block'] += '\n\n[MERGED FROM ' + b['id'] + ']\n' + b['block']
                    merged_ids.add(b['id'])
                elif cross_specialist_flag == '--cross-specialist':
                    # Flag as co-located
                    a['co_located'].append(b['id'])
                    b['co_located'].append(a['id'])

# Output
for f in findings:
    if f['id'] not in merged_ids:
        print(f['block'])
        if f['co_located']:
            print(f"\n[CO-LOCATED with: {', '.join(f['co_located'])}]")
        print()
PYEOF
