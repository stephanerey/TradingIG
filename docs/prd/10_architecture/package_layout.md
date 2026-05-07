# Package Layout

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Proposed layout
```text
trading-ig-assistant/
  pyproject.toml
  README.md
  src/
    trading_ig_assistant/
      __init__.py
      main.py
      app/
        application.py
        event_bus.py
        config.py
      adapters/
        ig_rest.py
        ig_streaming.py
        news_provider.py
        economic_calendar.py
        credentials.py
      domain/
        instruments.py
        products.py
        market_data.py
        tickets.py
        positions.py
        pending_orders.py
        trade_state.py
        journal.py
      services/
        market_data_service.py
        product_discovery_service.py
        setup_scoring_service.py
        macro_context_service.py
        macro_ribbon_service.py
        risk_engine.py
        ticket_builder.py
        pending_order_engine.py
        trade_manager.py
        journal_service.py
        analytics_service.py
      persistence/
        sqlite_store.py
        repositories.py
        migrations/
      ui/
        main_window.py
        settings_view.py
        product_selector.py
        macro_ribbon_widget.py
        chart_view.py
        ticket_view.py
        monitor_view.py
        journal_view.py
      utils/
        time.py
        ids.py
        redaction.py
  tests/
    unit/
    integration/
    replay/
  docs/
```

## Constraints
- `domain/` MUST have no dependency on Qt, IG, HTTP, or SQLite.
- `services/` MAY depend on domain and adapter interfaces, not concrete UI.
- `adapters/` contain external integration code.
- `ui/` consumes services and events.

## Acceptance criteria
- Importing domain and services does not initialize UI or network sessions.
- Unit tests can mock every external adapter.

## Testing notes
- Add import boundary tests if practical.
