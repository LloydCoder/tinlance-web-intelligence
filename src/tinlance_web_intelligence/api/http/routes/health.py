"""Liveness and readiness probes; responses intentionally reveal no internal details."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(request: Request) -> JSONResponse | dict[str, str]:
    repository = request.app.state.repository
    if not repository.ping():
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
