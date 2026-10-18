"""Authentication context; authorization scopes are issued by Tinlance Agent Platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Principal:
    tenant_id: str
    subject_id: str
    client_id: str
    principal_type: str
    token_id: str
    scopes: frozenset[str]
    roles: frozenset[str]
    expires_at: datetime


class PrincipalVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class DenyAllPrincipalVerifier:
    """Safe default for tests/local scaffolding when no identity verifier is configured."""

    def verify(self, token: str) -> Principal:
        del token
        raise PermissionError("no trusted identity verifier is configured")


def require_scope(principal: Principal, scope: str) -> None:
    if scope not in principal.scopes:
        raise PermissionError("required delegated scope is missing")
