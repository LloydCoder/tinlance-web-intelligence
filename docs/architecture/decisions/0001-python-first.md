# ADR 0001: Python-first implementation

- Status: accepted for initial workstreams.
- Decision: use Python 3.12+ for API, contracts, acquisition orchestration, extraction, and evaluation.
- Context: rapid iteration and broad web/data ecosystem support matter more than premature multi-language complexity.
- Consequences: use explicit interfaces and isolate CPU-/security-sensitive worker boundaries; add another language only with measured evidence and an ADR.
