from __future__ import annotations

import json
import pytest
from orchestrator.telemetry import (
    init_tracer, start_span, end_span, record_metric,
    flush, compute_cost, MODEL_PRICING, _tracer,
)


@pytest.fixture(autouse=True)
def _reset_tracer():
    import orchestrator.telemetry as tel
    tel._tracer = None
    yield
    tel._tracer = None


class TestTelemetryNoOp:
    def test_init_without_otel(self, tmp_path):
        init_tracer("test-service", str(tmp_path))

    def test_span_lifecycle(self, tmp_path):
        init_tracer("test-service", str(tmp_path))
        ctx = start_span("test.span", {"key": "value"})
        assert ctx is not None
        end_span(ctx, {"result": "ok"})

    def test_record_metric(self, tmp_path):
        init_tracer("test-service", str(tmp_path))
        record_metric("test.metric", 42.0, {"agent": "SEC"})

    def test_flush_writes_telemetry_json(self, tmp_path):
        init_tracer("test-service", str(tmp_path))
        ctx = start_span("review_run", {"profile": "code"})
        child = start_span("agent.SEC", {"tokens_in": 1000}, parent=ctx)
        end_span(child, {"tokens_out": 500})
        end_span(ctx, {})
        flush()
        path = tmp_path / "telemetry.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["spans"]) == 2
        assert data["spans"][0]["name"] == "review_run"

    def test_span_parent_child(self, tmp_path):
        init_tracer("test-service", str(tmp_path))
        parent = start_span("root", {})
        child = start_span("child", {}, parent=parent)
        assert child.parent_id == parent.span_id
        flush()
        data = json.loads((tmp_path / "telemetry.json").read_text())
        root = next(s for s in data["spans"] if s["name"] == "root")
        assert child.span_id in root["children"]

    def test_noop_before_init(self):
        ctx = start_span("noop", {})
        assert ctx.span_id == "noop"
        end_span(ctx, {})
        record_metric("m", 1.0, {})
        flush()  # should not crash


class TestCostComputation:
    def test_known_model(self):
        cost = compute_cost("claude-opus-4-6", tokens_in=1000, tokens_out=500, tokens_thinking=2000)
        expected = (1000 * 15.0 + 500 * 75.0 + 2000 * 15.0) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_unknown_model_returns_zero(self):
        cost = compute_cost("unknown-model", tokens_in=1000, tokens_out=500, tokens_thinking=0)
        assert cost == 0.0

    def test_sonnet_pricing(self):
        cost = compute_cost("claude-sonnet-4-6", tokens_in=1000, tokens_out=1000, tokens_thinking=1000)
        expected = (1000 * 3.0 + 1000 * 15.0 + 1000 * 3.0) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_all_models_have_pricing(self):
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing
            assert "thinking" in pricing


class TestMetrics:
    def test_metrics_recorded(self, tmp_path):
        init_tracer("test", str(tmp_path))
        record_metric("review.tokens.total", 5000, {"agent": "SEC"})
        record_metric("review.findings.count", 3, {"severity": "Important"})
        flush()
        data = json.loads((tmp_path / "telemetry.json").read_text())
        assert len(data["metrics"]) == 2
        assert data["metrics"][0]["name"] == "review.tokens.total"
        assert data["metrics"][0]["value"] == 5000
