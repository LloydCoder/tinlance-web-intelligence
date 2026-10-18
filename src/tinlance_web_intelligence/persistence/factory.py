"""Persistence backend selection shared by API and worker entry points."""
from __future__ import annotations

from tinlance_web_intelligence.artifacts.store import ArtifactStore, MemoryArtifactStore
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    SQLiteSourceEvidenceOutbox,
)
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
from tinlance_web_intelligence.persistence.postgres_artifacts import PostgresArtifactStore
from tinlance_web_intelligence.persistence.postgres_jobs import PostgresJobRepository
from tinlance_web_intelligence.persistence.postgres_outbox import PostgresSourceEvidenceOutbox
from tinlance_web_intelligence.persistence.protocols import JobRepository, SourceEvidenceOutbox


def create_job_repository(settings: Settings) -> JobRepository:
    """Select PostgreSQL when configured; SQLite is development/test only."""
    if settings.database_url:
        return PostgresJobRepository(settings.database_url)
    if settings.environment == "production":
        raise ValueError("production requires PostgreSQL persistence")
    return SQLiteJobRepository(settings.database_path)


def create_source_evidence_outbox(settings: Settings) -> SourceEvidenceOutbox:
    """Select the matching durable outbox backend."""
    if settings.database_url:
        return PostgresSourceEvidenceOutbox(settings.database_url)
    if settings.environment == "production":
        raise ValueError("production requires PostgreSQL persistence")
    return SQLiteSourceEvidenceOutbox(settings.database_path)


def create_artifact_store(settings: Settings) -> ArtifactStore:
    """Use durable, tenant-scoped PostgreSQL artifacts in production."""
    if settings.database_url:
        return PostgresArtifactStore(settings.database_url, max_bytes=settings.max_response_bytes)
    if settings.environment in {"staging", "production"}:
        raise ValueError("staging and production require PostgreSQL artifact storage")
    return MemoryArtifactStore(max_bytes=settings.max_response_bytes)
