# Findings

- The GUI currently invokes `_load_selected_product_history()` on product, timeframe, range and
  price-basis changes. That path can read persisted snapshots and start an IG REST history worker.
- A live gap currently schedules one bounded REST repair.
- Streaming currently requests the selected timeframe directly. The candle service can aggregate
  M1 updates, but it does not retain a canonical in-memory M1 session that can rebuild another
  timeframe after the user switches it.
- Paper ticket/session behavior is independent from scanner refresh and technical indicator
  readiness; no relaxation of risk or broker protections is needed.
- The PRD prefers cache/backfill when reliable, but already requires explicit `WARMING_UP` when a
  provider is unavailable. The human has selected a reversible session-only policy until a reliable
  historical provider exists.
- The implemented session path stores M1 revisions independently for BID/MID/ASK and can therefore
  reproject another timeframe or price basis without a network or disk access.
- Only the newest incomplete higher-timeframe bucket is displayed. An older bucket missing any M1
  observation is omitted, so later technical analysis sees an explicit gap rather than fabricated
  continuity.
- The dormant IG historical implementation remains in the module behind `SESSION_ONLY_CANDLES` for
  a future provider decision, but the default GUI path cannot reach it.

