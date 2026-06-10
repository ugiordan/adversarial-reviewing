---
name: adversarial-reviewing
description: Runs multi-agent adversarial code review via a deterministic FSM
  orchestrator. Dispatches specialist sub-agents through self-refinement,
  challenge, red team audit, and resolution phases. Use when the user asks
  for adversarial review, security review, code review, or multi-agent review.
user-invocable: true
---

# Adversarial Review

This skill runs a multi-agent security review via a Python orchestrator.

## Quick start

Run exactly this command:

```bash
cd ${CLAUDE_SKILL_DIR} && python3 -m scripts.orchestrator run-all $ARGUMENTS
```

This runs the full review pipeline (init, confirm, self-refinement,
challenge, red-team audit, report). No further action needed.

The command will take 30-90 minutes depending on repo size. Wait for
it to complete. Use `timeout: 600000` on the Bash tool call.

## Output

When complete, the command prints JSON with `{"status": "done"}`.
Review artifacts are in `${CLAUDE_SKILL_DIR}/artifacts/`.

## Legacy workflow

If `run-all` is not available, fall back to the step-by-step protocol:

```bash
cd ${CLAUDE_SKILL_DIR} && python3 -m scripts.orchestrator init $ARGUMENTS
```

Then follow the dispatch.json loop (confirm, dispatch agents, next)
until done=true.

## Error handling

If the command fails, report the error and exit. Do not retry.
Do not re-initialize. Do not improvise recovery.
