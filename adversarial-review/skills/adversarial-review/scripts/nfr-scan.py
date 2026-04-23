#!/usr/bin/env python3
"""NFR checklist scanner for STRAT documents (Layer 2).

Runs the recurring NFR checklist against a STRAT document.
Produces structured YES/NO/PARTIAL assessments per checklist item
with citations and deterministic severity assignment.

This script generates the prompt for the NFR scan agent. The actual LLM call
is done by the orchestrator (Claude Code agent dispatch).

Usage:
    # Generate scan prompt (pipe to agent)
    nfr-scan.py --prompt <strat-file> [--surface <threat-surface.json>]

    # Parse scan output into structured JSON
    nfr-scan.py --parse <scan-output-file>

Exit codes:
    0  Success
    1  Error
"""

import argparse
import json
import sys


# ---------------------------------------------------------------------------
# NFR Checklist items — each has an ID, category, question, and severity tree
# ---------------------------------------------------------------------------

NFR_CHECKLIST = [
    # -- Authentication & Authorization --
    {
        "id": "NFR-AUTH-01",
        "category": "Authentication & Authorization",
        "question": "Does the strategy specify which approved auth pattern gates every new API/UI surface? (If architecture context is provided, check against documented auth mechanisms.)",
        "severity_tree": {
            "NO": {"new_api_or_state_store": "Critical", "modifies_existing": "Important"},
            "PARTIAL": "Important",
        },
    },
    {
        "id": "NFR-AUTH-02",
        "category": "Authentication & Authorization",
        "question": "Are new operations mapped to specific Kubernetes RBAC verbs/resources/scopes?",
        "severity_tree": {
            "NO": {"new_api_or_state_store": "Important", "default": "Minor"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-AUTH-03",
        "category": "Authentication & Authorization",
        "question": "Is user-facing data filtered to the requesting tenant's scope (no cross-tenant visibility by default)?",
        "severity_tree": {
            "NO": {"multi_tenant_context": "Critical", "default": "Important"},
            "PARTIAL": "Important",
        },
    },
    {
        "id": "NFR-AUTH-04",
        "category": "Authentication & Authorization",
        "question": "If non-admins get new capabilities (provisioning, configuration), are admission controls and quota ceilings specified?",
        "severity_tree": {
            "NO": {"privilege_delegation": "Critical", "default": "N/A"},
            "PARTIAL": "Important",
        },
    },
    # -- Testability --
    {
        "id": "NFR-TEST-01",
        "category": "Testability",
        "question": "Does every acceptance criterion have a concrete pass/fail definition (not 'seamlessly', 'successfully', 'without degradation')?",
        "severity_tree": {
            "NO": "Important",
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-TEST-02",
        "category": "Testability",
        "question": "Are system behavior ACs (deterministic, testable) distinct from model quality ACs (probabilistic)?",
        "severity_tree": {
            "NO": {"ml_context": "Important", "default": "N/A"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-TEST-03",
        "category": "Testability",
        "question": "Do performance targets specify percentile (p50/p95/p99), load conditions, hardware, and measurement methodology?",
        "severity_tree": {
            "NO": {"has_perf_targets": "Important", "default": "N/A"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-TEST-04",
        "category": "Testability",
        "question": "Does the strategy reference or create a specific test suite with recorded baselines for regression comparison?",
        "severity_tree": {
            "NO": {"modifies_existing_behavior": "Important", "default": "Minor"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-TEST-05",
        "category": "Testability",
        "question": "If the strategy spans multiple models, formats, or backends, is the coverage matrix explicitly defined?",
        "severity_tree": {
            "NO": {"multi_model": "Important", "default": "N/A"},
            "PARTIAL": "Minor",
        },
    },
    # -- Security --
    {
        "id": "NFR-SEC-01",
        "category": "Security",
        "question": "Does every new endpoint, data store, or trust boundary have a threat model (even lightweight)?",
        "severity_tree": {
            "NO": {"new_endpoint_or_trust_boundary": "Important", "default": "Minor"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-SEC-02",
        "category": "Security",
        "question": "Do external dependencies (model weights, drivers, firmware, SDKs) specify verification method (checksums, signatures, pinned versions, SBOM)?",
        "severity_tree": {
            "NO": {"kernel_or_driver_deps": "Critical", "model_weight_deps": "Important", "default": "Minor"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-SEC-03",
        "category": "Security",
        "question": "Do security-relevant actions (enforcement, access decisions, provisioning) emit metrics or logs at configurable verbosity?",
        "severity_tree": {
            "NO": {"security_critical": "Important", "default": "Minor"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-SEC-04",
        "category": "Security",
        "question": "Are new enforcement mechanisms additive to existing validation (defense-in-depth preserved), not replacements?",
        "severity_tree": {
            "NO": {"replaces_existing_validation": "Important", "default": "N/A"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-SEC-05",
        "category": "Security",
        "question": "Does any persistent state specify encryption at rest, TTL/expiry, deletion API, and access control?",
        "severity_tree": {
            "NO": {"has_persistent_state": "Important", "default": "N/A"},
            "PARTIAL": "Minor",
        },
    },
    # -- Feasibility --
    {
        "id": "NFR-FEAS-01",
        "category": "Feasibility",
        "question": "Does the strategy include effort estimates (T-shirt sizing per work stream) mapped to release trains?",
        "severity_tree": {
            "NO": "Minor",
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-FEAS-02",
        "category": "Feasibility",
        "question": "Do external dependencies (upstream RFCs, third-party releases, hardware availability) have contingency plans and fallback dates?",
        "severity_tree": {
            "NO": {"serial_dep_chain": "Critical", "has_external_deps": "Important", "default": "Minor"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-FEAS-03",
        "category": "Feasibility",
        "question": "Are required skills and team composition documented (not just an assignee name)?",
        "severity_tree": {
            "NO": "Minor",
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-FEAS-04",
        "category": "Feasibility",
        "question": "If the strategy depends on upstream project APIs, features, or releases, is there a gap analysis confirming they exist?",
        "severity_tree": {
            "NO": {"heavy_upstream_dep": "Important", "default": "Minor"},
            "PARTIAL": "Minor",
        },
    },
    # -- Compliance & Governance --
    {
        "id": "NFR-COMP-01",
        "category": "Compliance & Governance",
        "question": "Do all administrative and security-relevant actions emit audit events compatible with OpenShift audit pipeline?",
        "severity_tree": {
            "NO": {"regulated_customers": "Important", "default": "Minor"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-COMP-02",
        "category": "Compliance & Governance",
        "question": "Does persistent data (sessions, logs, cached state) have defined retention, access control, and purge mechanisms?",
        "severity_tree": {
            "NO": {"has_persistent_state": "Important", "default": "N/A"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-COMP-03",
        "category": "Compliance & Governance",
        "question": "If targeting regulated/government customers, does the strategy address air-gapped deployment and testing?",
        "severity_tree": {
            "NO": {"regulated_customers": "Important", "default": "N/A"},
            "PARTIAL": "Minor",
        },
    },
    # -- Cross-Cutting --
    {
        "id": "NFR-CROSS-01",
        "category": "Cross-Cutting",
        "question": "If the strategy involves streaming (SSE, gRPC streams), are partial-state behavior, connection limits, and backpressure specified?",
        "severity_tree": {
            "NO": {"has_streaming": "Important", "default": "N/A"},
            "PARTIAL": "Minor",
        },
    },
    {
        "id": "NFR-CROSS-02",
        "category": "Cross-Cutting",
        "question": "Are breaking changes identified with migration paths and compatibility periods?",
        "severity_tree": {
            "NO": {"has_breaking_changes": "Critical", "default": "N/A"},
            "PARTIAL": "Important",
        },
    },
]


def generate_scan_prompt(strat_text, threat_surface_json=None):
    """Generate the NFR scan prompt for a lightweight LLM agent."""

    checklist_block = []
    for item in NFR_CHECKLIST:
        checklist_block.append(
            f"### {item['id']}: {item['category']}\n"
            f"**Question:** {item['question']}\n"
            f"**Answer:** [YES | NO | PARTIAL | N/A]\n"
            f"**Citation:** [Cite specific section/AC, or 'not mentioned']\n"
            f"**Brief:** [1-2 sentence explanation]\n"
        )

    surface_block = ""
    if threat_surface_json:
        surface_block = (
            "## Threat Surface Inventory (pre-extracted)\n\n"
            "```json\n"
            f"{json.dumps(threat_surface_json, indent=2)}\n"
            "```\n\n"
            "Use this inventory to inform your N/A decisions: if the strategy "
            "does not introduce the surface type, mark the related NFR item N/A.\n\n"
        )

    prompt = f"""You are an NFR checklist scanner. Your job is to check whether a strategy document addresses each item in the NFR checklist below.

RULES:
- Answer each item with exactly YES, NO, PARTIAL, or N/A
- YES: The strategy explicitly addresses this item with specific details
- NO: The strategy does not address this item at all, and it is relevant
- PARTIAL: The strategy mentions this topic but lacks specificity
- N/A: This item is not relevant to this strategy (e.g., no streaming = streaming NFR is N/A)
- For every NO or PARTIAL, cite the specific section or AC where the gap exists, or state "not mentioned"
- Do NOT produce findings, recommendations, or analysis. Just answer the checklist.
- Be strict: vague mentions ("we will ensure security") count as NO, not PARTIAL

{surface_block}## Strategy Document

{strat_text}

## NFR Checklist

Answer each item below:

{"".join(checklist_block)}
## Output Format

After answering all items, produce a JSON summary block:

```json
{{
  "items": [
    {{"id": "NFR-AUTH-01", "answer": "NO", "citation": "Section X", "brief": "..."}},
    ...
  ],
  "summary": {{
    "yes_count": N,
    "no_count": N,
    "partial_count": N,
    "na_count": N
  }}
}}
```
"""
    return prompt


def parse_scan_output(text):
    """Parse NFR scan agent output into structured JSON."""
    # Try to find JSON block in the output
    json_match = None
    # Look for ```json ... ``` blocks
    import re
    for m in re.finditer(r"```json\s*\n(.*?)```", text, re.DOTALL):
        try:
            candidate = json.loads(m.group(1))
            if "items" in candidate:
                json_match = candidate
                break
        except json.JSONDecodeError:
            continue

    if json_match:
        # Enrich with severity from decision tree
        for item_result in json_match.get("items", []):
            item_def = next(
                (d for d in NFR_CHECKLIST if d["id"] == item_result.get("id")),
                None
            )
            if item_def and item_result.get("answer") in ("NO", "PARTIAL"):
                tree = item_def["severity_tree"].get(item_result["answer"], "Minor")
                if isinstance(tree, str):
                    item_result["default_severity"] = tree
                else:
                    # Complex tree: use the default key
                    item_result["default_severity"] = tree.get("default", "Minor")
                    item_result["severity_conditions"] = {
                        k: v for k, v in tree.items() if k != "default"
                    }
            elif item_result.get("answer") in ("YES", "N/A"):
                item_result["default_severity"] = "N/A"

        return json_match

    # Fallback: try to parse individual items from text
    items = []
    for item_def in NFR_CHECKLIST:
        item_id = item_def["id"]
        pattern = rf"{item_id}.*?Answer:\s*(YES|NO|PARTIAL|N/A)"
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            answer = m.group(1).upper()
            items.append({
                "id": item_id,
                "answer": answer,
                "citation": "parsed from text",
                "brief": "",
            })

    return {"items": items, "summary": {"parsed_from_text": True}}


def main():
    parser = argparse.ArgumentParser(
        description="NFR checklist scanner for STRAT documents."
    )
    parser.add_argument(
        "--prompt", metavar="STRAT_FILE",
        help="Generate scan prompt for the given STRAT file"
    )
    parser.add_argument(
        "--surface", metavar="JSON_FILE",
        help="Threat surface JSON file (from extract-threat-surface.py)"
    )
    parser.add_argument(
        "--parse", metavar="OUTPUT_FILE",
        help="Parse scan agent output into structured JSON"
    )
    parser.add_argument(
        "--checklist", action="store_true",
        help="Print the NFR checklist as JSON"
    )
    args = parser.parse_args()

    if args.checklist:
        json.dump(NFR_CHECKLIST, sys.stdout, indent=2)
        print()
        return

    if args.prompt:
        with open(args.prompt, encoding="utf-8") as f:
            strat_text = f.read()

        surface_json = None
        if args.surface:
            with open(args.surface, encoding="utf-8") as f:
                surface_json = json.load(f)

        prompt = generate_scan_prompt(strat_text, surface_json)
        print(prompt)

    elif args.parse:
        with open(args.parse, encoding="utf-8") as f:
            text = f.read()
        result = parse_scan_output(text)
        json.dump(result, sys.stdout, indent=2)
        print()

    else:
        parser.error("Provide --prompt, --parse, or --checklist")


if __name__ == "__main__":
    main()
