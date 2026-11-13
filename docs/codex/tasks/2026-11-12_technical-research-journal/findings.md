# Findings

- The current schema already provides an append-only, WAL-enabled `journal_events` table with immutable triggers and secret-field rejection.
- The GUI scanner publishes a complete `ScannerRuntimeBatchResult` once a new closed candle is observed.
- That result contains the signal decision, readiness, reason codes, exact indicator values, context projection, score components and provenance required for an initial post-mortem record.
- Reusing this surface avoids a storage migration and reaches a reviewable GitHub checkpoint faster.
- A sanitized bundle can be produced from the same immutable events without exporting the account pseudonym, PnL, tickets, orders or positions.
- The generated bundle is suitable for an explicit human upload to Rooms; no connector or automatic external publication is introduced.

