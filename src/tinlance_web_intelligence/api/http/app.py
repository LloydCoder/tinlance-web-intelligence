"""FastAPI application factory with fail-closed Platform token verification."""

from __future__ import annotations

import hmac
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from tinlance_web_intelligence.api.http.middleware import RequestBodyLimitMiddleware
from tinlance_web_intelligence.api.http.routes.health import router as health_router
from tinlance_web_intelligence.api.http.routes.jobs import router as jobs_router
from tinlance_web_intelligence.api.http.routes.monitors import router as monitors_router
from tinlance_web_intelligence.api.http.routes.research import router as research_router
from tinlance_web_intelligence.api.http.routes.usage import router as usage_router
from tinlance_web_intelligence.api.http.routes.world_intelligence import (
    router as world_intelligence_router,
)
from tinlance_web_intelligence.commercial.entitlements import EntitlementResolver
from tinlance_web_intelligence.auth.jwks import PlatformTokenVerifier
from tinlance_web_intelligence.auth.principal import DenyAllPrincipalVerifier, PrincipalVerifier
from tinlance_web_intelligence.config import ConfigurationError, Settings
from tinlance_web_intelligence.monitors.service import MonitorService
from tinlance_web_intelligence.observability.tracing import (
    configure_tracing,
    extract_valid_traceparent,
    start_span,
)
from tinlance_web_intelligence.persistence.factory import (
    create_job_repository,
    create_monitor_repository,
    create_source_evidence_outbox,
    create_usage_ledger,
)
from tinlance_web_intelligence.persistence.monitor_protocol import MonitorRepository
from tinlance_web_intelligence.persistence.protocols import (
    JobRepository,
    SourceEvidenceOutbox,
    UsageLedger,
)


def create_app(
    *,
    settings: Settings | None = None,
    repository: JobRepository | None = None,
    verifier: PrincipalVerifier | None = None,
    evidence_outbox: SourceEvidenceOutbox | None = None,
    monitor_repository: MonitorRepository | None = None,
    usage_ledger: UsageLedger | None = None,
    entitlement_resolver: EntitlementResolver | None = None,
) -> FastAPI:
    config = settings or Settings.from_env()
    tracer_provider = configure_tracing(config.otel_exporter_endpoint)
    if (
        verifier is None
        and config.identity_issuer
        and config.identity_audience
        and config.identity_jwks_url
    ):
        verifier = PlatformTokenVerifier(
            issuer=config.identity_issuer,
            audience=config.identity_audience,
            jwks_url=config.identity_jwks_url,
        )
    if config.environment == "production" and verifier is None:
        raise ConfigurationError("production requires a configured Platform token verifier")
    if config.environment == "production" and entitlement_resolver is None:
        raise ConfigurationError(
            "production requires an entitlement resolver from the approved billing boundary"
        )
    trusted_verifier = verifier or DenyAllPrincipalVerifier()
    repo = repository or create_job_repository(config)
    monitors = monitor_repository or create_monitor_repository(config)
    usage = usage_ledger or create_usage_ledger(config)
    docs_enabled = config.environment in {"development", "test"}
    app = FastAPI(
        title="Tinlance Web Intelligence API",
        version="1.0.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.state.repository = repo
    app.state.monitor_repository = monitors
    app.state.usage_ledger = usage
    app.state.entitlement_resolver = entitlement_resolver
    app.state.monitor_service = MonitorService(repository=monitors, job_repository=repo)
    app.state.settings = config
    registry = CollectorRegistry()
    http_requests = Counter(
        "twi_http_requests_total",
        "Completed HTTP requests, excluding metrics scrapes.",
        ("method", "route", "status"),
        registry=registry,
    )
    http_duration = Histogram(
        "twi_http_request_duration_seconds",
        "HTTP request latency in seconds, excluding metrics scrapes.",
        ("method", "route"),
        registry=registry,
    )
    http_in_flight = Gauge(
        "twi_http_in_flight_requests",
        "HTTP requests currently being handled by this API process.",
        ("method",),
        registry=registry,
    )
    job_counts = Gauge(
        "twi_jobs_total",
        "Durable job count by lifecycle status.",
        ("status",),
        registry=registry,
    )
    oldest_queued_age = Gauge(
        "twi_jobs_oldest_queued_age_seconds",
        "Age of the oldest queued job in seconds.",
        registry=registry,
    )
    outbox_counts = Gauge(
        "twi_source_evidence_outbox_events_total",
        "Durable source-evidence outbox event count by status.",
        ("status",),
        registry=registry,
    )
    monitor_counts = Gauge(
        "twi_monitors_total",
        "Durable monitor count by lifecycle status.",
        ("status",),
        registry=registry,
    )
    oldest_pending_outbox_age = Gauge(
        "twi_source_evidence_outbox_oldest_pending_age_seconds",
        "Age of the oldest pending source-evidence outbox event in seconds.",
        registry=registry,
    )
    metrics_collection_errors = Counter(
        "twi_metrics_collection_errors_total",
        "Failures while collecting durable queue or outbox metrics.",
        ("component",),
        registry=registry,
    )
    app.state.metrics_registry = registry
    outbox = evidence_outbox or create_source_evidence_outbox(config)
    app.state.evidence_outbox = outbox
    if evidence_outbox is None:
        app.router.on_shutdown.append(outbox.close)
    if repository is None:
        app.router.on_shutdown.append(repo.close)
    if monitor_repository is None:
        app.router.on_shutdown.append(monitors.close)
    if usage_ledger is None:
        app.router.on_shutdown.append(usage.close)
    if tracer_provider is not None:
        app.router.on_shutdown.append(tracer_provider.shutdown)

    @app.get("/internal/metrics", include_in_schema=False)
    def metrics() -> Response:
        try:
            jobs_snapshot = repo.metrics_snapshot()
        except Exception:
            metrics_collection_errors.labels("jobs").inc()
        else:
            for status in ("queued", "running", "succeeded", "failed", "cancelled"):
                job_counts.labels(status).set(jobs_snapshot.get(f"jobs_{status}", 0.0))
            oldest_queued_age.set(jobs_snapshot.get("jobs_oldest_queued_age_seconds", 0.0))

        try:
            outbox_snapshot = outbox.metrics_snapshot()
        except Exception:
            metrics_collection_errors.labels("outbox").inc()
        else:
            for status in ("pending", "delivering", "delivered", "failed"):
                outbox_counts.labels(status).set(outbox_snapshot.get(f"outbox_{status}", 0.0))
            oldest_pending_outbox_age.set(
                outbox_snapshot.get("outbox_oldest_pending_age_seconds", 0.0)
            )
        try:
            monitor_snapshot = monitors.metrics_snapshot()
        except Exception:
            metrics_collection_errors.labels("monitors").inc()
        else:
            for status in ("active", "paused", "deleted"):
                monitor_counts.labels(status).set(monitor_snapshot.get(f"monitors_{status}", 0.0))
        response = Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.middleware("http")
    async def authenticate(request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = (
            request.method
            if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
            else "OTHER"
        )
        supplied_request_id = request.headers.get("x-request-id", "")
        request_id = (
            supplied_request_id
            if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_request_id)
            else uuid.uuid4().hex
        )
        request.state.request_id = request_id
        started_at = time.perf_counter()
        http_in_flight.labels(method).inc()
        response: Response | None = None

        async def traced_call_next() -> Response:
            traceparent = extract_valid_traceparent(request.headers)
            parent = None
            if traceparent:
                from opentelemetry.propagate import extract

                parent = extract({"traceparent": traceparent})
            with start_span(
                "twi.http.request",
                {"operation": method.lower(), "component": "api"},
                parent=parent,
            ):
                return await call_next(request)

        try:
            if request.url.path in {
                "/health/live",
                "/health/ready",
                "/health/monitors",
                "/health/telemetry",
            }:
                response = await traced_call_next()
            elif request.url.path == "/internal/metrics":
                if config.metrics_token is None:
                    response = JSONResponse(status_code=404, content={"detail": "not found"})
                elif not hmac.compare_digest(
                    request.headers.get("authorization", ""), f"Bearer {config.metrics_token}"
                ):
                    response = JSONResponse(
                        status_code=401,
                        content={"detail": "metrics credentials required"},
                        headers={"WWW-Authenticate": 'Bearer realm="twi-metrics"'},
                    )
                else:
                    response = await traced_call_next()
            else:
                authorization = request.headers.get("authorization", "")
                scheme, separator, token = authorization.partition(" ")
                if scheme.lower() != "bearer" or not separator or not token:
                    response = JSONResponse(
                        status_code=401,
                        content={"detail": "bearer token required"},
                        headers={"WWW-Authenticate": 'Bearer realm="twi", error="invalid_token"'},
                    )
                else:
                    try:
                        request.state.principal = trusted_verifier.verify(token)
                    except Exception:
                        response = JSONResponse(
                            status_code=401,
                            content={"detail": "access token invalid"},
                            headers={
                                "WWW-Authenticate": 'Bearer realm="twi", error="invalid_token"'
                            },
                        )
                    else:
                        response = await traced_call_next()
            if response is None:
                raise RuntimeError("request middleware completed without a response")
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            if not isinstance(route_path, str) or not route_path.startswith("/"):
                route_path = "unmatched"
            if request.url.path != "/internal/metrics":
                status_code = response.status_code if response is not None else 500
                http_requests.labels(method, route_path, str(status_code)).inc()
                http_duration.labels(method, route_path).observe(time.perf_counter() - started_at)
            http_in_flight.labels(method).dec()

    app.add_middleware(RequestBodyLimitMiddleware, max_body_bytes=65_536)
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(monitors_router)
    app.include_router(research_router)
    app.include_router(world_intelligence_router)
    app.include_router(usage_router)
    return app
