# Evaluation

Measures detection accuracy against a ground-truth corpus of known vulnerabilities
in the opendatahub-operator codebase.

Two approaches are available: the agent-eval-harness integration (recommended for
repeatable automated runs) and the legacy manual approach.

## agent-eval-harness integration

Uses [agent-eval-harness](https://github.com/opendatahub-io/agent-eval-harness)
for automated end-to-end evaluation with MLflow tracking.

### Setup

1. Clone agent-eval-harness alongside this repo
2. Install dependencies: `pip install -e .` in the harness repo
3. Ensure Claude Code CLI is available

### Running

```bash
# Single case, Opus
/eval-run --model opus --case odh-operator-security

# Single case, Sonnet (for model comparison)
/eval-run --model sonnet --case odh-operator-security
```

### How it works

`eval.yaml` configures the harness pipeline:

1. **Runner**: `claude-code` invokes the adversarial-reviewing skill
2. **Tool interception**: Auto-approves scope confirmation prompts via PreToolUse hooks
3. **Artifact collection**: Collects the `--save` output report
4. **Judges** (6 total):
   - `has_findings`: inline check, verifies structured output exists
   - `detection_rate`: external code judge (`judges/detection_judge.py`), scores
     against ground truth using file path + keyword matching. Returns 0.0-1.0.
   - `false_positive_rate`: external code judge, passes if FP rate < 30%
   - `severity_accuracy`: external code judge, scores severity classification
   - `output_quality`: LLM judge, scores report quality 1-5
   - `cost_reasonable`: inline check, verifies cost < $20
5. **Thresholds**: detection_rate min_mean 0.35, output_quality min_mean 3.0

### Dataset cases

Each case under `dataset/cases/` contains:
- `input.yaml`: prompt and expected specialist/finding metadata
- `reference.yaml`: ground truth findings with detection signals

Current cases:
- `odh-operator-security`: 17 verified findings across 9 categories

### External judges

`judges/detection_judge.py` exposes three scorer functions matching the harness's
`importlib` callable signature `(outputs=None, **kwargs) -> (score, rationale)`:

- `score_detection`: detection rate against ground truth (0.0-1.0)
- `score_false_positive_rate`: bool pass/fail at 30% threshold
- `score_severity_accuracy`: severity classification accuracy (0.0-1.0)

The matching algorithm scores each finding against ground truth entries using file
path matching (+3 points) and detection signal keyword hits in title (+2 each) and
evidence (+1 each). A match requires score >= 3.

## Legacy manual approach

Semi-automated: `run-experiment.sh` creates output directories and `score.py`
scores findings, but the adversarial-reviewing invocation is manual.

### Test Matrix

| Run ID | Model | Representation | Detection Rate | False Positive Rate |
|--------|-------|---------------|---------------|-------------------|
| R0-opus-baseline | Opus | R0 (raw source) | 41.2% (7/17) | 11.1% (1/9) |
| R1a-opus-ir-only | Opus | R1a (IR only) | see scores.json | see scores.json |
| R1b-opus-ir-plus-source | Opus | R1b (IR + source) | see scores.json | see scores.json |
| R2-opus-pattern-ir | Opus | R2 (pattern IR) | see scores.json | see scores.json |

### Running

```bash
./run-experiment.sh \
  --repo /path/to/opendatahub-operator \
  --ground-truth ground-truth-odh-operator.yaml \
  --model opus \
  --run-id R0-opus-baseline \
  --representation R0
```

### Scoring

```bash
python3 score.py findings.json ground-truth-odh-operator.yaml --output scores.json
```

## Ground truth

`ground-truth-odh-operator.yaml` (and its copy at `dataset/cases/odh-operator-security/reference.yaml`)
contains 17 verified findings across categories: crypto, input validation, RBAC, webhooks,
data flow, info disclosure, bounds checking, randomness. Each entry has detection signal
keywords that the scorer matches against finding titles and evidence.
