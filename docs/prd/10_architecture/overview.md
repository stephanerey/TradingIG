# Architecture Overview

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Goal
Define a modular desktop application where market connectivity, risk logic, trade management, charting, and UI remain decoupled and testable.

## Non-goals
- Do not put trading rules directly inside UI widget code.
- Do not hardcode IG EPICs or credentials in source code.
- Do not make live execution available before demo validation and explicit user enablement.

## High-level components
```text
[Qt UI]
  ├── Settings / Login View
  ├── Product Selector
  ├── Global Market Context Ribbon
  ├── Market Dashboard / Scanner
  ├── IG-like Candle Chart
  ├── Ticket Builder
  ├── Pending Order Monitor
  ├── Trade Monitor
  └── Journal / Analytics

[Application Services]
  ├── MarketDataService
  ├── ProductDiscoveryService
  ├── SetupScoringService
  ├── MacroContextService
  ├── MacroRibbonService / ViewModel
  ├── RiskEngine
  ├── TicketBuilder
  ├── SoftwarePendingOrderEngine
  ├── TradeManager
  ├── JournalService
  └── AlertService

[Adapters]
  ├── IGRestAdapter
  ├── IGStreamingAdapter
  ├── NewsProviderAdapter(s)
  ├── EconomicCalendarAdapter(s)
  └── CredentialProvider

[Persistence]
  ├── SQLite database
  ├── JSON/YAML non-secret settings
  └── OS keyring for secrets
```

## Constraints
- Core logic MUST be UI-independent.
- All external calls MUST go through adapters.
- All recommendations and trade-state changes MUST emit journal events.
- REST and Streaming sessions MUST expose explicit connection state.

## Acceptance criteria
- Services can be unit-tested without IG or Qt.
- UI subscribes to application events; it does not own domain state.
- Adapter errors are normalized into application-level error objects.

## Testing notes
- Mock adapters for unit tests.
- Integration tests gated behind demo credentials.
