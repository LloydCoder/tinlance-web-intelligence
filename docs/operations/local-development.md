# Local development

Python 3.12 or 3.13 is supported by CI. Install pinned development tools and run checks:

```bash
make install
make check
```

A Brave Search API key is optional and must be supplied as TWI_BRAVE_SEARCH_API_KEY to the worker. Never commit provider keys. The fetcher does not inherit proxy environment variables and rejects non-public DNS answers; do not weaken these checks to make local private test servers work. Test fetch orchestration with injected clients/resolvers and run network integration tests in an explicitly isolated environment.

Direct local development defaults to SQLite. To use PostgreSQL, set TWI_DATABASE_URL to a local PostgreSQL DSN with sslmode=disable only in development/test, then run python -m apps.migrate.main before starting the API or workers. Production requires sslmode=verify-full and a trusted CA, a separate TWI_MIGRATION_DATABASE_URL DDL role, and the migration job before runtime services start. PostgreSQL integration tests run when TWI_TEST_POSTGRES_DSN is set.

For Compose development, create a URL-safe local-only TWI_POSTGRES_PASSWORD in an ignored .env file, then run:

```bash
docker compose -f deployments/compose/development.yml config --quiet
docker compose -f deployments/compose/development.yml up --build
```

The API binds to localhost port 8080. Its readiness endpoint checks the job repository and source-evidence outbox. Browser isolation remains a separate security-test topology; do not treat the development Compose network as a production cloud egress policy.
