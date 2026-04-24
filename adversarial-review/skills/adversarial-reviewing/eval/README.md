# Evaluation

Measures detection accuracy against a ground-truth corpus of known vulnerabilities in the opendatahub-operator codebase.

## Test Matrix

| Run ID | Model | Representation | Detection Rate | False Positive Rate |
|--------|-------|---------------|---------------|-------------------|
| R0-opus-baseline | Opus | R0 (raw source) | 41.2% (7/17) | 11.1% (1/9) |
| R1a-opus-ir-only | Opus | R1a (IR only) | see scores.json | see scores.json |
| R1b-opus-ir-plus-source | Opus | R1b (IR + source) | see scores.json | see scores.json |
| R2-opus-pattern-ir | Opus | R2 (pattern IR) | see scores.json | see scores.json |

### Planned

| Run ID | Model | Representation | Status |
|--------|-------|---------------|--------|
| R0-sonnet-baseline | Sonnet | R0 (raw source) | not yet run |
| R0-haiku-baseline | Haiku | R0 (raw source) | not yet run |

## Running an experiment

```bash
# Opus baseline (R0, raw source)
./run-experiment.sh \
  --repo /path/to/opendatahub-operator \
  --ground-truth ground-truth-odh-operator.yaml \
  --model opus \
  --run-id R0-opus-baseline \
  --representation R0

# Sonnet baseline (same setup, different model)
./run-experiment.sh \
  --repo /path/to/opendatahub-operator \
  --ground-truth ground-truth-odh-operator.yaml \
  --model sonnet \
  --run-id R0-sonnet-baseline \
  --representation R0
```

The script is semi-automated: it creates the output directory and scores findings, but the actual adversarial-reviewing invocation is manual (requires a Claude Code session).

## Scoring

```bash
python3 score.py findings.json ground-truth-odh-operator.yaml --output scores.json
```

Metrics: detection rate, false positive rate, severity accuracy, source trust accuracy.

## Ground truth

`ground-truth-odh-operator.yaml` contains 17 verified findings across categories: crypto, input validation, RBAC, webhooks, data flow, info disclosure. Each entry has detection signal keywords that the scorer matches against finding titles and evidence.
