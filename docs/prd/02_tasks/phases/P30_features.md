# P30 Features

> **PRD Policy:** **PROJECT (editable)** — MVP feature phase scope.

**Last updated:** 2026-05-07

## Goal
Deliver the first usable assistant: connect to IG, display market/product data, build tickets, monitor software pending orders and open trades, and journal all actions.

## Non-goals
- No fully autonomous live trading by default.
- No opaque ML-based trade recommendations.

## Scope
- Settings screen.
- Product selector for Barriers/Options.
- IG-like candle chart with overlays.
- Scanner and setup scoring.
- Macro/news context panel.
- Ticket builder and risk validation.
- Software pending-order monitor with manual confirmation.
- Trade monitor and dynamic stop manager.
- Journal and basic analytics.

## Acceptance criteria
- User can reproduce the manual workflow from screenshots inside the app.
- Invalid or oversized tickets are rejected with explicit explanation.
- Software pending-order trigger produces an actionable alert and ticket state.
- Trade manager emits stop-update recommendations/events based on deterministic rules.
- Journal stores all key events.

## Testing notes
- Run dry-run trading session against replay data.
- Run demo session with live market data but manual/no execution.
