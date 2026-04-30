from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from .types import Delimiters

MIN_OUTPUT_SIZE = 500


@dataclass
class ComplianceResult:
    passed: bool = True
    error: str = ""
    warnings: int = 0
    warning_details: list[str] = field(default_factory=list)


def check_outputs_exist(output_files: list[str]) -> ComplianceResult:
    missing = [f for f in output_files if not os.path.exists(f)]
    if missing:
        names = ", ".join(os.path.basename(f) for f in missing)
        return ComplianceResult(passed=False, error=f"Missing output files: {names}")
    return ComplianceResult()


def check_delimiters(output_file: str, delimiters: Delimiters) -> ComplianceResult:
    content = Path(output_file).read_text()
    begin_count = content.count(delimiters.begin)
    end_count = content.count(delimiters.end)
    if begin_count == 0 or end_count == 0:
        return ComplianceResult(
            passed=False,
            error=f"Delimiters missing in {os.path.basename(output_file)}",
        )
    if begin_count > 1 or end_count > 1:
        return ComplianceResult(
            passed=False,
            error=f"Multiple delimiter pairs in {os.path.basename(output_file)}",
        )
    begin_idx = content.index(delimiters.begin)
    end_idx = content.index(delimiters.end)
    if begin_idx >= end_idx:
        return ComplianceResult(
            passed=False,
            error=f"Delimiters in wrong order in {os.path.basename(output_file)}",
        )
    return ComplianceResult()


def check_prompt_hashes(prompt_hash_map: dict[str, str]) -> ComplianceResult:
    for path, expected in prompt_hash_map.items():
        if not os.path.exists(path):
            return ComplianceResult(passed=False, error=f"Prompt file missing: {path}")
        actual_hash = "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if actual_hash != expected:
            return ComplianceResult(
                passed=False,
                error=f"Prompt tamper detected: {os.path.basename(path)}",
            )
    return ComplianceResult()


def check_output_sizes(output_files: list[str],
                       threshold: int = MIN_OUTPUT_SIZE) -> ComplianceResult:
    result = ComplianceResult()
    for f in output_files:
        size = os.path.getsize(f)
        if size < threshold:
            result.warnings += 1
            result.warning_details.append(
                f"{os.path.basename(f)}: {size} bytes (< {threshold})"
            )
    return result


def compute_content_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode()).hexdigest()


@dataclass
class StructuralResult:
    passed: bool = True
    findings_count: int = 0
    has_comparative: bool = False
    warnings: list[str] = field(default_factory=list)


_FINDING_HEADING = re.compile(r"^###\s+\w+-\d+", re.MULTILINE)
_NO_FINDINGS = re.compile(r"NO_FINDINGS_REPORTED")
_COMPARATIVE_TERMS = re.compile(
    r"\b(however|alternatively|on the other hand|could also be|"
    r"compared to|counter-?argument|not necessarily|might not be|"
    r"could be interpreted|false positive)\b",
    re.IGNORECASE,
)


def check_finding_structure(output: str) -> StructuralResult:
    if _NO_FINDINGS.search(output):
        return StructuralResult(passed=True, findings_count=0)
    findings = _FINDING_HEADING.findall(output)
    if not findings:
        return StructuralResult(
            passed=False, findings_count=0,
            warnings=["No finding template or NO_FINDINGS_REPORTED marker"],
        )
    return StructuralResult(passed=True, findings_count=len(findings))


def check_comparative_reasoning(output: str) -> bool:
    return bool(_COMPARATIVE_TERMS.search(output))
