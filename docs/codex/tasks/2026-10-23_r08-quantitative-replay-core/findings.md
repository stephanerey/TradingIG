# Findings

- `PaperPosition` already retains entry, close, fees, realized net P&L, timestamps, currency,
  provenance and fill-model version.
- It does not retain decision time or latest consumed source time, so a small immutable evidence
  wrapper is required to detect look-ahead explicitly.
- No approved AUTO strategy or production dataset exists; only generic mechanics can be validated.
- Recorded `realized_pnl` is the authoritative net result; the replay summary does not reconstruct
  fills or pretend that synthetic close prices prove broker realism.
- An empty replay is represented by explicit zero metrics rather than being rejected or interpreted
  as profitable.
- Persistence, dataset loading, full candle/event replay and walk-forward validation remain outside
  this bounded core.
