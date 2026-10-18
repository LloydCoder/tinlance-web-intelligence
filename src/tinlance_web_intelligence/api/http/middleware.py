"""ASGI request-size guard to bound JSON parsing and queue submission memory."""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_body_bytes: int = 65_536) -> None:
        if max_body_bytes < 1:
            raise ValueError("max_body_bytes must be positive")
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {
            "POST", "PUT", "PATCH", "DELETE"
        }:
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length is not None:
            try:
                declared_length = int(raw_length)
            except ValueError:
                await self._reject(send, 400, "invalid content length")
                return
            if declared_length < 0:
                await self._reject(send, 400, "invalid content length")
                return
            if declared_length > self.max_body_bytes:
                await self._reject(send, 413, "request body exceeds configured limit")
                return
        messages: list[Message] = []
        body_size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            messages.append(message)
            if message["type"] == "http.request":
                body_size += len(message.get("body", b""))
                if body_size > self.max_body_bytes:
                    await self._reject(send, 413, "request body exceeds configured limit")
                    return
                if not message.get("more_body", False):
                    break
        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send: Send, status_code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})
