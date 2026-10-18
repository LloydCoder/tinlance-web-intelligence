"""Acquisition result models shared by fetch, extraction, and artifact layers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    body: bytes
    retrieved_at: datetime
    headers: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    title: str | None
    description: str | None
    canonical_url: str | None
    text: str
    links: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AcquiredPage:
    fetch: FetchResult
    artifact_id: str
    content_sha256: str
    extracted: ExtractedPage
