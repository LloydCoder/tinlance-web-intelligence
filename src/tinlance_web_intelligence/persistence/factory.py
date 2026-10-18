"""Persistence backend selection shared by API and worker entry points."""
from __future__ import annotations

from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    SQLiteSourceEvidenceOutbox,
)
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
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
