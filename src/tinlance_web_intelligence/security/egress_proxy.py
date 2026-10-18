"""Authenticated HTTP CONNECT egress proxy with public-IP validation and pinning."""

from __future__ import annotations

import asyncio
import base64
import hmac
import ipaddress
import os
import re
import socket
from contextlib import suppress
from dataclasses import dataclass


class ProxyProtocolError(ValueError):
    """Malformed or unsupported proxy request."""


class ProxyAuthenticationError(ValueError):
    """Proxy credentials are absent or invalid."""


class ProxyPolicyError(ValueError):
    """Proxy destination violates the public-web egress policy."""


@dataclass(frozen=True, slots=True)
class EgressProxyConfig:
    host: str
    port: int
    username: str
    password: str
    max_connections: int = 100
    max_header_bytes: int = 16_384
    max_tunnel_seconds: int = 120
    max_tunnel_bytes: int = 25000000
    idle_timeout_seconds: int = 15

    def validate(self) -> None:
        if not self.host or not 1 <= self.port <= 65535:
            raise ValueError("egress proxy host and port are required")
        if not self.username or any(ord(ch) < 33 or ord(ch) > 126 for ch in self.username):
            raise ValueError("egress proxy username must be printable ASCII")
        if (
            len(self.password) < 24
            or self.password != self.password.strip()
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in self.password)
        ):
            raise ValueError("egress proxy password must be at least 24 printable ASCII characters")
        if not 1 <= self.max_connections <= 1000:
            raise ValueError("max connections must be between 1 and 1000")
        if not 1024 <= self.max_header_bytes <= 65536:
            raise ValueError("max header bytes must be between 1024 and 65536")
        if not 1 <= self.max_tunnel_seconds <= 600 or not 1 <= self.idle_timeout_seconds <= 60:
            raise ValueError("proxy tunnel and idle timeouts are outside permitted limits")
        if not 1024 <= self.max_tunnel_bytes <= 100000000:
            raise ValueError("proxy tunnel byte limit must be between 1024 and 100000000")


class SafeEgressProxy:
    def __init__(self, config: EgressProxyConfig) -> None:
        config.validate()
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_connections)
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        if self._server is not None:
            raise RuntimeError("egress proxy is already running")
        self._server = await asyncio.start_server(
            self._handle, self.config.host, self.config.port,
            limit=self.config.max_header_bytes + 1,
        )

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def serve_forever(self) -> None:
        if self._server is None:
            await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def _handle(
        self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
    ) -> None:
        async with self._semaphore:
            upstream_writer: asyncio.StreamWriter | None = None
            try:
                try:
                    raw = await asyncio.wait_for(
                        client_reader.readuntil(b"\r\n\r\n"),
                        timeout=self.config.idle_timeout_seconds,
                    )
                except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, TimeoutError):
                    await self._send_status(client_writer, 400, "Bad Request")
                    return
                if len(raw) > self.config.max_header_bytes:
                    await self._send_status(client_writer, 431, "Request Header Fields Too Large")
                    return
                try:
                    method, target, version, headers = self._parse_request(raw)
                    self._authenticate(headers)
                    host, port = self._parse_target(method, target)
                    ip = await self._resolve_public_ip(host, port, "https" if method == "CONNECT" else "http")
                except ProxyAuthenticationError:
                    await self._send_status(
                        client_writer,
                        407,
                        "Proxy Authentication Required",
                        extra='Proxy-Authenticate: Basic realm="twi-egress"\r\n',
                    )
                    return
                except ProxyProtocolError:
                    await self._send_status(client_writer, 400, "Bad Request")
                    return
                except (ProxyPolicyError, ValueError):
                    await self._send_status(client_writer, 403, "Forbidden")
                    return
                try:
                    upstream_reader, upstream_writer = await asyncio.wait_for(
                        asyncio.open_connection(
                            ip,
                            port,
                            family=socket.AF_INET6 if ":" in ip else socket.AF_INET,
                        ),
                        timeout=5,
                    )
                except (OSError, TimeoutError):
                    await self._send_status(client_writer, 502, "Bad Gateway")
                    return
                if method == "CONNECT":
                    client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    await client_writer.drain()
                else:
                    safe_headers = [
                        (name, value) for name, value in headers
                        if name.lower() not in {"proxy-authorization", "proxy-connection", "connection"}
                    ]
                    host_header = f"{host}:{port}"
                    request = f"GET {target} HTTP/1.1\r\nHost: {host_header}\r\nConnection: close\r\n"
                    request += "".join(f"{name}: {value}\r\n" for name, value in safe_headers)
                    client_writer.write(b"")
                    upstream_writer.write(request.encode("latin-1") + b"\r\n")
                    await upstream_writer.drain()
                await self._relay(
                    client_reader, client_writer, upstream_reader, upstream_writer,
                    max_seconds=self.config.max_tunnel_seconds,
                    max_bytes=self.config.max_tunnel_bytes,
                )
            except (ConnectionError, OSError, TimeoutError, ProxyPolicyError):
                return
            finally:
                if upstream_writer is not None:
                    upstream_writer.close()
                    with suppress(OSError):
                        await upstream_writer.wait_closed()
                client_writer.close()
                with suppress(OSError):
                    await client_writer.wait_closed()

    @staticmethod
    def _parse_request(raw: bytes) -> tuple[str, str, str, list[tuple[str, str]]]:
        try:
            lines = raw.decode("latin-1").split("\r\n")
            request_line = lines[0].split(" ")
        except (UnicodeDecodeError, IndexError) as exc:
            raise ProxyProtocolError("malformed request") from exc
        if len(request_line) != 3 or request_line[2] != "HTTP/1.1":
            raise ProxyProtocolError("only HTTP/1.1 proxy requests are supported")
        method, target, version = request_line
        if method != "CONNECT":
            raise ProxyProtocolError("only HTTPS CONNECT tunnels are supported")
        headers: list[tuple[str, str]] = []
        seen: set[str] = set()
        for line in lines[1:]:
            if not line:
                continue
            if line[0] in " \t" or ":" not in line:
                raise ProxyProtocolError("malformed header")
            name, value = line.split(":", 1)
            name = name.strip()
            value = value.strip()
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
                raise ProxyProtocolError("invalid header name")
            if any(ord(ch) < 32 and ch != "\t" for ch in value):
                raise ProxyProtocolError("invalid header value")
            lower = name.lower()
            if lower in seen:
                raise ProxyProtocolError("duplicate header")
            seen.add(lower)
            headers.append((name, value))
        return method, target, version, headers

    def _authenticate(self, headers: list[tuple[str, str]]) -> None:
        values = [value for name, value in headers if name.lower() == "proxy-authorization"]
        if len(values) != 1 or not values[0].startswith("Basic "):
            raise ProxyAuthenticationError("proxy authentication required")
        try:
            decoded = base64.b64decode(values[0][6:], validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProxyAuthenticationError("invalid proxy credentials") from exc
        expected = f"{self.config.username}:{self.config.password}"
        if not hmac.compare_digest(decoded, expected):
            raise ProxyAuthenticationError("invalid proxy credentials")

    @staticmethod
    def _parse_target(method: str, target: str) -> tuple[str, int]:
        if method != "CONNECT":
            raise ProxyPolicyError("only HTTPS CONNECT tunnels are supported")
        if target.startswith("["):
            closing = target.find("]")
            if closing < 0 or target[closing + 1 :] != ":443":
                raise ProxyProtocolError("IPv6 CONNECT target must use [address]:443")
            host = target[1:closing]
            try:
                address = ipaddress.ip_address(host)
            except ValueError as exc:
                raise ProxyProtocolError("invalid IPv6 CONNECT target") from exc
            if not isinstance(address, ipaddress.IPv6Address):
                raise ProxyProtocolError("bracketed CONNECT target must be IPv6")
            return str(address), 443
        if "@" in target or target.count(":") != 1:
            raise ProxyProtocolError("CONNECT target must be host:443")
        host, raw_port = target.rsplit(":", 1)
        if not raw_port.isdigit() or int(raw_port) != 443 or not host:
            raise ProxyPolicyError("CONNECT is permitted only on port 443")
        return host.rstrip(".").lower(), 443

    async def _resolve_public_ip(self, host: str, port: int, scheme: str) -> str:
        if scheme != "https" or port != 443:
            raise ProxyPolicyError("egress proxy permits HTTPS on port 443 only")
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            return await self._resolve_public_hostname(host, port)
        if not literal.is_global:
            raise ProxyPolicyError("non-public IP destinations are forbidden")
        return str(literal)

    async def _resolve_public_hostname(self, host: str, port: int) -> str:
        labels = host.rstrip(".").lower().split(".")
        if (
            not host
            or len(host) > 253
            or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in labels
            )
        ):
            raise ProxyPolicyError("invalid hostname")
        loop = asyncio.get_running_loop()
        try:
            infos = await asyncio.wait_for(
                loop.getaddrinfo(host, port, type=socket.SOCK_STREAM), timeout=5
            )
        except (OSError, TimeoutError) as exc:
            raise ProxyPolicyError("destination DNS lookup failed") from exc
        addresses = sorted({item[4][0].split("%", 1)[0] for item in infos})
        if not addresses:
            raise ProxyPolicyError("destination has no addresses")
        parsed: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        for address in addresses:
            try:
                parsed.append(ipaddress.ip_address(address))
            except ValueError as exc:
                raise ProxyPolicyError("invalid DNS response") from exc
        if any(not address.is_global for address in parsed):
            raise ProxyPolicyError("hostname resolves to a non-public address")
        return str(parsed[0])

    @staticmethod
    async def _relay(
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream_reader: asyncio.StreamReader,
        upstream_writer: asyncio.StreamWriter,
        *, max_seconds: int,
    ) -> None:
        async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            while True:
                chunk = await asyncio.wait_for(reader.read(16_384), timeout=15)
                if not chunk:
                    with suppress(OSError):
                        writer.write_eof()
                    return
                writer.write(chunk)
                await writer.drain()
        async with asyncio.timeout(max_seconds):
            tasks = [
                asyncio.create_task(pipe(client_reader, upstream_writer)),
                asyncio.create_task(pipe(upstream_reader, client_writer)),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                task.result()

    @staticmethod
    async def _send_status(
        writer: asyncio.StreamWriter, code: int, reason: str, *, extra: str = ""
    ) -> None:
        body = f"{code} {reason}\n".encode()
        writer.write(
            (
                f"HTTP/1.1 {code} {reason}\r\n{extra}"
                f"Connection: close\r\nContent-Length: {len(body)}\r\n\r\n"
            ).encode()
            + body
        )
        with suppress(OSError):
            await writer.drain()


def config_from_env() -> EgressProxyConfig:
    config = EgressProxyConfig(
        host=os.environ.get("TWI_EGRESS_PROXY_HOST", "127.0.0.1"),
        port=int(os.environ.get("TWI_EGRESS_PROXY_PORT", "3128")),
        username=os.environ.get("TWI_BROWSER_PROXY_USERNAME", ""),
        password=os.environ.get("TWI_BROWSER_PROXY_PASSWORD", ""),
        max_connections=int(os.environ.get("TWI_EGRESS_PROXY_MAX_CONNECTIONS", "100")),
        max_tunnel_seconds=int(os.environ.get("TWI_EGRESS_PROXY_MAX_TUNNEL_SECONDS", "120")),
        idle_timeout_seconds=int(os.environ.get("TWI_EGRESS_PROXY_IDLE_TIMEOUT_SECONDS", "15")),
        max_tunnel_bytes=int(os.environ.get("TWI_EGRESS_PROXY_MAX_BYTES", "25000000")),
    )
    config.validate()
    return config
