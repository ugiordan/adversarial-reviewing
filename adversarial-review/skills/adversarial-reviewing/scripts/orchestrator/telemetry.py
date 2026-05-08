from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

MODEL_PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0, "thinking": 15.0},
    "claude-opus-4-7": {"input": 15.0, "output": 75.0, "thinking": 15.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "thinking": 3.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0, "thinking": 0.80},
}

_tracer: _Tracer | None = None


@dataclass
class SpanContext:
    span_id: str
    name: str
    attributes: dict = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    parent_id: str = ""
    children: list[str] = field(default_factory=list)


class _Tracer:
    def __init__(self, service_name: str, cache_dir: str):
        self.service_name = service_name
        self.cache_dir = cache_dir
        self.spans: dict[str, SpanContext] = {}
        self.metrics: list[dict] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"span_{self._counter}"


def init_tracer(service_name: str, cache_dir: str) -> None:
    global _tracer
    _tracer = _Tracer(service_name, cache_dir)


def start_span(name: str, attributes: dict, parent: SpanContext = None) -> SpanContext:
    if _tracer is None:
        return SpanContext(span_id="noop", name=name)
    span_id = _tracer._next_id()
    ctx = SpanContext(
        span_id=span_id, name=name,
        attributes=dict(attributes),
        start_time=time.time(),
        parent_id=parent.span_id if parent else "",
    )
    _tracer.spans[span_id] = ctx
    if parent and parent.span_id in _tracer.spans:
        _tracer.spans[parent.span_id].children.append(span_id)
    return ctx


def end_span(ctx: SpanContext, attributes: dict) -> None:
    if _tracer is None or ctx.span_id not in _tracer.spans:
        return
    span = _tracer.spans[ctx.span_id]
    span.end_time = time.time()
    span.attributes.update(attributes)


def record_metric(name: str, value: float, attributes: dict) -> None:
    if _tracer is None:
        return
    _tracer.metrics.append({
        "name": name,
        "value": value,
        "attributes": attributes,
        "timestamp": time.time(),
    })


def flush() -> None:
    if _tracer is None:
        return
    spans_data = []
    for span in _tracer.spans.values():
        spans_data.append({
            "name": span.name,
            "span_id": span.span_id,
            "parent_id": span.parent_id,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ms": round((span.end_time - span.start_time) * 1000, 2)
            if span.end_time > 0 else 0,
            "attributes": span.attributes,
            "children": span.children,
        })
    data = {
        "service": _tracer.service_name,
        "spans": spans_data,
        "metrics": _tracer.metrics,
    }
    path = Path(_tracer.cache_dir) / "telemetry.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)

    _try_otlp_export(spans_data, _tracer.metrics)


def compute_cost(model: str, tokens_in: int, tokens_out: int,
                 tokens_thinking: int) -> float:
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0
    return (
        tokens_in * pricing["input"]
        + tokens_out * pricing["output"]
        + tokens_thinking * pricing["thinking"]
    ) / 1_000_000


def _try_otlp_export(spans: list, metrics: list) -> None:
    import os
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    try:
        from opentelemetry.sdk.trace import TracerProvider  # noqa: F401
        # OTel SDK export would be implemented here
    except ImportError:
        pass
