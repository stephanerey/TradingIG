# Decisions

- Reuse `AnalysisCandle` and `IndicatorInput`; do not create a parallel candle model.
- Keep cache/file loading outside the replay service and accept an already loaded chart series.
- Emit every prefix so production indicator warmup behavior remains observable.
- Require exact dataset ID/version agreement with `ReplayExperimentConfig`.
