# Task plan — R08 chronological replay feed

## Objective

Add a deterministic, offline and versioned candle feed that exposes only the observations already
reached by the replay clock.

## Authority and limits

- Authorized by the user's request to continue R08 offline development.
- No strategy selection or optimization, broker call, AUTO activation, persistence, migration,
  dependency or GUI wiring.
- Existing `ChartCandleSeries` may be adapted in memory; this lot does not open cache files itself.
- Synthetic fixtures prove chronology and validation mechanics only.

## Selected project skills

- `codex-tradingig-paper-execution`
- `codex-tradingig-accounts-risk`

## Approach

1. Define immutable dataset and replay-frame contracts in the existing replay domain module.
2. Validate required provenance, UTC closed candles, valid OHLC and strict timestamp ordering.
3. Adapt an existing `ChartCandleSeries` into a versioned replay dataset without I/O.
4. Emit cumulative `IndicatorInput` frames, including explicit warmup status.
5. Bind the feed to the experiment dataset ID/version and reject mismatches.

## Verification

- Synthetic cumulative-feed and warmup tests.
- Future-candle invisibility assertion.
- Invalid chronology, OHLC, UTC, open candle and provenance mismatch tests.
- Protected Paper/IG regressions and full offline suite.

## Stop condition

Stop after the generic chronological candle feed. Do not invent an entry strategy, simulate new
trades, persist experiments or claim quantitative acceptance.
