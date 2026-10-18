# Local development

Python 3.12 or 3.13 is supported by CI. Install pinned development tools and run checks:

```bash
make install
make check
```

A Brave Search API key is optional and must be supplied to `BraveSearchProvider` by the caller. Never commit provider keys. The fetcher does not inherit proxy environment variables and rejects non-public DNS answers; do not weaken these checks to make local private test servers work. Test fetch orchestration with injected clients/resolvers and run network integration tests in an explicitly isolated environment.

The current artifact store is process-local and intended for tests/development only. Durable job and artifact persistence is part of W3.
