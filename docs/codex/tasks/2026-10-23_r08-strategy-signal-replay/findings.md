# Findings

- `Strategy` already defines the required injected boundary: stable `strategy_id` and
  `evaluate(IndicatorInput)`.
- `StrategySignal` already carries strategy version, instrument, UTC decision time, data state,
  reasons, features and provenance.
- The chronological feed supplies closed cumulative prefixes and an explicit source-availability
  clock; no second candle pipeline is required.
- No approved concrete strategy exists, so only a synthetic strategy can test orchestration.
- The existing strategy contract has no separate latency model; the runner permits decisions at or
  after source availability and rejects any subsequent backward movement.
- `rules_version` is the experiment field available to bind the emitted strategy version; the
  binding is explicit and covered by regression tests.
