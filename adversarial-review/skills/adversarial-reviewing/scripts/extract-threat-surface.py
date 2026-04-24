#!/usr/bin/env python3
"""Extract threat surface from a strategy document (deterministic Pass 1).

Scans STRAT text for security-relevant keywords and extracts a structured
inventory of surfaces. No LLM required. Output is JSON.

Usage:
    extract-threat-surface.py <strat-file>
    extract-threat-surface.py --inline <text>

Output (stdout): JSON with tier, surface hints, keywords matched.

Exit codes:
    0  Success
    1  Error
"""

import argparse
import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Keyword categories — each maps to a list of patterns (case-insensitive)
# ---------------------------------------------------------------------------

KEYWORD_CATEGORIES = {
    "auth": [
        r"\bauthenticat\w*\b", r"\bauthoriz\w*\b", r"\bauth\b",
        r"\brbac\b", r"\boauth\b", r"\boidc\b", r"\bsaml\b",
        r"\btoken\b", r"\bcredential\w*\b", r"\blogin\b",
        r"\bsession\b", r"\bsession.id\b", r"\bsession_id\b",
        r"\baccess.control\b", r"\bpermission\w*\b",
        r"\bservice.?account\b", r"\brole.?binding\b",
        r"\bcluster.?role\b", r"\bsubject.?access.?review\b",
    ],
    "crypto": [
        r"\bencrypt\w*\b", r"\btls\b", r"\bssl\b", r"\bcertificat\w*\b",
        r"\bsign\w*\b", r"\bhash\w*\b", r"\bhmac\b",
        r"\bat.rest\b", r"\bin.transit\b", r"\bmtls\b",
    ],
    "network": [
        r"\bendpoint\w*\b", r"\bapi\b", r"\bingress\b", r"\begress\b",
        r"\bnetwork.?polic\w*\b", r"\bfirewall\b", r"\bproxy\b",
        r"\bgateway\b", r"\broute\b", r"\bhttp\w*\b",
        r"\bsse\b", r"\bserver.sent.event\w*\b", r"\bstreaming\b",
        r"\bgrpc\b", r"\bwebsocket\b",
    ],
    "data": [
        r"\bsecret\w*\b", r"\bpassword\w*\b", r"\bapi.?key\w*\b",
        r"\bconfigmap\b", r"\bpersist\w*\b", r"\bstor\w+\b",
        r"\bdatabas\w*\b", r"\bcache\b", r"\bredis\b",
        r"\bpvc\b", r"\bvolume\b", r"\bstate\b",
        r"\bsession.?store\b", r"\bdata.?at.?rest\b",
    ],
    "multi_tenant": [
        r"\bmulti.?tenant\w*\b", r"\btenant\w*\b", r"\bisolat\w*\b",
        r"\bnamespace\b", r"\bquota\w*\b", r"\bresource.?limit\w*\b",
        r"\bfair.?shar\w*\b", r"\bpreempt\w*\b",
    ],
    "supply_chain": [
        r"\bdependenc\w*\b", r"\bupstream\b", r"\bthird.?party\b",
        r"\bexternal\b", r"\bimport\b", r"\bpackage\w*\b",
        r"\bcontainer.?imag\w*\b", r"\brocm\b", r"\bcuda\b",
        r"\bdriver\w*\b", r"\bfirmware\b", r"\bsbom\b",
        r"\bmodel.?weight\w*\b", r"\bhugging.?face\b",
    ],
    "compliance": [
        r"\baudit\w*\b", r"\blog\w*\b", r"\bcomplia\w*\b",
        r"\bgdpr\b", r"\bsoc.?2\b", r"\bfedramp\b",
        r"\bretent\w*\b", r"\bprivacy\b",
    ],
    "agentic": [
        r"\bagent\w*\b", r"\btool.?call\w*\b", r"\bfunction.?call\w*\b",
        r"\bmcp\b", r"\borchestrat\w*\b", r"\bmulti.?turn\b",
        r"\bcode.?execut\w*\b", r"\bbash\b", r"\bwrite_file\b",
        r"\bread_file\b", r"\bedit_file\b",
    ],
}

# Tier escalation triggers — if ANY of these categories have matches,
# escalate to deep review
DEEP_TRIGGERS = {"auth", "crypto", "multi_tenant", "agentic"}
STANDARD_TRIGGERS = {"network", "data", "supply_chain", "compliance"}


# ---------------------------------------------------------------------------
# Surface hint extraction — deterministic pattern matching
# ---------------------------------------------------------------------------

SURFACE_PATTERNS = {
    "endpoints": [
        r"/v\d+/\w+(?:/\w+)*",                  # versioned API paths like /v1/models
        r"\b\w+\s+endpoint\b",                   # "streaming endpoint"
        r"\bAPI\s+surface\b",
        r"\bSSE\b",
        r"\bREST\s+API\b",
        r"\bgRPC\b",
    ],
    "data_stores": [
        r"\bsession\s+store\b",
        r"\bcache\b",
        r"\bredis\b",
        r"\bdatabase\b",
        r"\bpersist\w+\s+stor\w+\b",
        r"\bKV\s+cache\b",
        r"\bstate\s+(?:store|manag\w+)\b",
    ],
    "credentials": [
        r"\bsession.?id\b",
        r"\bapi.?key\b",
        r"\btoken\b",
        r"\bsecret\b",
        r"\bcredential\w*\b",
        r"\bpassword\b",
    ],
    "external_deps": [
        r"\bcodex\s+cli\b",
        r"\bllama.?stack\b",
        r"\bvllm\b",
        r"\brocm\b",
        r"\bpytorch\b",
        r"\bkueue\b",
        r"\btriton\b",
        r"\bkserve\b",
        r"\bhugging.?face\b",
        r"\bupstream\s+\w+\b",
    ],
    "trust_boundaries": [
        r"\bclient.server\b",
        r"\btool\s+execut\w+\b",
        r"\bexecut\w+\s+boundar\w*\b",
        r"\bsandbox\w*\b",
        r"\bprivileg\w+\b",
        r"\bnon.?admin\w*\b",
        r"\bself.?service\b",
    ],
    "crd_changes": [
        r"\bcrd\b",
        r"\bcustom\s+resource\b",
        r"\bcluster.?queue\b",
        r"\bresource.?flavor\b",
        r"\bgateway\s+api\b",
        r"\benvoy.?filter\b",
    ],
    "agent_surfaces": [
        r"\btool\s+(?:call|defin)\w*\b",
        r"\bfunction\s+call\w*\b",
        r"\bbash\b",
        r"\bwrite_file\b",
        r"\bread_file\b",
        r"\bedit_file\b",
        r"\bglob_search\b",
        r"\bgrep_search\b",
        r"\bcode\s+generat\w+\b",
    ],
}


def scan_keywords(text):
    """Scan text for keyword category matches. Returns dict of category -> matched terms."""
    text_lower = text.lower()
    matches = {}
    for category, patterns in KEYWORD_CATEGORIES.items():
        found = set()
        for pattern in patterns:
            for m in re.finditer(pattern, text_lower):
                found.add(m.group())
        if found:
            matches[category] = sorted(found)
    return matches


def classify_tier(keyword_matches):
    """Classify review tier based on keyword matches."""
    categories_hit = set(keyword_matches.keys())

    if not categories_hit:
        return "skip"

    if categories_hit & DEEP_TRIGGERS:
        return "deep"

    if categories_hit & STANDARD_TRIGGERS:
        return "standard"

    return "light"


def extract_surface_hints(text):
    """Extract surface hints from text using pattern matching."""
    text_lower = text.lower()
    surface = {}
    for category, patterns in SURFACE_PATTERNS.items():
        found = set()
        for pattern in patterns:
            for m in re.finditer(pattern, text_lower):
                term = m.group().strip()
                if len(term) > 2:
                    found.add(term)
        if found:
            surface[category] = sorted(found)
    return surface


def extract_sections(text):
    """Extract markdown section headers for citation mapping."""
    sections = []
    for m in re.finditer(r"^(#{1,4})\s+(.+)$", text, re.MULTILINE):
        sections.append({
            "level": len(m.group(1)),
            "title": m.group(2).strip(),
            "offset": m.start(),
        })
    return sections


def extract_acceptance_criteria(text):
    """Extract numbered acceptance criteria."""
    criteria = []
    # Match numbered lists that look like ACs
    for m in re.finditer(
        r"(?:^|\n)\s*(\d+)\.\s+(.+?)(?=\n\s*\d+\.|\n\n|\Z)",
        text, re.DOTALL
    ):
        criteria.append({
            "number": int(m.group(1)),
            "text": m.group(2).strip()[:200],
        })
    # Also match bullet-style ACs after all "Acceptance Criteria" headers
    for ac_section in re.finditer(
        r"(?:acceptance\s+criteria|## ac\b)(.*?)(?=\n##|\Z)",
        text, re.IGNORECASE | re.DOTALL
    ):
        for m in re.finditer(r"[*\-]\s+(.+)", ac_section.group(1)):
            criteria.append({
                "number": len(criteria) + 1,
                "text": m.group(1).strip()[:200],
            })
    return criteria


def main():
    parser = argparse.ArgumentParser(
        description="Extract threat surface from a strategy document (deterministic)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("strat_file", nargs="?", help="Path to STRAT markdown file")
    group.add_argument("--inline", help="Inline STRAT text")
    args = parser.parse_args()

    if args.inline:
        text = args.inline
    else:
        try:
            with open(args.strat_file, encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: file not found: {args.strat_file}", file=sys.stderr)
            print(f"Provide a valid path to a STRAT markdown file, or use --inline.", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(f"Error: permission denied reading {args.strat_file}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error reading {args.strat_file}: {e}", file=sys.stderr)
            sys.exit(1)

    if not text.strip():
        print("Error: input text is empty. Provide a non-empty STRAT document.", file=sys.stderr)
        sys.exit(1)

    keyword_matches = scan_keywords(text)
    tier = classify_tier(keyword_matches)
    surface_hints = extract_surface_hints(text)
    sections = extract_sections(text)
    acceptance_criteria = extract_acceptance_criteria(text)

    result = {
        "tier": tier,
        "keyword_categories": keyword_matches,
        "keyword_count": sum(len(v) for v in keyword_matches.values()),
        "surface_hints": surface_hints,
        "surface_item_count": sum(len(v) for v in surface_hints.values()),
        "sections": sections,
        "acceptance_criteria": acceptance_criteria,
    }

    try:
        json.dump(result, sys.stdout, indent=2)
        print()
    except (BrokenPipeError, IOError):
        sys.exit(1)


if __name__ == "__main__":
    main()
