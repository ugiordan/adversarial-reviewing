#!/usr/bin/env bash
# Shared injection detection logic.
# Source this file; do not execute directly.
# Usage: check_injection <freetext> <finding_id> — appends to ERRORS array

check_injection() {
    local freetext="$1"
    local finding_id="$2"
    local freetext_lower
    freetext_lower=$(echo "$freetext" | tr '[:upper:]' '[:lower:]')

    # High-confidence patterns: single match flags
    local injection_patterns_high=(
        "ignore all previous" "ignore all instructions" "disregard previous"
        "disregard all" "system prompt" "discard previous" "new instructions"
        "real task" "you are now" "forget your" "ignore the above"
    )
    # Context-sensitive patterns: require 2+ matches
    local injection_patterns_context=(
        "you must" "you should" "override" "set aside" "supersede"
        "abandon" "authoritative" "ignore all" "disregard"
    )

    for pattern in "${injection_patterns_high[@]}"; do
        if grep -qF "$pattern" <<< "$freetext_lower"; then
            ERRORS+=("Finding $finding_id: injection pattern detected: '$pattern'")
        fi
    done

    local context_hits=0
    local context_matched=()
    for pattern in "${injection_patterns_context[@]}"; do
        if grep -qF "$pattern" <<< "$freetext_lower"; then
            context_hits=$((context_hits + 1))
            context_matched+=("$pattern")
        fi
    done
    if (( context_hits >= 2 )); then
        ERRORS+=("Finding $finding_id: multiple injection patterns detected: ${context_matched[*]}")
    fi

    # Provenance marker patterns
    if grep -qF "[PROVENANCE::" <<< "$freetext"; then
        ERRORS+=("Finding $finding_id: contains provenance marker pattern in field content")
    fi

    # Field isolation marker patterns
    if grep -qF "[FIELD_DATA_" <<< "$freetext"; then
        ERRORS+=("Finding $finding_id: contains field isolation marker pattern in field content")
    fi
}
