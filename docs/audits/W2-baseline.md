# W2 baseline audit — evidence record

- PR: [#8](https://github.com/LloydCoder/tinlance-web-intelligence/pull/8)
- PR head tested: `c1daf949aad9fd7710e6aa3400bc843a2bc528c6`
- CI run: [39139426892](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39139426892)
- Merge commit: `e6dd014d6cec8ada4bdfe49e3aaa452c5563af33`
- Result: Python 3.12 and 3.13 CI passed; PR merged after checks completed.

## Verified scope

- Brave Search API adapter with injected API key and source URL validation.
- HTTP retrieval uses connection-time DNS/IP checks, disables DNS cache and proxy environment inheritance, validates redirects manually, strips non-safe headers across origin changes, restricts destination ports, caps response bytes and timeouts, and rejects compressed responses until bounded decompression exists.
- HTML extraction strips script/style-like content and caps text and link output.
- Content-addressed in-memory artifacts preserve per-source capture records; this store is for tests/development and is not durable.
- Adversarial URL, resolver, credential-forwarding, extraction, search, acquisition service, and artifact tests passed.

## Limitations

- Live external search/fetch was not exercised in CI because no provider credentials or live-network integration environment were configured.
- Production egress firewalling, browser isolation, durable artifact storage, and Platform/World Intelligence/TSIC registration remain future gates.
