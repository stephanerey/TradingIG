# R00/R01 findings

## R00 baseline

- Project-local environment: `.venv`, CPython 3.12.6; declared package and `dev` extras installed without changing `pyproject.toml` or the global interpreter.
- `pip check` and application/PyQt/import smoke passed.
- Baseline full suite before R01: 102 tests passed.
- `ruff check src tests` passed. Repository-wide Ruff remains red because the installed SR scripts contain pre-existing lint findings outside R01.
- Formatting debt was pre-existing: repository-wide check listed 37 files; the focused `src tests` check listed 11. No unrelated blanket formatting was performed.
- Offline Windows Qt smoke passed: `MainWindow` could be created, shown, processed, and closed without IG connectivity.

## R01 diagnosis

1. Historical-quota cache access was not reproduced: three existing offline regressions passed and showed disk cache rendering with zero REST calls after historical allowance exhaustion, including a barrier using its chart-source epic. An adjacent ordering bug did exist for the global API allowance flag: it returned before either local cache was inspected. Cache loading now always precedes every REST allowance gate.
2. M1-to-M5 aggregation was reproduced as defective. Two M1 updates in the same five-minute bucket left only the second minute's OHLC; a revision similarly replaced the whole bucket. The service now retains source-minute candles by bucket and recomputes aggregate open/high/low/close on every insertion or revision.
3. Slow history loading was reproduced by inspection and timing: `_load_selected_product_history` called the adaptive REST fallback on the Qt thread. That work now runs in `PriceHistoryWorker`; cache rendering remains immediate, stale generations are ignored, and one latest reload is queued while a worker is active.

No authenticated IG request, order operation, trading activation, dependency addition, migration, or settings-inheritance decision was made.

