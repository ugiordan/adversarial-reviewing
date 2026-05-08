from . import self_refinement, challenge_round

# Phase extension registry: maps phase name to compose_extensions function.
# These extend the base prompt with phase-specific instructions.
#
# report and resolution phases have different interfaces:
#   - report.compose_report_prompt: standalone prompt, not an extension
#   - resolution.run_resolution: execution step, not prompt composition
# They are invoked directly from fsm.py, not through this registry.
PHASE_EXTENSIONS = {
    "self-refinement": self_refinement.compose_extensions,
    "challenge-round": challenge_round.compose_extensions,
}
