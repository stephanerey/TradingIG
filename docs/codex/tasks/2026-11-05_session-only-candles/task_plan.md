# Session-only candles

## Objective

Remove IG historical REST and persisted candle-cache recovery from the normal GUI path. Build the
current session from the M1 stream, derive displayed higher timeframes from that session, and keep
technical analysis explicitly warming up without blocking the independent Paper workflow.

## Authority and scope

- Human decision recorded in this conversation on 2026-11-05.
- Allowed: candle session accumulation, GUI history/bootstrap behavior, scanner availability text,
  focused tests and current-state/task documentation.
- Forbidden: LIVE/AUTO activation, broker order changes, dependency/provider additions, secret or
  credential access, branch/commit/file deletion.
- Preserve every pre-existing local modification.

## Smallest sufficient approach

1. Keep a canonical in-memory M1 series per session/source/price basis.
2. Subscribe the chart to M1 and derive M5/M15/M30/H1 from the accumulated session data.
3. Do not read persisted candle caches or start a historical REST worker from GUI selection,
   timeframe, range, price-basis or gap events.
4. Keep missing technical data visible as `WARMING_UP`/unavailable; do not manufacture values.
5. Leave Paper ticket/risk behavior structurally independent and unchanged.

## Selected skills

- `aurora-architecture-check`: temporary but durable runtime source/orchestration boundary.
- `codex-tradingig-analysis-scanner`: preserve closed-candle, warmup, provenance and no-execution
  rules.

## Verification

- Focused candle-history and GUI tests proving M1 accumulation, higher-timeframe derivation and
  zero historical REST calls.
- Scanner preview tests proving honest warmup on insufficient session data.
- Protected Paper/order regressions and targeted Ruff.

