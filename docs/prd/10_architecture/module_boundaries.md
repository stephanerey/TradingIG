# Module Boundaries

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Goal
Prevent a monolithic trading script by enforcing clear dependencies.

## Allowed dependencies
- `domain` depends only on Python standard library and small value-object utilities.
- `services` depend on `domain` and adapter protocols/interfaces.
- `adapters` depend on external libraries and map external data to domain models.
- `ui` depends on services, not on raw broker API responses.
- `persistence` maps domain events/models to local storage.

## Forbidden dependencies
- UI code MUST NOT calculate risk directly.
- UI code MUST NOT directly call IG endpoints.
- Broker adapters MUST NOT decide trade recommendations.
- Trading rules MUST NOT be hidden in chart widgets.
- Macro ribbon UI MUST NOT fetch news/calendar data directly; it consumes `MacroRibbonState` from services.
- Secrets MUST NOT be passed through generic logs/events.

## Acceptance criteria
- `RiskEngine`, `TicketBuilder`, `PendingOrderEngine`, and `TradeManager` run headless in tests.
- IG adapters can be replaced by replay/mock adapters.

## Testing notes
- Unit tests should instantiate core services without Qt application startup.
