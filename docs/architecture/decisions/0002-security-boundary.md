# ADR 0002: Network acquisition is a hostile-input boundary

- Status: accepted.
- Decision: URL parsing is only one control. Acquisition must enforce DNS/IP checks at connection time, redirect revalidation, time/size limits, and network egress policy.
- Context: SSRF, DNS rebinding, internal service discovery, cloud metadata access, malicious documents, and prompt injection are expected threat classes.
- Consequences: browser workers run isolated from control-plane credentials. Retrieved content is data, never authority. Tests must cover IPv4 and IPv6 edge cases.
