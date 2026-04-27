#!/usr/bin/env python3
"""Detect references to external resources in cached code files.

Scans code for patterns that indicate dependencies on definitions
outside the reviewed scope: Go imports from other repos, file paths
pointing elsewhere, RBAC resourceNames, kustomize external references.

Usage:
    python3 detect-external-refs.py <code_dir> --source-root <path> [--json]

Output: JSON list of detected references with fetchability info.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


GO_IMPORT_RE = re.compile(
    r'(?:^|\s)"(github\.com/([^/]+)/([^/"]+)(?:/[^"]*)?)"',
    re.MULTILINE,
)

FILE_PATH_COMMENT_RE = re.compile(
    r'(?://|#)\s*(?:See|see|cf\.|ref:|defined in|from)\s+'
    r'["\']?([a-zA-Z0-9_./-]*(?:/[a-zA-Z0-9_./-]+)+\.(?:yaml|yml|json))["\']?',
)

RBAC_RESOURCE_NAMES_RE = re.compile(
    r'resourceNames:\s*\[([^\]]+)\]',
)

KUSTOMIZE_REF_RE = re.compile(
    r'^\s*-\s+((?:\.\./|https?://)[^\s#]+)',
    re.MULTILINE,
)

CRD_APIVERSION_RE = re.compile(
    r'apiVersion:\s*([a-z0-9.-]+\.(?:io|com|org|dev)/[a-z0-9]+)',
)

MANAGED_BY_RE = re.compile(
    r'app\.kubernetes\.io/managed-by:\s*["\']?(\S+)',
)

EMPTY_POD_SELECTOR_RE = re.compile(
    r'podSelector:\s*\{\s*\}',
)

K8S_BUILTIN_GROUPS = {
    "apps/v1", "batch/v1", "core/v1", "v1",
    "rbac.authorization.k8s.io/v1",
    "networking.k8s.io/v1",
    "policy/v1", "policy/v1beta1",
    "admissionregistration.k8s.io/v1",
    "apiextensions.k8s.io/v1",
    "autoscaling/v1", "autoscaling/v2",
    "coordination.k8s.io/v1",
    "storage.k8s.io/v1",
    "certificates.k8s.io/v1",
    "discovery.k8s.io/v1",
    "events.k8s.io/v1",
    "flowcontrol.apiserver.k8s.io/v1",
    "node.k8s.io/v1",
    "scheduling.k8s.io/v1",
}


MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB


def _build_line_offsets(content):
    offsets = [0]
    idx = content.find("\n")
    while idx != -1:
        offsets.append(idx + 1)
        idx = content.find("\n", idx + 1)
    return offsets


def _line_at(offsets, pos):
    lo, hi = 0, len(offsets)
    while lo < hi:
        mid = (lo + hi) // 2
        if offsets[mid] <= pos:
            lo = mid + 1
        else:
            hi = mid
    return lo


API_REPOS = {
    "openshift/api",
    "operator-framework/api",
    "operator-framework/operator-lifecycle-manager",
    "kubernetes-sigs/controller-runtime",
    "kubernetes-sigs/kustomize",
}


def _is_relevant_import(org, repo, org_repo, source_org):
    if org == source_org:
        return True
    if org_repo in API_REPOS:
        return True
    return False


def detect_go_imports(content, filename, source_root_repo, line_offsets):
    refs = []
    seen = set()
    source_org = source_root_repo.split("/")[0] if source_root_repo else ""

    for match in GO_IMPORT_RE.finditer(content):
        org = match.group(2)
        repo = match.group(3)
        org_repo = f"{org}/{repo}"
        if org_repo in seen or org_repo == source_root_repo:
            continue
        if not _is_relevant_import(org, repo, org_repo, source_org):
            continue
        seen.add(org_repo)
        refs.append({
            "type": "go_import",
            "reference": org_repo,
            "file": filename,
            "line": _line_at(line_offsets, match.start()),
            "fetchable": True,
            "fetch_source": f"https://github.com/{org_repo}",
        })

    return refs


def detect_file_path_refs(content, filename, source_root, line_offsets):
    refs = []
    for match in FILE_PATH_COMMENT_RE.finditer(content):
        path_ref = match.group(1)
        resolved = (Path(source_root) / path_ref).resolve()
        in_source = str(resolved).startswith(str(Path(source_root).resolve()))
        if in_source and resolved.exists():
            continue

        parent_resolved = None
        for parent in Path(source_root).parents:
            candidate = parent / path_ref
            if candidate.exists():
                parent_resolved = str(candidate)
                break

        refs.append({
            "type": "file_path",
            "reference": path_ref,
            "file": filename,
            "line": _line_at(line_offsets, match.start()),
            "fetchable": parent_resolved is not None,
            "fetch_source": parent_resolved,
        })
    return refs


def detect_rbac_resources(content, filename, line_offsets):
    refs = []
    for match in RBAC_RESOURCE_NAMES_RE.finditer(content):
        names_str = match.group(1)
        names = [n.strip().strip('"').strip("'") for n in names_str.split(",")]
        for name in names:
            if not name or name.startswith("{{"):
                continue
            refs.append({
                "type": "rbac_resource",
                "reference": name,
                "file": filename,
                "line": _line_at(line_offsets, match.start()),
                "fetchable": False,
                "fetch_source": None,
            })
    return refs


def detect_kustomize_refs(content, filename, source_root, line_offsets):
    refs = []
    basename = os.path.basename(filename)
    if basename not in ("kustomization.yaml", "kustomization.yml", "kustomize.yaml"):
        return refs

    for match in KUSTOMIZE_REF_RE.finditer(content):
        ref = match.group(1)
        if ref.startswith("http"):
            refs.append({
                "type": "kustomize_ref",
                "reference": ref,
                "file": filename,
                "line": _line_at(line_offsets, match.start()),
                "fetchable": True,
                "fetch_source": ref,
            })
        elif ref.startswith("../"):
            resolved = (Path(source_root) / os.path.dirname(filename) / ref).resolve()
            in_source = str(resolved).startswith(str(Path(source_root).resolve()))
            if not in_source:
                refs.append({
                    "type": "kustomize_ref",
                    "reference": ref,
                    "file": filename,
                    "line": _line_at(line_offsets, match.start()),
                    "fetchable": resolved.exists(),
                    "fetch_source": str(resolved) if resolved.exists() else None,
                })
    return refs


def detect_crd_refs(content, filename, source_org, line_offsets):
    refs = []
    seen = set()
    org_domain = source_org.replace("-", "") if source_org else ""
    for match in CRD_APIVERSION_RE.finditer(content):
        api_version = match.group(1)
        if api_version in seen or api_version in K8S_BUILTIN_GROUPS:
            continue
        group = api_version.split("/")[0]
        if org_domain and org_domain in group.replace(".", ""):
            continue
        seen.add(api_version)
        refs.append({
            "type": "crd_ref",
            "reference": api_version,
            "file": filename,
            "line": _line_at(line_offsets, match.start()),
            "fetchable": False,
            "fetch_source": None,
        })
    return refs


def detect_deployment_signals(content, filename, line_offsets):
    signals = []
    for match in MANAGED_BY_RE.finditer(content):
        signals.append({
            "type": "deployment_signal",
            "reference": f"managed-by:{match.group(1)}",
            "file": filename,
            "line": _line_at(line_offsets, match.start()),
            "fetchable": False,
            "fetch_source": None,
        })
    for match in EMPTY_POD_SELECTOR_RE.finditer(content):
        if "NetworkPolicy" in content[:match.start()].rsplit("---", 1)[-1]:
            signals.append({
                "type": "deployment_signal",
                "reference": "namespace-wide-network-policy",
                "file": filename,
                "line": _line_at(line_offsets, match.start()),
                "fetchable": False,
                "fetch_source": None,
            })
    return signals


def detect_repo_name(source_root):
    go_mod = Path(source_root) / "go.mod"
    if go_mod.exists():
        with open(go_mod, encoding="utf-8") as f:
            for line in f:
                if line.startswith("module "):
                    mod_path = line.split()[1].strip()
                    if mod_path.startswith("github.com/"):
                        parts = mod_path.split("/")
                        if len(parts) >= 3:
                            return f"{parts[1]}/{parts[2]}"
    return None


def scan_directory(code_dir, source_root):
    all_refs = []
    source_repo = detect_repo_name(source_root)
    source_org = source_repo.split("/")[0] if source_repo else ""

    for root, _dirs, files in os.walk(code_dir):
        for fname in files:
            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, code_dir)

            try:
                size = os.path.getsize(filepath)
            except OSError:
                continue
            if size > MAX_FILE_SIZE or size == 0:
                continue

            try:
                with open(filepath, "rb") as f:
                    head = f.read(512)
                if b"\x00" in head:
                    continue
            except OSError:
                continue

            try:
                with open(filepath, encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue

            line_offsets = _build_line_offsets(content)

            if fname.endswith(".go"):
                all_refs.extend(detect_go_imports(content, rel_path, source_repo, line_offsets))

            if fname.endswith((".yaml", ".yml")):
                all_refs.extend(detect_rbac_resources(content, rel_path, line_offsets))
                all_refs.extend(detect_kustomize_refs(content, rel_path, source_root, line_offsets))
                all_refs.extend(detect_crd_refs(content, rel_path, source_org, line_offsets))
                all_refs.extend(detect_deployment_signals(content, rel_path, line_offsets))

            all_refs.extend(detect_file_path_refs(content, rel_path, source_root, line_offsets))

    seen = set()
    deduped = []
    for ref in all_refs:
        key = (ref["type"], ref["reference"])
        if key not in seen:
            seen.add(key)
            deduped.append(ref)

    return deduped


def main():
    parser = argparse.ArgumentParser(description="Detect external references in code")
    parser.add_argument("code_dir", help="Directory containing cached code files")
    parser.add_argument("--source-root", required=True, help="Original source root path")
    parser.add_argument("--json", action="store_true", help="Output JSON (default)")
    args = parser.parse_args()

    if not os.path.isdir(args.code_dir):
        print(json.dumps({"error": f"Not a directory: {args.code_dir}", "references": []}))
        sys.exit(1)

    refs = scan_directory(args.code_dir, args.source_root)

    ext_refs = [r for r in refs if r["type"] != "deployment_signal"]
    dep_signals = [r for r in refs if r["type"] == "deployment_signal"]
    fetchable = [r for r in ext_refs if r["fetchable"]]
    unfetchable = [r for r in ext_refs if not r["fetchable"]]

    output = {
        "references": sorted(ext_refs, key=lambda r: (r["type"], r["reference"])),
        "deployment_signals": dep_signals,
        "summary": {
            "total": len(ext_refs),
            "fetchable": len(fetchable),
            "unfetchable": len(unfetchable),
            "deployment_signals": len(dep_signals),
        },
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
