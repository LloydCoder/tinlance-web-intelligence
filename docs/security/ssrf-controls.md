# SSRF controls and verification

The [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) emphasizes validating the address actually used for the connection. A separate DNS preflight can be bypassed by DNS rebinding. TWI therefore uses a connection resolver that rejects any non-public DNS answer, disables aiohttp's DNS cache, disables automatic redirects, and validates every redirect target before requesting it. Network-level egress restrictions remain mandatory.

## Current controls

- HTTP(S) only; reject URL userinfo, local/internal suffixes, literal and legacy-form non-public IPv4 addresses, malformed ports, fragments, backslash parser ambiguity, and control characters.
- Resolve A/AAAA results through the connector resolver and reject the entire destination if any answer is non-public.
- No proxy environment inheritance; no automatic redirects; revalidate every redirect; bounded redirect count.
- Bounded total/connect/read timeouts, connection concurrency, response bytes, and content type/encoding.
- Request `Accept-Encoding: identity` and reject compressed responses until bounded decompression is implemented.
- No browser or API credentials are available to acquisition workers.

## Required deployment controls

- Deny egress to private, loopback, link-local, metadata, cluster, and control-plane networks at the network layer.
- Keep browser workers in ephemeral, unprivileged sandboxes.
- Verify actual socket destinations and redirect handling in integration tests under production network policy.
- Include adversarial URL cases from OWASP SSRF guidance and maintain a documented risk register.

These controls reduce risk but do not, by themselves, certify a deployed service as secure.
