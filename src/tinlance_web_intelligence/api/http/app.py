"""FastAPI application factory with fail-closed Platform token verification."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from tinlance_web_intelligence.api.http.middleware import RequestBodyLimitMiddleware
from tinlance_web_intelligence.api.http.routes.health import router as health_router
from tinlance_web_intelligence.api.http.routes.jobs import router as jobs_router
from tinlance_web_intelligence.api.http.routes.research import router as research_router
from tinlance_web_intelligence.auth.jwks import PlatformTokenVerifier
from tinlance_web_intelligence.auth.principal import DenyAllPrincipalVerifier, PrincipalVerifier
from tinlance_web_intelligence.config import ConfigurationError, Settings
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository


def create_app(
    *,
    settings: Settings | None = None,
    repository: SQLiteJobRepository | None = None,
    verifier: PrincipalVerifier | None = None,
) -> FastAPI:
    config = settings or Settings.from_env()
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
    trusted_verifier = verifier or DenyAllPrincipalVerifier()
    repo = repository or SQLiteJobRepository(config.database_path)
    docs_enabled = config.environment in {"development", "test"}
    app = FastAPI(
        title="Tinlance Web Intelligence API",
        version="1.0.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.state.repository = repo
    app.state.settings = config

    @app.middleware("http")
    async def authenticate(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in {"/health/live", "/health/ready"}:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "bearer token required"},
                headers={"WWW-Authenticate": 'Bearer realm="twi", error="invalid_token"'},
            )
        try:
            request.state.principal = trusted_verifier.verify(token)
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "access token invalid"},
                headers={"WWW-Authenticate": 'Bearer realm="twi", error="invalid_token"'},
            )
        return await call_next(request)

    app.add_middleware(RequestBodyLimitMiddleware, max_body_bytes=65_536)
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(research_router)
    return app
