# Findings

- `ChartCandleSeries` already represents merged REST/cache/stream history in memory.
- `IndicatorInput` is the existing analysis boundary and already carries instrument, timeframe,
  source and price-basis provenance.
- No approved strategy or production dataset is available, so this lot must remain a generic feed.
- The existing indicator layer already reports warmup from the visible prefix; the feed must not
  skip early frames.
- A chart series does not identify its current/open candle. Conversion therefore requires an
  explicit UTC availability boundary and excludes intervals ending after it.
- Chart timestamps represent interval starts in the existing aggregation path, so replay OHLC
  availability is timestamp plus resolution.
