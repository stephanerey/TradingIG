# P20 Architecture

> **PRD Policy:** **PROJECT (editable)** — Architecture phase scope.

**Last updated:** 2026-05-07

## Goal
Implement stable module boundaries and domain models before feature-heavy UI work.

## Non-goals
- No advanced trading signals.
- No live-mode order placement.

## Scope
- Domain models: `Instrument`, `ProductContract`, `Quote`, `Candle`, `Ticket`, `Position`, `PendingOrder`, `TradeState`, `JournalEvent`.
- Adapter interfaces: IG REST, IG Streaming, news/calendar providers.
- Event bus for quote updates, position updates, trade manager events.
- Persistence abstraction with SQLite implementation.
- Chart data model and candle aggregation.
- Risk engine and trade manager as UI-independent services.

## Acceptance criteria
- Core services are importable and unit-testable without Qt.
- Adapters can be mocked.
- Feature modules depend on interfaces, not concrete UI widgets.
- Logs and journal events share consistent IDs/timestamps.

## Testing notes
- Contract tests for adapters.
- Unit tests for risk/trade-manager/pending-order state machines.
