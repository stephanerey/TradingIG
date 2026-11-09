# Decisions

- Inject the existing `Strategy` protocol; do not add a strategy implementation.
- Preserve every frame, including warmup frames, and let the strategy return its explicit state.
- Bind `ReplayExperimentConfig.rules_version` to `StrategySignal.strategy_version` for this run.
- Keep signal evidence separate from tickets, risk reservations and execution.
