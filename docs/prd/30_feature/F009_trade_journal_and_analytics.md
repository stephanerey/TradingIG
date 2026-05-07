# F009 — Trade Journal and Analytics

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Record all trades and decisions, then compute performance metrics to improve rules over time.

## Non-goals
- No tax/accounting module in MVP.

## Requirements
- Store ticket proposals, accepted tickets, pending-order events, position updates, stop/limit changes, exits, PnL, user comments.
- Support tags: instrument, setup type, macro context, manual override, software pending order, dynamic stop mode.
- Store R multiple for each closed trade.
- Compute basic stats: win rate, average win/loss, expectancy, profit factor, max drawdown, result by instrument/setup.
- Export CSV/JSON without secrets.

## Constraints
- Journal event log should be append-only.
- Corrections must be added as events, not overwrite history silently.

## Acceptance criteria
- Every opened/linked trade has an event trail from proposal to close.
- Analytics can run on sample data.
- Export contains no credentials or tokens.

## Testing notes
- Unit-test journal persistence.
- Unit-test metrics on deterministic sample trades.
