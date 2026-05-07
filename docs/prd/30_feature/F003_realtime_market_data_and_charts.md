# F003 — Real-time Market Data and IG-like Charts

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Display a candlestick chart close enough to the IG web platform workflow to support the user's manual decision process and trade monitoring.

## Non-goals
- Do not clone the full IG platform.
- Do not implement advanced drawing tools in MVP unless trivial.

## Requirements
- Load historical candles via REST.
- Update live price via Streaming API.
- Support at least 5 min, 1 h, and configurable timeframes.
- Display candlesticks with OHLC tooltip/crosshair.
- Display bid/ask/current price labels.
- Overlay entry, stop, limit, KO/barrier, R/R label, software pending trigger, and PnL markers.
- Display open position markers and current state (`OPEN`, `PROTECTED`, `TRAILING`).
- Coexist with a persistent Global Market Context Ribbon above the chart workspace; chart area should resize cleanly when the ribbon is visible.
- Detect and display stale data.

## Constraints
- Chart rendering must remain responsive during streaming updates.
- Candle aggregation must be deterministic and testable.

## Acceptance criteria
- Chart can reproduce the essential visual workflow seen in IG screenshots: candles + horizontal lines for KO/stop/limit/entry + labels.
- Stale feed warning appears when no update is received beyond threshold.
- Chart can run from replay data without IG.

## Testing notes
- Unit-test candle aggregation.
- Replay known sessions and compare overlay levels.
