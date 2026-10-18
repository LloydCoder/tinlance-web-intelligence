"""ASGI entry point: uvicorn apps.api.main:app"""

from tinlance_web_intelligence.api.http.app import create_app

app = create_app()
