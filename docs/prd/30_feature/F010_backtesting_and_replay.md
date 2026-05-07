# F010 — Backtesting and Replay

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Replay historical market data and journaled sessions to test entry filters, software pending orders, and stop-management rules.

## Non-goals
- No over-optimized ML strategy in MVP.
- No guarantee that backtest results predict live performance.

## Requirements
- Load cached IG historical candles.
- Replay candles/ticks into scanner, pending-order engine, and trade manager.
- Compare modes: fixed target, break-even only, trailing by structure, trailing by ATR.
- Produce metrics in R and currency.
- Save replay configuration and results.

## Constraints
- Backtests must include spread/fees/slippage approximations where possible.
- Avoid look-ahead bias: only past data is available to rules.

## Acceptance criteria
- A known scenario produces deterministic replay results.
- Stop-management rules can be compared without live broker connection.

## Testing notes
- Use fixture datasets.
- Add tests for no look-ahead access.
