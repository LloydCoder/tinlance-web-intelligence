"""Privacy-safe, no-op-by-default distributed tracing helpers."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")


def validate_traceparent(value: str | None) -> str | None:
    if value is None:
        return None
    if not _TRACEPARENT.fullmatch(value):
        return None
    version, trace_id, span_id, _flags = value.split("-")
    if version == "ff" or set(trace_id) == {"0"} or set(span_id) == {"0"}:
        return None
    return value


def extract_valid_traceparent(headers: Mapping[str, str]) -> str | None:
    value = next((v for k, v in headers.items() if k.lower() == "traceparent"), None)
    return validate_traceparent(value)


def inject_traceparent(headers: MutableMapping[str, str], traceparent: str | None) -> None:
    valid = validate_traceparent(traceparent)
    if valid is not None:
        headers["traceparent"] = valid


def inject_current_traceparent(headers: MutableMapping[str, str]) -> None:
    """Inject W3C trace context only; baggage is deliberately not propagated."""
    carrier: dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)
    value = extract_valid_traceparent(carrier)
    if value is not None:
        headers["traceparent"] = value


@contextmanager
def start_span(
    name: str, attributes: Mapping[str, str], *, parent: Context | None = None
) -> Iterator[Span]:
    """Start a span with only an allowlisted, low-cardinality attribute set."""
    allowed = {"operation", "component", "outcome", "error_class"}
    safe = {key: value for key, value in attributes.items() if key in allowed}
    with trace.get_tracer("tinlance_web_intelligence").start_as_current_span(
        name, context=parent
    ) as span:
        for key, value in safe.items():
            if len(value) <= 64:
                span.set_attribute(key, value)
        yield span
