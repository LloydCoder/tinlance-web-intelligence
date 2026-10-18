# System overview

TWI acquires and transforms web content into traceable observations. Its internal pipeline is:

`request → policy preflight → provider/fetch/browser → raw artifact reference → extraction → source-backed observation → export contract`

The first workstream establishes interfaces and security invariants; network-capable implementations arrive only after these foundations are reviewed.

TWI does not own world-state semantics, caller identity, execution approvals, or agent lifecycle.
