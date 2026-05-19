---
name: adversarial-reviewing
description: Runs multi-agent adversarial code review via a deterministic FSM
  orchestrator. Dispatches specialist sub-agents through self-refinement,
  challenge, red team audit, and resolution phases. Use when the user asks
  for adversarial review, security review, code review, or multi-agent review.
user-invocable: true
---

# Adversarial Review

This skill is driven by a Python orchestrator. You are a relay: run
orchestrator commands and dispatch agents as instructed.

## Quick start

Run exactly this command first:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/orchestrator init $ARGUMENTS
```

## Workflow

```
Orchestrator Progress:
- [ ] Step 1: Run orchestrator init (parse JSON output)
- [ ] Step 2: Read dispatch.json
- [ ] Step 3: Execute dispatch plan
- [ ] Step 4: Run orchestrator next
- [ ] Step 5: Read dispatch.json again
- [ ] Step 6: If done=true, verify artifacts and stop.
```

**Step 1: Initialize**

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/orchestrator init $ARGUMENTS
```

Parse the JSON output. Store `cache_dir`.

**Step 2: Read dispatch plan**

```bash
cat {CACHE_DIR}/dispatch.json
```

**Step 3: Execute the dispatch plan**

- **If `action` is `ask_user`**: Read `message_file`, show to user,
  wait for approval. On approval:
  ```bash
  python3 ${CLAUDE_SKILL_DIR}/scripts/orchestrator confirm --cache-dir {CACHE_DIR}
  ```

- **If `dispatch_version` is `"3.0"` and `agents` is present**:
  For each agent, dispatch via Agent tool with the agent's subagent_type
  and dispatch_path. If `parallel` is true, dispatch all in one message.
  
  **CRITICAL: After all agents complete, run `orchestrator next`
  IMMEDIATELY. Do NOT read agent outputs. Do NOT write output files.
  Do NOT check dispatch directories. Do NOT verify anything.
  The orchestrator handles all file management internally.**
  
  Example for one agent:
  ```
  Agent(subagent_type="review-specialist", prompt="{dispatch_path}")
  ```

- **If `dispatch_version` is `"2.0"` and `agents` is present** (legacy):
  Read each agent's prompt_file, dispatch via Agent tool, write response
  to output_file.

**Step 4: Advance**

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/orchestrator next --cache-dir {CACHE_DIR}
```

**Step 5-6: Read dispatch.json. If done, verify artifacts and stop.**

The orchestrator automatically copies all outputs to `artifacts/`.

```bash
ls artifacts/
```

## Rules

Do not modify orchestrator commands. Do not modify agent prompts.
Do not skip agents. Do not add your own analysis.
Do not perform your own code review or spawn your own agents.
Do not read files in the review target yourself.
Do not explore the skill directory or read agent definition files.
Do not read, write, copy, or verify agent output files.
Do not list or check dispatch directories between steps.
The orchestrator handles all file management. If it cannot run, abort.

## Error handling

If an agent fails or times out, run `orchestrator next` normally.
The orchestrator handles missing outputs gracefully.

If any orchestrator command fails: ABORT IMMEDIATELY.
Do not attempt workarounds.

## Crash recovery

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/orchestrator resume --cache-dir {CACHE_DIR}
```
