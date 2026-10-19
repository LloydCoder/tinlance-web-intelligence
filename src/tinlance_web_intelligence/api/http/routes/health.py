"""Liveness and readiness probes; responses intentionally reveal no internal details."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from tinlance_web_intelligence.observability.tracing import tracing_export_mode

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", response_model=None)
def readiness(request: Request) -> JSONResponse | dict[str, str]:
    repository = request.app.state.repository
    monitors = request.app.state.monitor_repository
    outbox = request.app.state.evidence_outbox
    if not repository.ping() or not monitors.ping() or not outbox.ping():
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@router.get("/health/monitors", response_model=None)
def monitor_health(request: Request) -> JSONResponse | dict[str, str]:
    """Report monitor persistence availability without exposing operational details."""

    if not request.app.state.monitor_repository.ping():
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@router.get("/health/telemetry")
def telemetry_health() -> dict[str, str]:
    """Confirm trace propagation is enabled; exporter readiness is deployment evidence."""

    return {"status": "instrumented", "export_mode": tracing_export_mode()}
