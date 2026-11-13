# Technical research journal — plan

1. Reuse the versioned append-only `journal_events` SQLite surface; do not add a migration.
2. Convert each scanner evaluation, including `FLAT`, `WARMING_UP`, invalid and failed cases, into an immutable structured event.
3. Persist exact decimal values as strings, UTC timestamps, closed-candle counts, indicators, levels, reasons and provenance.
4. Pseudonymize account identity and reject any secret-bearing payload through the existing repository guard.
5. Wire recording after a successful scanner evaluation without changing the scanner result or any order path.
6. Add unit tests for deterministic identity, duplicate suppression, readiness retention, failures, pseudonymization and controller error isolation.
7. Run targeted tests, then the full suite before the GitHub checkpoint.

