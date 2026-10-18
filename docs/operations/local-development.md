# Local development

Python 3.12 or 3.13 is supported by CI. Install pinned development tools and run checks:

```bash
make install
make check
```

A Brave Search API key is optional and must be supplied as `TWI_BRAVE_SEARCH_API_KEY` to the worker. Never commit provider keys. The fetcher does not inherit proxy environment variables and rejects non-public DNS answers; do not weaken these checks to make local private test servers work. Test fetch orchestration with injected clients/resolvers and run network integration tests in an explicitly isolated environment.

The W3 API uses a durable SQLite database by default at `./var/twi.sqlite3`. Non-health endpoints fail closed unless a trusted `PrincipalVerifier` is configured. Production requires `TWI_IDENTITY_ISSUER`, `TWI_IDENTITY_AUDIENCE`, and `TWI_IDENTITY_JWKS_URL`; these must describe the Tinlance Agent Platform token issuer and the TWI resource audience.

The artifact store is still process-local and intended for tests/development only. Durable job persistence is implemented; durable raw artifact storage remains a later hardening item.
