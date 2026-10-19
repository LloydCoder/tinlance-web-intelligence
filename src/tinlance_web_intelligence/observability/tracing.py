"""Privacy-safe, no-op-by-default distributed tracing helpers."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from threading import Lock

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.trace import ProxyTracerProvider, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")
_provider_lock = Lock()
_provider: TracerProvider | None = None
_configured_endpoint: str | None = None


def create_tracer_provider(
    endpoint: str,
    *,
    exporter_factory: Callable[[str], SpanExporter] | None = None,
) -> TracerProvider:
    """Build a batch-exporting provider; the caller must supply a validated endpoint."""

    exporter = (exporter_factory or OTLPSpanExporter)(endpoint)
    provider = TracerProvider(
        resource=Resource.create({"service.name": "tinlance-web-intelligence"})
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


def configure_tracing(endpoint: str | None) -> TracerProvider | None:
    """Install OTLP tracing only for an explicitly configured collector endpoint."""

    global _configured_endpoint, _provider
    if endpoint is None:
        return None
    with _provider_lock:
        if _provider is not None:
            if endpoint != _configured_endpoint:
                raise RuntimeError("OpenTelemetry provider already configured for another endpoint")
            return _provider
        provider = create_tracer_provider(endpoint)
        current_provider = trace.get_tracer_provider()
        if not isinstance(current_provider, ProxyTracerProvider):
            provider.shutdown()
            raise RuntimeError("OpenTelemetry provider is already configured by another owner")
        trace.set_tracer_provider(provider)
        _provider = provider
        _configured_endpoint = endpoint
        return provider


def tracing_export_configured() -> bool:
    """Return whether this process configured an OTLP exporter; never exposes its URL."""

    return _provider is not None


def tracing_export_mode() -> str:
    """Describe exporter configuration without disclosing endpoint details."""

    return "otlp" if tracing_export_configured() else "noop"


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


def safe_span_attributes(attributes: Mapping[str, str]) -> dict[str, str]:
    """Filter attributes to bounded, low-cardinality values before span recording."""

    allowed = {"operation", "component", "outcome", "error_class"}
    return {
        key: value
        for key, value in attributes.items()
        if key in allowed and isinstance(value, str) and 0 < len(value) <= 64
    }


@contextmanager
def start_span(
    name: str, attributes: Mapping[str, str], *, parent: Context | None = None
) -> Iterator[Span]:
    """Start a span with only an allowlisted, low-cardinality attribute set."""
    safe = safe_span_attributes(attributes)
    with trace.get_tracer("tinlance_web_intelligence").start_as_current_span(
        name, context=parent
    ) as span:
        for key, value in safe.items():
            span.set_attribute(key, value)
        yield span
